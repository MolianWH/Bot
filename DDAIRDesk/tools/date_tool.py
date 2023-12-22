# -*- coding: utf-8 -*-
# @Copyright © 2022 DreamDeck. All rights reserved. 
# @FileName   : date_tool.py
# @Author     : https://blog.csdn.net/gymaisyl/article/details/90644222
# @Version    : 0.0.1
# @Date       : 2022/11/23 14:55
# @Description: write some description here
# @Update    :
# @Software   : PyCharm

def datetime_verify(date):
    """判断是否是一个有效的日期字符串"""
    import time
    try:
        if ':' in date:
            time.strptime(date, '%Y-%m-%d %H:%M:%S')
        else:
            time.strptime(date, '%Y-%m-%d')
        return True
    except Exception as e:
        print(e)
        return False
