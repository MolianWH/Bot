@echo off
set current_dir=D:\DDAIRSpace\DDJZBot-6.0\
set current_wsl_dir=/mnt/d/\DDAIRSpace/DDJZBot-6.0/
set conda_env_name=langchain

:: Step 0:  close wsl
:: start /b cmd /k "%current_dir%close_wsl.bat"

:: Step 1. 以管理员身份运行脚本
>nul 2>&1 "%SYSTEMROOT%\system32\cacls.exe" "%SYSTEMROOT%\system32\config\system"
if '%errorlevel%' NEQ '0' (
goto UACPrompt
) else ( goto gotAdmin )
:UACPrompt
echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"
"%temp%\getadmin.vbs"
exit /B
:gotAdmin
if exist "%temp%\getadmin.vbs" ( del "%temp%\getadmin.vbs" )
pushd "%CD%"
CD /D "%~dp0"

:: Step 2. 先关闭虚拟子系统
wsl --shutdown

:: Step 3. 配置IP，以下的Ubuntu-18.04为第4步查到的Linux子系统名称
wsl -d Ubuntu-18.04 -u root ip addr del $(ip addr show eth0 ^| grep 'inet\b' ^| awk '{print $2}' ^| head -n 1) dev eth0
wsl -d Ubuntu-18.04 -u root ip addr add 172.30.16.2/24 broadcast 172.30.16.255 dev eth0
wsl -d Ubuntu-18.04 -u root ip route add 0.0.0.0/0 via 172.30.16.1 dev eth0

powershell -c "Get-NetAdapter 'vEthernet (WSL)' | Get-NetIPAddress | Remove-NetIPAddress -Confirm:$False; New-NetIPAddress -IPAddress 172.30.16.1 -PrefixLength 24 -InterfaceAlias 'vEthernet (WSL)'; Get-NetNat | ? Name -Eq WSLNat | Remove-NetNat -Confirm:$False; New-NetNat -Name WSLNat -InternalIPInterfaceAddressPrefix 172.30.16.0/24;"

::  step 4. 启动对应Linux系统（这一步报错了，但暂时不影响整体运行）
:: wt -p Ubuntu-18.04

:: Step 5: Activate Conda environment and run langchain.sh
wsl bash -c "source /home/dreamdeck/anaconda3/etc/profile.d/conda.sh && conda activate %conda_env_name% && cd %current_wsl_dir% && ./langchain.sh"
ping -n 10 127.0>nul

:: Step 6: Deactivate Conda environment (optional)
:: wsl bash -c "conda deactivate"