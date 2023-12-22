# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDChatFace.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 6/19/2023
# @Description: 
# @Upadate    : 
# @Software   : PyCharm
import os, sys
# import psutil

cur_path = os.getcwd()
# workpath
os.chdir(cur_path)
# python search path
sys.path.append(os.path.dirname(os.path.dirname(cur_path)))
from DDAIRDesk.app.DDChatBot import DDChatBot

# os.environ["CUDA_VISIBLE_DEVICES"] = "1"


def run_app():
    """
    运行接口
    Returns:

    """
    remote_conf = "../config/remote/DDAudioFaceRemoteConf.yaml"
    chatbot = DDChatBot(remote_conf)
    chatbot.load_model()
    chatbot()
    chatbot.shutdown_gracefully()


if __name__ == "__main__":
    # p = psutil.Process(os.getpid())
    # for dll in p.memory_maps():
    #     print(dll.path)
    run_app()
