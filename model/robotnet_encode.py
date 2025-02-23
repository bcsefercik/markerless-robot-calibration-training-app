from enum import Enum
from ntpath import join
import ipdb

import torch
import numpy as np
import torch.nn as nn
import torch.nn.functional as F
import MinkowskiEngine as ME

from utils.quaternion import qeuler
from utils.metrics import compute_pose_dist
from utils import config


_config = config.Config()

_backbone = _config()['STRUCTURE'].get('backbone')
if _config.MODE == "inference":
    _backbone = _config.INFERENCE.TRANSLATION.backbone

if _backbone == 'minkunet':
    from model.backbone.minkunet import MinkUNet18D as UNet
elif _backbone == 'minkunet101':
    from model.backbone.minkunet import MinkUNet101 as UNet
elif _backbone == 'minkunet34C':
    from model.backbone.minkunet import MinkUNet34C as UNet
elif _backbone == 'minkunet14A':
    from model.backbone.minkunet import MinkUNet14A as UNet
else:
    from model.backbone.aliveunet import AliveUNet as UNet

M = _config.STRUCTURE.m


class RobotNetEncode(UNet):
    name = "robotnet"

    def __init__(self, in_channels, out_channels, D=3):
        UNet.__init__(self, in_channels, out_channels, D)
        self.global_pool = ME.MinkowskiGlobalAvgPooling()
        # self.global_pool = ME.MinkowskiGlobalMaxPooling()
        self.leaky_relu = nn.LeakyReLU()
        self.final_bn = ME.MinkowskiBatchNorm(out_channels)

        self.output_layer = nn.Sequential(
            ME.MinkowskiBatchNorm(self.PLANES[3] * self.BLOCK.expansion),
            self.relu
        )

        self.pose_regression_input_size = self.PLANES[3] * self.BLOCK.expansion
        if _config.STRUCTURE.use_joint_angles:
            self.pose_regression_input_size += 9

        self.pose_regression = nn.Sequential(
            nn.Linear(self.pose_regression_input_size, 2048),
            nn.LeakyReLU(),
            nn.Linear(2048, out_channels)
        )

        self.quantization_size = _config()["DATA"].get(
            "quantization_size", 1 / _config.DATA.scale
        )
        self.voxelize_position = _config()["DATA"].get(
            "voxelize_position", False
        )

    def forward(self, x):  # WXYZ
        if isinstance(x, tuple):
            x, joint_angles = x

        out = self.conv0p1s1(x)
        out = self.bn0(out)
        out_p1 = self.relu(out)

        out = self.conv1p1s2(out_p1)
        out = self.bn1(out)
        out = self.relu(out)
        out_b1p2 = self.block1(out)

        out = self.conv2p2s2(out_b1p2)
        out = self.bn2(out)
        out = self.relu(out)
        out_b2p4 = self.block2(out)

        out = self.conv3p4s2(out_b2p4)
        out = self.bn3(out)
        out = self.relu(out)
        out_b3p8 = self.block3(out)

        # tensor_stride=16
        out = self.conv4p8s2(out_b3p8)
        out = self.bn4(out)
        out = self.relu(out)
        output = self.block4(out)

        # tensor_stride=8
        # out = self.convtr4p16s2(out)
        # out = self.bntr4(out)
        # output = self.relu(out)
        output = self.output_layer(output)
        output = self.global_pool(output)

        if _config.STRUCTURE.use_joint_angles:
            regression_input = torch.cat((output.features, joint_angles), dim=1)
        else:
            regression_input = output.features

        output = self.pose_regression(regression_input)

        output[:, 7:] = torch.sigmoid(output[:, 7:])  # confidences

        if not self.training:
            output[:, 3:7] = F.normalize(output[:, 3:7], p=2, dim=1)

            if self.voxelize_position:
                output[:, :3] *= self.quantization_size

        return output
