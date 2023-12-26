<h1 align='center'> DDChatFace </h1>

---
**目录**

- [简介](#简介)
- [更新日志](#更新日志)
- [Requirements](#requirements)
- [Usage](#usage)
    - [**Run Demo**](#run-demo)
- [附录](#附录)
    - [附录1： 音色选项](#附录1-音色选项)
    - [附录2：FaceGood到ARKit的转换关系](#附录2facegood到arkit的转换关系)
- [预告内容](#预告内容)

## 简介

本仓库具备以下功能：

- [x] 语音识别
- [x] Chat实时聊天，直接识别语音，通过语音聊天
- [x] TTS实时语音合成
- [x] 通过音频驱动嘴部**20**个blend shape系数，驱动角色动画
- [x] 语音打断
- [x] 添加本地知识库
- [x] 噪音滤波功能
- [x] radis缓存

<p align="center">
<img src="https://www.bilibili.com/video/BV1HN411r7pK/?spm_id_from=333.999.0.0&vd_source=b9aa223b24b6c3fb3c787010de2541c9", width="640">
</p>
<p align="center">DDAudioFace测试<p align="center">


## 更新日志

|            版本号 | 更新内容                                      |
|---------------:|-------------------------------------------|
| 1.0.231225 | 修复缓存bug，修改缓存逻辑，缓存中不再添加音频文件名，简化缓存流程，减少缓存消耗 |
|     1.0.231222 | 增加openai tts; 增加缓存机制；                     |

## Requirements

- tensorflow-gpu 2.6
- cudatoolkit 11.3.1
- cudnn 8.2.1
- pyaudio

Note: test can run with cpu.
（其他安装包请参考插件目录下的[requirements.txt](requirments.txt)）

```shell
conda create -n audio_face python=3.9
conda activate audio_face
pip install -r requirements.txt
```

---

## Usage

### **目录结构说明**

```
.
├── DDAIRDesk         算法包
├── DDLogo.ico
├── README.md
├── Requirments.txt
└── bat               bat脚本，一键启动wsl chat服务和算法
```

### **Run Demo**

运行前需要确保：

- redis连接可用
- DDAIRDesk/face_db目录存在，该目录为人脸图像数据库

通信说明：

UDP客户端，发送UE blendshape。livelink_name为UE livelink中选择的livelink名称。端口固定为11111。

TCP服务端，将ASR识别的语音转文字和Chat对话内容发给UE用于显示。格式为

```
{
    'role': 'User',
    'content': '今天天气怎么样？'
}
```

step1. 开启UE

step2. 运行DDAIRDesk/app/DDChatAppMain.py

step3. 在UE中选择livelink连接名称

**run**

修改DDAIRDesk/config/local/DDAudioFacePluginsConf.yaml配置文件

```shell
python ./DDAIRDesk/app/DDChatAppMain.py
```

--

## 附录

### 附录1： 音色选项

```python
"""
Name: zh-CN-XiaoxiaoNeural
Gender: Female 

Name: zh-CN-XiaoyiNeural
Gender: Female

Name: zh-CN-YunjianNeural
Gender: Male  男听书音

Name: zh-CN-YunxiNeural
Gender: Male  男少年

Name: zh-CN-YunxiaNeural
Gender: Male  男儿童

Name: zh-CN-YunyangNeural
Gender: Male  男新闻主持人

Name: zh-CN-liaoning-XiaobeiNeural
Gender: Female

Name: zh-CN-shaanxi-XiaoniNeural
Gender: Female 女陕西口音

Name: zh-HK-HiuGaaiNeural
Gender: Female

Name: zh-HK-HiuMaanNeural
Gender: Female

Name: zh-HK-WanLungNeural
Gender: Male

Name: zh-TW-HsiaoChenNeural
Gender: Female

Name: zh-TW-HsiaoYuNeural
Gender: Female

Name: zh-TW-YunJheNeural
Gender: Male
"""
```

### 附录2：FaceGood到ARKit的转换关系

驱动的是ARKit 20个嘴部动画。FaceGood到ARKit的转换关系如下：

![FGAudioFace 转 ARKit](./doc/DDFGAudioFace.png)

---

## 预告内容

- 人脸识别
