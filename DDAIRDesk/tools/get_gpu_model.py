# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : get_gpu_model.py
# @Author     : HYD
# @Version    :
# @Date       : 2022/10/21 15:03
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    :
# @Software   : PyCharm

import re
from pynvml import nvmlInit, nvmlDeviceGetName, nvmlDeviceGetHandleByIndex


def get_gpu_model():
    """

    Returns:返回gpu型号(10系列显卡返回"RTX_10"，20系列显卡返回"RTX_20")

    """
    s_gpu_model = "RTX_20"
    try:
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        s_gpu_model = str(nvmlDeviceGetName(handle))
        s_gpu_model = re.findall(r"\d+", s_gpu_model)[0][:2]

        if s_gpu_model == "10":
            s_gpu_model = "RTX_10"
        elif s_gpu_model == "16":
            s_gpu_model = "RTX_16"
        elif s_gpu_model == "20":
            s_gpu_model = "RTX_20"
        else:
            print("Can not get gpu,default to use RTX_20!")
    except:
        print("Can not get gpu,default to use RTX_20!")
    return s_gpu_model