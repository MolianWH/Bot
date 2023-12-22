# -*- coding: utf-8 -*-
# @Copyright © 2022 DreamDeck. All rights reserved. 
# @FileName   : device_info_loader.py
# @Author     : yaowei
# @Version    : 0.0.1
# @Date       : 2022/11/10 15:00
# @Description: write some description here
# @Update    :
# @Software   : PyCharm
# !/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import platform

if platform.system().lower() == "windows":
    import wmi
    import pythoncom


class DeviceInfoLoader:

    def __init__(self):
        self.os_platform = platform.system().lower()  # != 'windows'
        if self.os_platform == 'windows':
            pythoncom.CoInitialize()
            self.c = wmi.WMI()
            cpu_info = self._get_cpu_info()
            board_info = self._get_board_info()
            disk_info = self._get_disk_info()
            memory_info = self._get_memory_info()
            self._device_info = ''.join([cpu_info, board_info, disk_info, memory_info])
            pythoncom.CoUninitialize()
        elif self.os_platform == 'linux':  # Linux UUID
            cmd = "blkid -o value | head -1 | awk '{print $NF}'"
            output = os.popen(cmd)
            self._device_info = output.read()
        else:  # TODO Linux平台判断及信息获取
            # Linux and MacOS only need to get serial or UUID. This is UUID
            cmd = "/usr/sbin/system_profiler SPHardwareDataType | fgrep 'UUID' | awk '{print $NF}'"
            output = os.popen(cmd)
            self._device_info = output.read()

    def _get_cpu_info(self):
        cpu_info = []
        for cpu in self.c.Win32_Processor():
            cpu_info.append(cpu.ProcessorId.strip())
        return ''.join(cpu_info)

    def _get_board_info(self):
        board_info = []
        for board in self.c.Win32_BaseBoard():
            board_info.append(board.qualifiers['UUID'][1:-1])
        return ''.join(board_info)

    def _get_disk_info(self):
        disk_info = []
        for disk in self.c.Win32_DiskDrive():
            disk_info.append(disk.SerialNumber.strip())
        return ''.join(disk_info)

    def _get_memory_info(self):
        memory_info = []
        for memory in self.c.Win32_PhysicalMemory():
            memory_info.append(memory.qualifiers['UUID'][1:-1])
        return ''.join(memory_info)

    @property
    def device_info(self):
        return self._device_info


if __name__ == "__main__":
    device_info_loader = DeviceInfoLoader()
    device_info = device_info_loader.device_info
    print(device_info)