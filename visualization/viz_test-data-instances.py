import os
import sys
import glob
import pickle
import argparse
import random

import open3d as o3d
import numpy as np

sys.path.append("..")  # noqa
from utils import file_utils
from utils.visualization import create_coordinate_frame, get_kinect_mesh
from utils.data import get_roi_mask

BASE_PATH = os.path.dirname(os.path.abspath(__file__))

import ipdb


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="viz test data")
    parser.add_argument("--data", type=str, default="test_data/")
    parser.add_argument("--ref", type=str, default=None)
    parser.add_argument("--arms", action="store_true")
    args = parser.parse_args()

    kinect_mesh = kinect_mesh = get_kinect_mesh(np.array([0, 0, 0, 1, 0, 0, 0]), coordinate_frame_enabled=True, scale=0.001)

    class_folders = glob.glob(os.path.join(args.data, "*"))
    class_folders = [cf for cf in class_folders if os.path.isdir(cf)]

    sp = args.ref
    if sp is None:
        pickles = glob.glob(os.path.join(class_folders[0], "labeled", "*.pickle"))
        sp = random.choice(pickles)

    data, _ = file_utils.load_alive_file(sp)
    points = data['points']
    rgb = data['rgb']
    pose = data['pose']
    labels = data['labels']
    bg_labels = labels == 0
    points = points[bg_labels]
    rgb = rgb[bg_labels]

    coordinate_frames = list()

    for cf in class_folders:
        print("Processing:", cf)
        pickles = glob.glob(os.path.join(cf, "labeled", "*.pickle"))
        sp = random.choice(pickles)

        data, _ = file_utils.load_alive_file(sp)

        coordinate_frames.append(create_coordinate_frame(data['pose'], switch_w=True, radius=0.005, length=0.15))

        if args.arms:
            arm = data['labels'] == 1
            points = np.concatenate((points, data['points'][arm]), axis=0)
            rgb = np.concatenate((rgb, data['rgb'][arm]), axis=0)

    roi_mask = get_roi_mask(
        points,
        max_z=1.1,
        max_y=0.5,
        min_x=-0.45,
        max_x=0.2,
    )

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(points[roi_mask])
    pcd.colors = o3d.utility.Vector3dVector(rgb[roi_mask])

    # ipdb.set_trace()

    o3d.visualization.draw_geometries(
        [pcd, kinect_mesh] + coordinate_frames,
        # [pcd, kinect_mesh, kinect_frame],
        # [pcd, ee_frame, ref_shapes, obbox],
        zoom=0.5,
        front=[0., -0., -0.1],
        lookat=[0, -0.5, -0.],
        up=[-0., -0.2768, -1.9]
    )
