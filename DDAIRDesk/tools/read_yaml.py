# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : read_yaml.py
# @Author     : HYD
# @Version    :
# @Date       : 2022/10/17 11:48
# @Description: 可列出参考连接，如mediapipe的demo连接； 模块功能等
# @Upadate    :
# @Software   : PyCharm

import yaml


def read_yaml_all(yaml_path):
    try:
        # 打开文件
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.load(f, Loader=yaml.FullLoader)
            return data
    except:
        return None


def read_yaml(yaml_path, n):
    # 打开文件
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
        try:
            # 判断传入的n是否在存在
            if n in data.keys():
                return data[n]
            else:
                print(f"n：{n}不存在")
                return None  # add by MJJ. For easy to use
        except Exception as e:
            print(f"key值{e}不存在")
            return None  # add by MJJ.


def write_obj2_yaml(yaml_file_path, yaml_obj, mode='w'):
    from loguru import logger
    with open(yaml_file_path, mode, encoding='utf8') as yf:
        try:
            yaml.dump(yaml_obj, yf, allow_unicode=True)
        except Exception as e:
            logger.error('写入yaml文件时发生异常: {}'.format(e))
