# -*- coding: utf-8 -*-
# @Copyright © 2022 DreamDeck. All rights reserved. 
# @FileName   : dd_exception.py
# @Author     : yaowei
# @Version    : 0.0.1
# @Date       : 2022/12/9 11:21
# @Description: write some description here
# @Update    :
# @Software   : PyCharm
class PluginLoadFailException(Exception):
    def __init__(self, msg: str = ''):
        print(msg)
