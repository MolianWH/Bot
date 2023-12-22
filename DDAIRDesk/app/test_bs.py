# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : test_bs.py
@Author     : MJJ
@Version    :
@Date       : 11/20/2023 12:25 PM 
@Description: 语音TTS+BS测试，BS需要2G显存
@Update     :
@Software   : PyCharm
"""

import time
from pylivelinkface import PyLiveLinkFace, FaceBlendShape

from DDAIRDesk.plugins.HumanSpeech.DDTTS import DDTTS
from DDAIRDesk.plugins.MetaHuman.DDFGAudioFace import DDFGAudioFace


class Test:
    def __init__(self):
        # 注册插件
        yaml_path = "../config/local/TestDDBS.yaml"
        self.TTS = DDTTS(yaml_path)
        self.BS = DDFGAudioFace(yaml_path)
        self.livelink_data = PyLiveLinkFace(name="test",
                                            fps=45,
                                            filter_size=5)
        self.BS.load_model()

    def __call__(self, *args, **kwargs):
        text = input("请输入语音：")
        wav_data = self.TTS(text)
        ba_data = self.BS({"role": "User", "text": text, "wav_stream": wav_data})
        print("BS Over")
        for info in ba_data:  # bs数据实时发送
            role = info.get("role", '')
            bs = info.get("bs", '')
            self.send_ue_bs(bs, role)

    def send_ue_bs(self, face_bs, role):
        '''
        TCP服务器发送到UE
        Args:
            face_bs: 面捕blendshape
            livelink_data: PyLiveLinkFace对象
            udp_client:

        Returns:

        '''
        # 生成面捕blendshape数据
        self.last_end_time = time.time()  # 刷新待机开始时间
        for bs_name, bs_value in face_bs.items():  # 这里做滤波，编码等处理
            self.livelink_data.set_blendshape(FaceBlendShape[bs_name], bs_value)


test = Test()
test()
