import random
import time
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


def train_epoch(train_data_loader, model, optimizer, criterion, miner, epoch):
    iter_time = utils.AverageMeter()
    data_time = utils.AverageMeter()
    am_dict = defaultdict(utils.AverageMeter)

    train_iter = iter(train_data_loader)
    model.train()

    start_epoch = time.time()
    end = time.time()

    for i, batch in enumerate(train_iter):
        try:
            data_time.update(time.time() - end)

            utils.step_learning_rate(
                optimizer,
                _config.TRAIN.lr,
                epoch - 1,
                _config.TRAIN.step_epoch,
                _config.TRAIN.multiplier,
            )

            coords, rgb, labels, _ = batch
            labels = labels.to(device=_device)
            model_input = ME.SparseTensor(rgb, coordinates=coords, device=_device)
            out = model(model_input)

            hard_pairs = miner(out.features, labels)
            pos_perm_size = min(
                len(hard_pairs[0]), _config.DATA.batch_size * _config.DATA.max_pair
            )
            neg_perm_size = min(
                len(hard_pairs[2]), _config.DATA.batch_size * _config.DATA.max_pair
            )
            pos_idx = torch.randperm(pos_perm_size)
            neg_idx = torch.randperm(neg_perm_size)

            hard_pairs = (
                hard_pairs[0][pos_idx],
                hard_pairs[1][pos_idx],
                hard_pairs[2][neg_idx],
                hard_pairs[3][neg_idx],
            )
            loss = criterion(out.features, labels, hard_pairs)

            loss.backward()
            optimizer.step()

            curr_batch_count = coords[-1][0].item() + 1
            am_dict["loss"].update(loss.item(), curr_batch_count)

            current_iter = (epoch - 1) * len(train_data_loader) + i + 1
            max_iter = _config.TRAIN.epochs * len(train_data_loader)
            remain_iter = max_iter - current_iter

            iter_time.update(time.time() - end)
            end = time.time()

            remain_time = remain_iter * iter_time.avg
            t_m, t_s = divmod(remain_time, 60)
            t_h, t_m = divmod(t_m, 60)
            remain_time = f"{int(t_h):02d}:{int(t_m):02d}:{int(t_s):02d}"

            _logger.info(
                "epoch: {}/{} iter: {}/{} loss: {:.4f}({:.4f}) data_time: {:.2f}({:.2f}) iter_time: {:.2f}({:.2f}) remain_time: {remain_time}".format(
                    epoch,
                    _config.TRAIN.epochs,
                    i + 1,
                    len(train_data_loader),
                    am_dict["loss"].val,
                    am_dict["loss"].avg,
                    data_time.val,
                    data_time.avg,
                    iter_time.val,
                    iter_time.avg,
                    remain_time=remain_time,
                )
            )
        # For better debugging
        # except Exception as e:
        #     print(str(batch))
        #     print(str(e))
        #     print(traceback.format_exc())
        #     ipdb.set_trace()
        #     raise e
        except Exception:
            _logger.exception(str(batch))

    for k in am_dict:
        # if k in visual_dict.keys():
        _tensorboard_writer.add_scalar(k + "_train", am_dict[k].avg, epoch)
    _tensorboard_writer.flush()


# def eval_epoch(val_data_loader, model, criterion, epoch):
#     _logger.info(f"> Evaluation at epoch: {epoch}")
#     am_dict = defaultdict(utils.AverageMeter)

#     with torch.no_grad():
#         val_iter = iter(val_data_loader)
#         model.eval()
#         start_epoch = time.time()
#         for i, batch in enumerate(val_iter):
#             try:
#                 coords, feats, _, poses, _ = batch
#                 poses = poses.to(device=_device)

#                 model_input = ME.SparseTensor(
#                     feats, coordinates=coords, device=_device, requires_grad=False
#                 )
#                 out = model(model_input)
#                 loss = criterion(out.F, poses)

#                 dists = metrics.compute_pose_dist(poses, out.features)
#                 am_dict["loss"].update(loss.item(), len(poses))
#                 am_dict["dist"].update(statistics.mean(dists[0].tolist()), len(poses))
#                 am_dict["dist_position"].update(
#                     statistics.mean(dists[1].tolist()), len(poses)
#                 )
#                 am_dict["dist_orientation"].update(
#                     statistics.mean(dists[2].tolist()), len(poses)
#                 )
#                 am_dict["angle_diff"].update(
#                     statistics.mean(dists[3].tolist()), len(poses)
#                 )

#                 _logger.info(
#                     f'iter: {i + 1}/{len(val_data_loader)} loss: {am_dict["loss"].val:.4f}({am_dict["loss"].avg:.4f})'
#                 )
#             except Exception:
#                 _logger.exception(str(batch))

#         _logger.info(
#             f'epoch: {epoch}/{_config.TRAIN.epochs}, val loss: {am_dict["loss"].avg:.4f}, time: {time.time() - start_epoch}s'
#         )

#         for k in am_dict:
#             # if k in visual_dict.keys():
#             _tensorboard_writer.add_scalar(k + "_val", am_dict[k].avg, epoch)
#         _tensorboard_writer.flush()


if __name__ == "__main__":
    _logger.info("=================================================\n")
    _logger.info(f"UTC Time: {datetime.datetime.utcnow().isoformat()}")
    _logger.info(f"Device: {_device}")
    _logger.info("Starting new training.")

    _logger.info(f"CONFIG: {json.dumps(_config(), indent=4)}")

    _logger.info(f"Setting seed: {_config.GENERAL.seed}")
    random.seed(_config.GENERAL.seed)
    np.random.seed(_config.GENERAL.seed)
    torch.manual_seed(_config.GENERAL.seed)

    if _use_cuda:
        torch.cuda.manual_seed_all(_config.GENERAL.seed)
        torch.cuda.empty_cache()

    from model.featurenet import FeatureNet, get_criterion
    from data.ycb import YCBDataset, collate

    criterion, miner = get_criterion(device=_device)
    model = FeatureNet(
        in_channels=3, out_channels=_config.STRUCTURE.embedding_size, D=3
    )
    if _use_cuda:
        model.cuda()
    _logger.info(f"Model: {str(model)}")

    if _config.TRAIN.optim == "Adam":
        optimizer = optim.Adam(
            filter(lambda p: p.requires_grad, model.parameters()), lr=_config.TRAIN.lr
        )
    elif _config.TRAIN.optim == "SGD":
        optimizer = optim.SGD(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=_config.TRAIN.lr,
            momentum=_config.TRAIN.momentum,
            weight_decay=_config.TRAIN.weight_decay,
        )

    train_dataset = YCBDataset(set_name="train")
    train_data_loader = DataLoader(
        train_dataset,
        batch_size=_config.DATA.batch_size,
        collate_fn=collate,
        num_workers=_config.DATA.workers,
        shuffle=True,
        drop_last=True,
        pin_memory=True,
        worker_init_fn=utils.seed_worker,
        generator=utils.torch_generator,
    )
    # val_dataset = AliveV1Dataset(set_name="val")
    # val_data_loader = DataLoader(
    #     val_dataset,
    #     batch_size=_config.DATA.batch_size,
    #     collate_fn=collate,
    #     num_workers=max(2, int(_config.DATA.workers/4)),
    #     shuffle=False,
    #     drop_last=False,
    #     pin_memory=True,
    # )

    start_epoch = utils.checkpoint_restore(
        model,
        _config.exp_path,
        _config.config.split("/")[-1][:-5],
        optimizer=optimizer,
        use_cuda=_use_cuda,
    )  # resume from the latest epoch, or specify the epoch to restore

    for epoch in range(start_epoch, _config.TRAIN.epochs + 1):
        train_epoch(train_data_loader, model, optimizer, criterion, miner, epoch)
        if utils.is_multiple(epoch, _config.GENERAL.save_freq) or utils.is_power2(
            epoch
        ):
            utils.checkpoint_save(
                model,
                _config.exp_path,
                _config.config.split("/")[-1][:-5],
                epoch,
                optimizer=optimizer,
                save_freq=_config.GENERAL.save_freq,
                use_cuda=_use_cuda,
            )

        #     eval_epoch(val_data_loader, model, criterion, epoch)

    ipdb.set_trace()

    _logger.info("DONE!")
