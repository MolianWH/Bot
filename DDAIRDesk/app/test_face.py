# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : test_face.py
@Author     : MJJ
@Version    :
@Date       : 12/12/2023 8:29 PM 
@Description: 
@Update     :
@Software   : PyCharm
"""
import threading
import time

import cv2
from loguru import logger
from DDAIRDesk.plugins.PluginLoader import PluginLoader
from DDAIRDesk.plugins.DataSource.DDCamera import DDCamera
from DDAIRDesk.plugins.HumanFace.DDFaceRecognition import DDFaceRecognition


class Test:
    def __init__(self):
        # 注册插件
        yaml_path = "../config/local/DDAudioFacePluginsConf.yaml"
        # self.plugins_loader = PluginLoader(yaml_path)
        # plugins_dict = self.plugins_loader.get_plugins()
        #
        # self.DDChat = plugins_dict['DDChat']
        self.camera = DDCamera(yaml_path)
        self.DDFaceRecognition = DDFaceRecognition(yaml_path)
        self.DDFaceRecognition.load_model()
        # self.task = threading.Thread(target=self.stop_chat)

    def __call__(self, *args, **kwargs):
        self.camera()
        for img in self.camera:
            if img is not None:
                res = self.DDFaceRecognition(img, True)
                pose = res["res"]
                cv2.imshow("res", res["out_img"])
                cv2.waitKey(1)


test = Test()
test()
