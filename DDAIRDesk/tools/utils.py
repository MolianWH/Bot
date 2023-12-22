# -*- coding: utf-8 -*-
"""
@Copyright
@FileName   : utils.py
@Author     : MJJ
@Version    :
@Date       : 12/15/2023 5:09 PM 
@Description: 
@Update     :
@Software   : PyCharm
"""

import hashlib
from pydub import AudioSegment
import json
from io import BytesIO


class DotDict(dict):
    """ A dictionary that supports dot notation for key access. """

    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError(f"'DotDict' object has no attribute '{attr}'")

    def __setattr__(self, key, value):
        self[key] = value

def is_json(test_str):
    """
    判断是否是json数据
    Args:
        test_str: 输入文本

    Returns: True or Falseq

    """
    try:
        json_object = int(test_str)  # 即先判断该字符串是否为int
        return False
    except Exception:
        pass

    try:
        json_object = json.loads(test_str)
    except Exception:
        return False
    return True


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


def consistent_hash(question):
    return hashlib.sha256(question.encode()).hexdigest()