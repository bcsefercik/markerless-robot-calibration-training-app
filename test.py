import random
import time
import os
import json
import traceback
import statistics
import datetime
from collections import defaultdict

import torch
import torch.optim as optim
from torch.utils.data import DataLoader
import numpy as np
import MinkowskiEngine as ME
import open3d as o3d
from tensorboardX import SummaryWriter

from utils import config, logger, utils, metrics


import ipdb


_config = config.Config()
_logger = logger.Logger().get()
_tensorboard_writer = SummaryWriter(_config.exp_path)

_use_cuda = torch.cuda.is_available()
_device = torch.device("cuda" if _use_cuda else "cpu")

torch.set_printoptions(precision=_config.TEST.print_precision, sci_mode=False)


def test(model, criterion, data_loader, output_filename="results.txt"):
    data_iter = iter(data_loader)
    model = model.eval()
    with torch.no_grad():
        start = time.time()

        overall_results = defaultdict(list)
        individual_results = defaultdict(lambda: defaultdict(list))
        results_json = {}

        for i, batch in enumerate(data_iter):
            try:
                coords, feats, _, poses, others = batch
                poses = poses.to(device=_device)

                model_input = ME.SparseTensor(feats, coordinates=coords, device=_device)
                out = model(model_input)

                loss = criterion(out, poses).item()

                metric_results = metrics.compute_pose_dist(poses, out)
                (
                    dist,
                    dist_position,
                    dist_orientation,
                    angle_diff,
                ) = tuple(mr.tolist() for mr in metric_results)

                for fi, other_info in enumerate(others):
                    fname = other_info["filename"]
                    position = other_info["position"]

                    print(f"{position}/{fname}")
                    preds_fi = [round(p, 4) for p in out[fi].tolist()]
                    result = {
                        "dist": round(float(dist[fi]), 4),
                        "dist_position": round(float(dist_position[fi]), 4),
                        "dist_orientation": round(float(dist_orientation[fi]), 4),
                        "angle_diff": round(float(angle_diff[fi]), 4),
                        "preds": preds_fi[:7],
                        "poses": [round(p, 4) for p in poses[fi].tolist()],
                        "position_confidence": preds_fi[7],
                        "orientation_confidence": preds_fi[8],
                        "confidence": preds_fi[9]
                    }
                    overall_results["dist"].append(result["dist"])
                    overall_results["dist_position"].append(result["dist_position"])
                    overall_results["dist_orientation"].append(
                        result["dist_orientation"]
                    )
                    overall_results["angle_diff"].append(result["angle_diff"])

                    individual_results[position]["dist"].append(result["dist"])
                    individual_results[position]["dist_position"].append(
                        result["dist_position"]
                    )
                    individual_results[position]["dist_orientation"].append(
                        result["dist_orientation"]
                    )
                    individual_results[position]["angle_diff"].append(
                        result["angle_diff"]
                    )
                    individual_results[position]["position_confidence"].append(
                        result["position_confidence"]
                    )
                    individual_results[position]["orientation_confidence"].append(
                        result["orientation_confidence"]
                    )
                    individual_results[position]["confidence"].append(
                        result["confidence"]
                    )
                    results_json[f"{position}/{fname}"] = result

                    with open(output_filename, "a") as fp:
                        fp.write(
                            f"{position}/{fname}: {json.dumps(result, indent=4)}\n"
                        )
                    # ipdb.set_trace()
            except Exception as e:
                print(e)
                _logger.exception(f"Filenames: {json.dumps(others)}")

        with open(output_filename.replace('.txt', '.json'), "a") as fp:
            json.dump(results_json, fp)

        for k in overall_results:
            overall_results[k] = round(statistics.mean(overall_results[k]), 4)
        for pos in individual_results:
            for k in individual_results[pos]:
                individual_results[pos][k] = round(
                    statistics.mean(individual_results[pos][k]), 4
                )

        with open(output_filename, "a") as fp:
            fp.write("\n---------- SUMMARY ----------\n")

            for pos in individual_results:
                fp.write(f"{pos}: {json.dumps(individual_results[pos], indent=4)}\n")

            fp.write(f"Overall: {json.dumps(overall_results, indent=4)}\n")


if __name__ == "__main__":
    print(f"CONFIG: {_config()}")

    if _use_cuda:
        torch.cuda.empty_cache()

    from model.robotnet import RobotNet, get_criterion
    from data.alivev2 import AliveV2Dataset, collate

    criterion = get_criterion(device=_device)
    compute_confidence = _config()['STRUCTURE'].get('compute_confidence', False)
    model = RobotNet(
        in_channels=3,
        out_channels=10 if compute_confidence else 7,
        D=3
    )

    start_epoch = utils.checkpoint_restore(
        model,
        f=os.path.join(_config.exp_path, _config.TEST.checkpoint),
        use_cuda=_use_cuda,
    )

    print("Loaded model.")

    dataset_name = ""

    file_names = defaultdict(list)
    file_names_path = _config()['DATA'].get('file_names')
    if file_names_path:
        file_names_path = file_names_path.split(',')

        dataset_name = utils.remove_suffix(file_names_path[0].split('/')[-1], '.json')

        with open(file_names_path[0], 'r') as fp:
            file_names = json.load(fp)

        for fnp in file_names_path[1:]:
            with open(fnp, 'r') as fp:
                new_file_names = json.load(fp)

                for k in new_file_names:
                    if k in file_names:
                        file_names[k].extend(new_file_names[k])

    for dt in ("val", "test", "train"):
        print("Dataset:", dt)

        if not file_names[dt]:
            print(f"Dataset {dt} split is empty.")
            continue

        dataset = AliveV2Dataset(set_name=dt, file_names=file_names[dt])
        data_loader = DataLoader(
            dataset,
            batch_size=_config.TEST.batch_size,
            collate_fn=collate,
            num_workers=_config.TEST.workers,
            shuffle=False,
            drop_last=False,
            pin_memory=True,
        )

        test(
            model,
            criterion,
            data_loader,
            output_filename=os.path.join(
                _config.exp_path,
                f"{utils.remove_suffix(_config.TEST.checkpoint, '.pth')}_results_{dataset_name}_{dt}.txt",
            ),
        )

    # ipdb.set_trace()

    print("DONE!")
