@echo off
set "root_dir=%~dp0"
cd %~dp0\DDAIRDesk\app
set CUDA_VISIBLE_DEVICES=0
D:\Python392_DDAIRDesk\python.exe .\DDChatAppMain.py