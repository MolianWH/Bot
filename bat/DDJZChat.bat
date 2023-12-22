:: %1 mshta vbscript:CreateObject("WScript.Shell").Run("%~s0 ::",0,FALSE)(window.close)&&exit

set current_dir=D:\DDAIRSpace\DDJZBot-6.0\

:: STEP 0. start wsl langchain server
start "LangChain" "%current_dir%StartLangChain.bat"

:: STEP 1. start DDFaceFit
start "DDFaceFit" cmd /k "cd DDFaceFit && demo_main.exe"
ping -n 20 127.0>nul

:: STEP 2. start DDAIRDesk
:: call "%current_dir%DDAIRDesk.bat"
start "DDAIRDesk" "%current_dir%DDAIRDesk.bat"
ping -n 10 127.0>nul

:: STEP 3. start UE
start "JingZhang" "D:\DDAIRSpace\JingZhang_T\Windows\JingZhang.exe"
