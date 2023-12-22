# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : DDPluginsTemplate.py
# @Author     : HYD
# @Version    :
# @Date       : 2022/10/28 9:55
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    :
# @Software   : PyCharm

import sys

from tools.read_yaml import read_yaml


class DDPluginsTemplate:
    def __init__(self, yaml_path):
        # 读取配置文件
        # 初始化变量
        # 加载模型
        try:
            self.config = read_yaml(yaml_path, 'PluginsTemplate')
            self.threshold = self.config['threshold']
            self.draw = self.config['draw']
        except:
            print("PluginsTemplate.yaml配置文件出错!")
            sys.exit()

    def __call__(self, arg):
        # 插件功能实现
        return arg

    def __del__(self):
        # 插件销毁
        print("PluginsTemplate closed!")


def get_plugin_class():
    """获取插件类

    Returns:插件

    """
    return DDPluginsTemplate
