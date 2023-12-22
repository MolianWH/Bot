# -*- coding: utf-8 -*-
# @Copyright
# @FileName   : ddio.py
# @Author     : MJJ
# @Version    : 0.X.23XXXX
# @Date       : 6/30/2023
# @Description: 输入输出
# @Upadate    : 
# @Software   : PyCharm

import time


class DDFont:
    # 设置颜色和样式的控制序列
    BLACK = '\033[30m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    WHITE = '\033[37m'
    BOLD = '\033[1m'
    RESET = '\033[0m'


def print_colored(text, color: DDFont = DDFont.WHITE, size: int = 16):
    """打印带颜色输出
    Args:
        text: 打印内容
        color_code: 颜色
        size: 字体大小

    Returns:
    """
    # print(f"\033[{color_code}m{text}\033[0m")
    print(color + f"\033[{size}m" + str(text) + DDFont.RESET)


def wait_interval(interval):
    """
    定时触发装饰器。可认为是定时器。这里用于打印
    Args:
        interval: 时间间隔

    Returns:

    """

    def decorator(func):
        last_time = 0

        def wrapper(*args, **kwargs):
            nonlocal last_time
            current_time = time.time()

            if current_time - last_time >= interval:
                func(*args, **kwargs)
                last_time = current_time

        return wrapper

    return decorator


@wait_interval(5)
def print_interval(text, color: DDFont = DDFont.WHITE, size: int = 16):
    """
    定时打印。每隔5秒打印一次，防止频繁打印
    Args:
        text: 输入文本

    """
    print_colored(text, color=color, size=size)
