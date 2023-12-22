# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : test_chat.py
@Author     : MJJ
@Version    :
@Date       : 10/13/2023 4:06 PM 
@Description: 
@Update     :
@Software   : PyCharm
"""
import threading
import time

from loguru import logger
from DDAIRDesk.plugins.PluginLoader import PluginLoader
from DDAIRDesk.plugins.HumanSpeech.DDChat import DDChat


class Test:
    def __init__(self):
        # 注册插件
        yaml_path = "../config/local/TestDDChat.yaml"
        # self.plugins_loader = PluginLoader(yaml_path)
        # plugins_dict = self.plugins_loader.get_plugins()
        #
        # self.DDChat = plugins_dict['DDChat']
        self.DDChat = DDChat(yaml_path)
        # self.task = threading.Thread(target=self.stop_chat)

    def __call__(self, *args, **kwargs):
        while True:
            question = input("请输入问题：")
            chat_ans = self.DDChat(question)
            for ans in chat_ans:
                # logger.info("Chat: " + ans + "(T:{:.2f})".format(time.time() - b_time))
                # print(ans+"(T:{:.2f})".format(time.time()-b_time), end='')
                print(ans, end='', flush=True)
                b_time = time.time()
            # self.task.start()

    # def stop_chat(self):
    #     time.sleep(1)
    #     self.DDChat.stop = True
    #     self.DDChat("介绍一下詹天佑？")


test = Test()
test()
