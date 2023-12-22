# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDHumanPoseRtmPose.py
# @Author     : HYD
# @Version    :
# @Date       : 2023/11/4 12:22
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Update     :
# @Software   : PyCharm


import time
import cv2
import torch
import random
import multiprocessing as mp
from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.tools.read_yaml import read_yaml
from mmdeploy_runtime import PoseTracker


class DDHumanPose(DDBasePlugin):
    def __init__(self, yaml_path):
        """

        Args:
            yaml_path:
        """
        super(DDHumanPose, self).__init__()
        try:
            self.config = read_yaml(yaml_path, 'DDHumanPoseRtmPose')
            self.det_model = self.config['det_model']
            self.pose_model = self.config['pose_model']
            self.device = self.config['device']
        except:
            print("配置文件中DDHumanPoseRtmPose出错!")
            exit()

        self.l_pair = [(0, 1), (0, 2), (1, 3), (2, 4),
                       (5, 6), (5, 7), (7, 9), (6, 8), (8, 10), (5, 11), (6, 12),
                       (11, 12), (11, 13), (13, 15), (12, 14), (14, 16)]
        self.palette = [(255, 128, 0), (255, 153, 51), (255, 178, 102), (230, 230, 0),
                        (255, 153, 255), (153, 204, 255), (255, 102, 255),
                        (255, 51, 255), (102, 178, 255),
                        (51, 153, 255), (255, 153, 153), (255, 102, 102), (255, 51, 51),
                        (153, 255, 153), (0, 0, 255), (102, 255, 102), (255, 0, 0),
                        (51, 255, 51), (0, 255, 0), (255, 255, 255)]

        self.pre_load_model()

    def pre_load_model(self):
        self.tracker = PoseTracker(det_model=self.det_model, pose_model=self.pose_model, device_name=self.device)
        coco_sigmas = [
            0.026, 0.025, 0.025, 0.035, 0.035, 0.079, 0.079, 0.072, 0.072, 0.062,
            0.062, 0.107, 0.107, 0.087, 0.087, 0.089, 0.089
        ]
        self.state = self.tracker.create_state(
            det_interval=1, det_min_bbox_size=100, keypoint_sigmas=coco_sigmas)

    def load_model(self):
        pass

    def unload_model(self):
        pass

    def __call__(self, image, output_img=False):
        """

        Args:
            image: 输入图片
            output_img: 是否输出图片

        Returns:关键点

        """
        img = image.copy()
        results = self.tracker(self.state, img, detect=-1)
        keypoints, boxes, _ = results
        keypoints = keypoints.astype(int)
        if output_img:
            for i in range(len(keypoints)):
                player_data = keypoints[i]
                for index, pair in enumerate(self.l_pair):
                    img = cv2.line(img, (int(player_data[pair[0]][0]), int(player_data[pair[0]][1])),
                                   (int(player_data[pair[1]][0]), int(player_data[pair[1]][1])),
                                   self.palette[index], 3, cv2.LINE_8)
            DDBasePlugin.DDPluginDataFlow['DDHumanPoseRtmPose'] = {'res': keypoints, 'out_img': img}
            return {'res': keypoints, 'out_img': img}
        DDBasePlugin.DDPluginDataFlow['DDHumanPoseRtmPose'] = {'res': keypoints}
        return {'res': keypoints}

    def __del__(self):
        self.tracker = None
        print("DDHumanPoseRtmPose closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDHumanPose
