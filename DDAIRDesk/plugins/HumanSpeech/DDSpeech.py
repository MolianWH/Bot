# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDSpeech.py.py
# @Author     : Dawei TANG
# @Version    :
# @Date       : 2022/11/29 10:05
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    :
# @Software   : PyCharm

import audioop
import json
import time
import wave
import queue
import threading
import copy

import ffmpeg
import numpy as np
import pyaudio
from faster_whisper import WhisperModel
from zhconv import convert
from loguru import logger

from DDAIRDesk.plugins.DDBasePlugin import DDBasePlugin
from DDAIRDesk.tools.read_yaml import read_yaml
from DDAIRDesk.tools.ddio import print_colored, DDFont


class DDSpeech(DDBasePlugin):
    '''
    语音转文字
    '''

    def __init__(self, yaml_path):

        super(DDSpeech, self).__init__()
        try:
            # 首先读取声音的配置
            self.config1 = read_yaml(yaml_path, 'DDSound')
            # 音频流截取设置
            self.chunk = self.config1['chunk']  # Record in chunks of 1024 samples
            self.channels = self.config1['channels']  # 声道数量
            self.sample_rate = self.config1['sample_rate']  # 44100 samples per second

            # 再读取语音识别的配置
            self.config2 = read_yaml(yaml_path, 'DDSpeech')
            self.printSound = self.config2['printSound']
            # 音频流截取设置
            self.startV = self.config2['startV']  # 音量大于此值，则开始录音      # 600
            self.endV = self.config2['endV']  # 音量小于此值一段时间，则停止录音  # 1000
            self.recordMin = self.config2['recordMin']  # 最短录音时长，小于此值，不记录声音
            self.recordMax = self.config2['recordMax']  # 最长录音时长，大于此值，停止记录
            self.recordGap = self.config2['recordGap']  # 允许录音中不说话的时长，必须小于最短录音时长
            self.ttsDecoder = self.config2['ttsDecoder']  # 语音转换器，可以是语音引擎或其他编
            self.model_size = self.config2['model']  # whisper模型大小选择(同faster whisper)
            self.save_cache = self.config2['save_cache']
            self.mode = self.config2['mode']
            self.no_speech_threshold0 = self.config2['no_speech_threshold0']
            self.no_speech_threshold1 = self.config2['no_speech_threshold1']
            self.asr_output = queue.Queue(maxsize=2)
        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()
        except KeyError as e:
            print(f"配置文件{yaml_path}中DDSound和DDSpeech出错!{e}")
            exit()

        # 启用pyaudio
        self.p = pyaudio.PyAudio()

        # 音频保存设置
        self.filename = "LastSound.wav"
        self.file_ind = 0  # 保存音频文件的序号
        self.count = 0  # 记录帧数
        self.frames = {'chunk': [], 'chunk_rms': [], 'chunk_id': []}  # 用于保存数据的帧
        self.recordStatus = 0  # 判断是否开启录音
        self.countRec = 0  # 开始录音的帧数记录
        self.countEnd = 0  # 声音小于阈值的帧数记录
        self.ind = 0
        self.startRec = 0  # 是否开启语音识别
        thread_rec = threading.Thread(name='t_rec', target=self.soundRec)
        thread_rec.start()

    def load_model(self):
        # 本地服务器网址
        if self.ttsDecoder == "whisper":
            import whisper
            self.model = whisper.load_model("medium")  # small
        elif self.ttsDecoder == "faster-whisper":
            # 注意不同显卡支持类型不一样 https://github.com/guillaumekln/faster-whisper/issues/42
            self.model = WhisperModel(self.model_size, device="cuda", compute_type="float16")
        elif self.ttsDecoder == "wenet":
            # self.model = wenet.Decoder(lang='chs')
            exit()

    # 将拾取的语音转成whisper的输入类型
    def load_audio(self, file, sr: int = 16000):
        """
        Open an audio file and read as mono waveform, resampling as necessary

        Parameters
        ----------
        file: (str, bytes)
            The audio file to open or bytes of audio file

        sr: int
            The sample rate to resample the audio if necessary

        Returns
        -------
        A NumPy array containing the audio waveform, in float32 dtype.

        参考https://github.com/openai/whisper/discussions/380
        """
        if isinstance(file, bytes):
            inp = file
            file = 'pipe:'
        else:
            inp = None
        try:
            # This launches a subprocess to decode audio while down-mixing and resampling as necessary.
            # Requires the ffmpeg CLI and `ffmpeg-python` package to be installed.
            out, _ = (
                ffmpeg.input(file, format='s16le', acodec='pcm_s16le', ac=1, ar=sr, threads=0)
                .output("-", format="s16le", acodec="pcm_s16le", ac=1, ar=sr)
                .run(cmd="ffmpeg", capture_stdout=True, capture_stderr=True, input=inp)
            )
        except ffmpeg.Error as e:
            raise RuntimeError(f"Failed to load audio: {e.stderr.decode()}") from e
        except Exception as e:
            print("Failed to load audio2:", e)

        return np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0

    def soundRec(self):
        '''
        faster-whisper参数：
        - no_speech_threshold=0.4,  no-speech概率大于threshold时，返回空数据
        - vad_filter=True  是否启用vad语音活动检测（识别语音信号中的静默段、背景噪声以及非语音声音）
        - vad_parameters   字典，参数参考VADOptions
            - threshold: Speech阈值，默认0.5. Silero VAD输出每个音频块的语音概率，高于此值的概率被认为是speech.
            - min_speech_duration_ms: 短于此值的语音块被丢弃. 单位毫秒，默认值250
            - max_speech_duration_s: 最大持续时间.单位秒，默认值正无穷
            - min_silence_duration_ms: 在每个语音块结束时，等待min_silence_duration_ms，然后将其分离。单位毫秒，默认值2000
            - window_size_samples: silero VAD模型输入音频块大小，默认值1024。该值只能设512, 1024, 1536
            - speech_pad_ms: 最后的语音块由两边的speech_pad_ms填充
        Returns:

        '''
        while 1:
            if self.startRec:
                # self.ind += 1

                # 首先复位语音识别状态
                self.startRec = 0
                length = self.countRec
                # print('Recognizing sound with rms of %i, length of %.1f' % (self.rms, length/18))
                # 保存音频文件测试
                self.file_ind += 1
                if self.save_cache:
                    self.filename = "part_" + str(self.file_ind) + "_" + str(length) + ".wav"
                else:
                    self.filename = "record.wav"
                wf = wave.open(self.filename, 'wb')
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16))
                wf.setframerate(self.sample_rate)
                wf.writeframes(b''.join(self.frames['chunk']))
                wf.close()
                logger.info('录音保存完毕:{}'.format(self.filename))

                # 语音转文字
                wav_file = self.filename
                rec_words = ''
                if self.ttsDecoder == "whisper":
                    btime = time.time()
                    ans = self.model.transcribe(wav_file, language='Chinese')
                    if ans["text"]:
                        if ans['segments'][0]['no_speech_prob'] < 0.2:  # 确定不是噪音
                            rec_words = convert(ans["text"], 'zh-cn')
                            content = [wav_file, ", speech:", rec_words, ans['segments'][0]['no_speech_prob']]
                            print_colored(content, DDFont.GREEN)
                        else:
                            content = [wav_file, ", no speech:", convert(ans["text"], 'zh-cn'),
                                       ans['segments'][0]['no_speech_prob']]
                            print_colored(content, DDFont.RED)
                            rec_words = None
                    else:
                        print("空语音")
                        rec_words = None
                    print(self.ttsDecoder, "推理时间：", time.time() - btime)
                elif self.ttsDecoder == "faster-whisper":
                    btime = time.time()
                    audio = self.load_audio(b''.join(self.frames['chunk']))
                    logger.info('ASR准备识别...')
                    try:
                        segments, info = self.model.transcribe(audio,  # wav_file
                                                               beam_size=1,
                                                               vad_filter=True,  # 识别语音信号中的静默段、背景噪声以及非语音声音
                                                               language='zh',
                                                               no_speech_threshold=self.no_speech_threshold0,  # no-speech概率大于threshold时，返回空数据
                                                               vad_parameters=dict(min_silence_duration_ms=500))
                        rec_words = ''
                        for segment in segments:
                            if self.mode == 0:   # 麦克风模式
                                rec_words += convert(segment.text, 'zh-cn')
                                content = [wav_file, "speech: {}".format(rec_words),
                                           "Pro: {:.2f}".format(segment.no_speech_prob),
                                           "time： {:.2f}".format(time.time() - btime)]
                                print_colored(content, DDFont.GREEN)
                            elif self.mode == 1:  # 讯飞语音板模式
                                if segment.no_speech_prob < self.no_speech_threshold1:
                                    rec_words += convert(segment.text, 'zh-cn')
                                    content = [wav_file, "speech: {}".format(rec_words),
                                               "Pro: {:.2f}".format(segment.no_speech_prob),
                                               "time： {:.2f}".format(time.time() - btime)]
                                    print_colored(content, DDFont.GREEN)
                                else:
                                    content = [wav_file, ", no speech: {}".format(convert(segment.text, 'zh-cn')),
                                               "Pro: {:.2f}".format(segment.no_speech_prob),
                                               "Time： {:.2f}".format(time.time() - btime)]
                                    print_colored(content, DDFont.RED)
                        if rec_words == '':
                            print_colored("faster-whisper没有识别结果。Time:{:.2f}".format(time.time() - btime),
                                          DDFont.YELLOW)
                    except Exception as e:
                        logger.error(f"ASR推理出现异常2：{e}")

                elif self.ttsDecoder == "wenet":
                    ans = self.model.decode_wav(wav_file)
                    rec_words = json.loads(ans)['nbest'][0]['sentence']

                # if rec_words == "":
                #     return None

                # 将文字传到插件内
                DDBasePlugin.DDPluginDataFlow['DDSpeech'] = {'res': rec_words, 'chunk_rms': self.frames['chunk_rms'],
                                                             'chunk_id': self.frames['chunk_id'],
                                                             'chunk_name': self.filename}
                while self.asr_output.qsize() > 0:
                    self.asr_output.get()
                self.asr_output.put({'res': rec_words,
                                     'chunk_rms': self.frames['chunk_rms'],
                                     'chunk_id': self.frames['chunk_id'],
                                     'chunk_name': self.filename})
                # return {'res': rec_words, 'chunk_rms': self.frames['chunk_rms'], 'chunk_id': self.frames['chunk_id'],
                #         'chunk_name': self.filename}
            else:
                time.sleep(0.01)

    def __call__(self, chunk_input):
        """
        Args:
            chunk: 输入音频
        Returns: 识别文字
        """
        if self.asr_output.qsize() > 0:
            return self.asr_output.get()

        chunk = chunk_input['chunk']
        chunk_id = chunk_input['chunk_id']
        chunk_rms = audioop.rms(chunk, 2)  # 检测声音的音量
        if self.printSound:
            print("Listening: %s; rms: %s" % (str(self.count).zfill(3), str(chunk_rms)))  # 打印声音的音量

        # 总是优先加入一帧，以防止录取的声音缺少开头
        self.frames['chunk'].append(chunk)
        self.frames['chunk_rms'].append(chunk_rms)
        self.frames['chunk_id'].append(chunk_id)

        # 声音大于阈值，则开始记录声音
        if chunk_rms >= self.startV:
            self.recordStatus = 1

        if self.recordStatus == 1:
            self.countRec += 1
            # print(datetime.datetime.now().strftime("%H:%M:%S") + ' Sound Detect!')
            # 当录音大于最大时长时, 则直接识别音频
            if self.countRec > self.sample_rate / self.chunk * self.recordMax:
                # if self.countRec > 20 and self.frames['chunk_id'][1]-self.frames['chunk_id'][0]==1:
                self.frames_rec = copy.deepcopy(self.frames)
                self.startRec = 1
                time.sleep(0.1)
                # 更新录音状态与录音数为 0
                self.count = 0
                self.recordStatus = 0
                self.countRec = 0
                self.frames['chunk'] = self.frames['chunk'][-2:]
                self.frames['chunk_rms'] = self.frames['chunk_rms'][-2:]
                self.frames['chunk_id'] = self.frames['chunk_id'][-2:]
                # return
            # print("Listening: %i; rms: %i; countEnd: %i" % (self.countRec, chunk_rms, self.countEnd))  # 打印声音的音量
            # 如果声音小于阈值，则开始记录小于阈值的时间，否则记为0重新开始
            if chunk_rms < self.endV:
                self.countEnd += 1
            else:
                self.countEnd = 0

            # 如果声音持续小于阈值一段时间，则根据音频流长度判断是否识别音频：
            if self.countEnd > self.sample_rate / self.chunk * self.recordGap:
                # 如果声音流长度大于设定值，则保存声音文件
                if self.countRec > self.sample_rate / self.chunk * self.recordMin:
                    # 识别文字
                    # rec_words = self.soundRec()
                    self.frames_rec = copy.deepcopy(self.frames)
                    self.startRec = 1
                    time.sleep(0.1)
                    self.countRec = 0
                    self.frames['chunk'] = self.frames['chunk'][-2:]
                    self.frames['chunk_rms'] = self.frames['chunk_rms'][-2:]
                    self.frames['chunk_id'] = self.frames['chunk_id'][-2:]
                    # return rec_words
                    # return
                # 更新录音状态与录音数为 0
                self.count = 0
                self.recordStatus = 0
        else:
            # 重置录音帧数统计
            self.countRec = 0
            # 如果不处于记录声音的状态，则剔除多余音频
            while len(self.frames['chunk']) >= 5:
                self.frames['chunk'].pop(0)
                self.frames['chunk_rms'].pop(0)
                self.frames['chunk_id'].pop(0)
            self.count += 1
            if self.count > 9999:
                self.count = 0
        return

    def __del__(self):
        print("DDHumanSpeech closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDSpeech
