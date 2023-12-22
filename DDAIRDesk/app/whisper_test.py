# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : whisper_test.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 8/23/2023
# @Description: 
# @Upadate    : 
# @Software   : PyCharm
import time

from loguru import logger
from DDAIRDesk.plugins.PluginLoader import PluginLoader


class Test:
    def __init__(self):
        # 注册插件
        yaml_path = "../config/local/DDSpeechTest.yaml"
        self.plugins_loader = PluginLoader(yaml_path)
        plugins_dict = self.plugins_loader.get_plugins()

        self.DDSound = plugins_dict['DDSound']
        self.DDSpeech = plugins_dict["DDSpeech"]  # ASR
        self.DDSpeech.load_model()

    def __call__(self, *args, **kwargs):
        self.DDSound()
        for sound in self.DDSound:
            if sound['chunk'] == b'':
                time.sleep(0.01)
                continue
            output = self.DDSpeech(sound)
            if output is not None and output['res']:
                logger.info(output['res'])


test = Test()
test()