# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDTTS.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 7/24/2023
# @Description: 
# @Upadate    : 添加openai-tts-1方式
# @Software   : PyCharm
import threading
import time
from io import BytesIO
import asyncio
from loguru import logger
import aiohttp

import edge_tts
from pydub import AudioSegment

from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.tools.read_yaml import read_yaml

VOICE_LIST = {"edge-tts": ["zh-CN-XiaoxiaoNeural", "zh-CN-XiaoyiNeural", "zh-CN-YunjianNeural", "zh-CN-YunxiNeural",
                           "zh-CN-YunxiaNeural", "zh-CN-YunyangNeural", "zh-CN-liaoning-XiaobeiNeural",
                           "zh-CN-shaanxi-XiaoniNeural", "zh-HK-HiuGaaiNeural", "zh-HK-HiuMaanNeural",
                           "zh-HK-WanLungNeural", "zh-TW-HsiaoChenNeural", "zh-TW-HsiaoYuNeural", "zh-TW-YunJheNeural"],
              "openai-tts-1": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]}


def mp3_to_wav(mp3_stream):
    """mp3音频流转wav音频流

    Args:
        mp3_stream (bytes): mp3音频字节流

    Returns:
        bytes: wav音频流
    """
    audio_segment = AudioSegment.from_file(BytesIO(mp3_stream), format="mp3")
    wav_stream = BytesIO()
    audio_segment.export(wav_stream, format="wav")
    return wav_stream.getvalue()


class DDTTS(DDBasePlugin):
    """
    文本转语音：edge-tts
    """

    def __init__(self, yaml_path):
        super(DDTTS, self).__init__()

        try:
            self.config = read_yaml(yaml_path, 'DDTTS')
            self._voice = self.config['voice']
            self.rate = self.config['rate']
            self.volume = self.config['volume']
            # self.voice_list = self.config.get('voice_list', [])
            self.model = self.config.get('model', 'edge-tts')
            self.url = self.config.get("url", "https://aigptx.top/v1/audio/speech")
            self.headers = {
                "Authorization": self.config.get("api-key", ""),
                "Content-Type": "application/json"
            }
        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()
        except KeyError as e:
            print(f"配置文件{yaml_path}中DDTTS出错!{e}")
            exit()

        if self.model == 'edge-tts':
            self.tts = self.run_edge_tts
        elif self.model == 'openai-tts-1':
            self.tts = self.run_openai_tts
        else:
            logger.error("TTS Model Name Error. Use edge-tts OR openai-tts-1")

        self.stop = False
        self.event_over = threading.Event()
        self.loop = asyncio.get_event_loop()

    @property
    def voice(self):
        return self._voice

    @voice.setter
    def voice(self, voice):
        self._voice = voice

    def __call__(self, in_data):
        msg = in_data
        try:
            # return asyncio.run(self.tts(msg))
            result = self.loop.run_until_complete(self.tts(msg))
            return result
        except Exception as e:
            print("TTS 异步打断出现异常:", e)
            return b''

    async def run_openai_tts(self, msg, voice=''):
        if voice not in VOICE_LIST['openai-tts-1']:
            voice = self._voice
        self.event_over.clear()
        self.stop = False
        data = {
            "model": "tts-1",
            "voice": voice,
            "input": msg,
            'response_format': 'mp3',
        }
        # logger.info("TTS请求:{}".format(msg))
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=self.headers, json=data) as response:
                # 读取响应内容为字节序列
                data = await response.read()
                if not isinstance(data, bytes):
                    data = b''
        if data != b'':
            wav_stream = mp3_to_wav(data)[64:-200]  # 删除每段音频合成后末尾的空白
        else:
            wav_stream = b''
        logger.info("TTS Over")
        return wav_stream

    async def run_edge_tts(self, msg, voice=''):
        """
        edge-tts文本转语音
        Args:
            msg: 文本信息
            voice: 音色代码

        Returns:

        """
        if voice not in VOICE_LIST['edge-tts']:
            voice = self._voice
        self.event_over.clear()
        self.stop = False
        # logger.info("TTS请求:{}".format(msg))
        communicate = edge_tts.Communicate(
            text=msg, voice=voice, rate=self.rate, volume=self.volume
        )
        # logger.info("TTS请求成功:{}".format(msg))
        data = b''
        try:
            async for chunk in communicate.stream():
                # logger.info("TTS正在处理...")
                if self.stop:
                    data = b''
                    logger.info("打断DDTTS...")
                    # self.event_over.set()
                    break
                if chunk["type"] == "audio":
                    data += chunk["data"]
                await asyncio.sleep(0.01)
        except Exception as e:
            logger.error(e)
        if data != b'':
            wav_stream = mp3_to_wav(data)[64:-200]  # 删除每段音频合成后末尾的空白
        else:
            wav_stream = b''
        logger.info("TTS Over")
        return wav_stream


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDTTS
