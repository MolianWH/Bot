# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : PluginLoader.py
# @Author     : HYD
# @Version    :
# @Date       : 2022/10/15 17:44
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    :
# @Software   : PyCharm

import os
import sys

from DDAIRDesk.tools.read_yaml import read_yaml_all


class PluginLoader:
    '''
    插件加载
    '''

    def __init__(self, yaml_path, deploy=False):
        try:
            self.config = read_yaml_all(yaml_path)
        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()

        self.deploy = deploy
        if deploy is True:
            self.path_list = []
        self.plugins_name = list(self.config.keys())
        self.plugins_dict = {}
        path = "../plugins"
        self.load_plugins(yaml_path, path)

        if deploy is True:
            print("查询所有py插件路径成功！")
        else:
            print("所有插件注册成功!")

    def load_plugins(self, yaml_path, path="../plugins"):
        """插件注册函数

        Args:
            path: 插件所在文件夹路径

        Returns:

        """
        sys.path.append(path)
        for filename in os.listdir(path):
            paths = path + "/" + filename
            if os.path.isdir(paths):
                self.load_plugins(yaml_path, path=paths)
            else:
                # if not filename.endswith(".py") or filename.startswith("_") or filename == "PluginLoader.py":
                if not filename.endswith(".py") or filename[:2] != "DD":
                    if not filename.endswith(".pyd"):
                        continue

                plugin_name = os.path.splitext(filename)[0]
                if plugin_name in self.plugins_name:

                    # 查询所有py插件路径
                    if self.deploy is True:
                        paths = paths.split('..')[-1]
                        self.path_list.append(paths)
                        continue

                    plugin = __import__(plugin_name, fromlist=[plugin_name])
                    classname = plugin.get_plugin_class()
                    plugin_instance = classname(yaml_path)
                    try:
                        if plugin_instance.is_activated():
                            self.plugins_dict[plugin_name] = plugin_instance
                        else:
                            print('插件{}没有激活'.format(plugin_name))
                            sys.exit()
                    except Exception as e:
                        print('插件{}没有正确继承父类：{}'.format(plugin_name, e))
                        sys.exit()

    def get_plugins(self):
        """获取注册的插件

        Returns:注册的插件

        """
        return self.plugins_dict

    def release_plugins(self, name):
        del self.plugins_dict[name]

    def release_all_plugins(self):
        """注销所有插件

        Returns:

        """
        self.plugins_dict.clear()


class PluginLoaderMini:
    '''
        静态插件加载，适用于京张项目打包
    '''

    def __init__(self, yaml_path, deploy=False):
        from DDAIRDesk.plugins.DataSource.DDCamera import DDCamera
        from DDAIRDesk.plugins.DataSource.DDSound import DDSound
        from DDAIRDesk.plugins.HumanSpeech.DDSpeech import DDSpeech
        from DDAIRDesk.plugins.HumanSpeech.DDChat import DDChat
        from DDAIRDesk.plugins.HumanSpeech.DDTTS import DDTTS
        from DDAIRDesk.plugins.MetaHuman.DDFGAudioFace import DDFGAudioFace
        from DDAIRDesk.plugins.HumanFace.DDFaceRecognition import DDFaceRecognition
        from DDAIRDesk.plugins.HumanBody.DDHumanPoseRtmPose import DDHumanPose
        try:
            self.config = read_yaml_all(yaml_path)
        except FileNotFoundError as e:
            print(f"配置文件{yaml_path}不存在：{e}")
            exit()

        self.deploy = deploy
        if deploy is True:
            self.path_list = []
        self.plugins_name = ["DDCamera", "DDSound", "DDSpeech", "DDChatBot", "DDFGAudioFace",
                             "DDFaceRecognition", "DDHumanDetection"]
        self.plugins_dict = dict()
        self.plugins_dict["DDCamera"] = DDCamera(yaml_path)
        self.plugins_dict["DDSound"] = DDSound(yaml_path)  # 必须静态导入，并且引用了打包时才能打包进去。动态导入和动态实例化都会在打包时忽略该模块
        self.plugins_dict["DDSpeech"] = DDSpeech(yaml_path)
        self.plugins_dict["DDChat"] = DDChat(yaml_path)
        self.plugins_dict["DDTTS"] = DDTTS(yaml_path)
        self.plugins_dict["DDFGAudioFace"] = DDFGAudioFace(yaml_path)
        self.plugins_dict["DDFaceRecognition"] = DDFaceRecognition(yaml_path)
        self.plugins_dict["DDHumanPose"] = DDHumanPose(yaml_path)
        # for plugin_name in self.plugins_name:
        #     plugin_instance = eval(plugin_name)(yaml_path)
        #     self.plugins_dict[plugin_name] = plugin_instance
        for plugin_name, plugin_instance in self.plugins_dict.items():
            try:
                if plugin_instance.is_activated():
                    self.plugins_dict[plugin_name] = plugin_instance
                else:
                    print('插件{}没有激活'.format(plugin_name))
                    sys.exit()
            except Exception as e:
                print('插件{}没有正确继承父类：{}'.format(plugin_name, e))
                sys.exit()

        if deploy is True:
            print("查询所有py插件路径成功！")
        else:
            print("所有插件注册成功!")

    def get_plugins(self):
        """获取注册的插件

        Returns:注册的插件

        """
        return self.plugins_dict

    def release_plugins(self, name):
        del self.plugins_dict[name]

    def release_all_plugins(self):
        """注销所有插件

        Returns:

        """
        self.plugins_dict.clear()
