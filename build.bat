@echo off
REM ---------------------------------------------------------------------------
REM Build RPG Lifer into a single Windows executable: dist\RPGLifer.exe
REM
REM Requirements: Python 3.9+ from python.org (includes Tkinter) on your PATH.
REM Just double-click this file, or run it from a command prompt.
REM ---------------------------------------------------------------------------
setlocal

echo Installing build dependencies...
python -m pip install --upgrade pip || goto :err
python -m pip install pyinstaller || goto :err

echo Building RPGLifer.exe...
pyinstaller --noconfirm --clean packaging\rpglifer.spec || goto :err

echo.
echo ============================================================
echo  Done!  Your app is here:  dist\RPGLifer.exe
echo  Double-click it to play, or copy it anywhere you like.
echo ============================================================
goto :eof

:err
echo.
echo Build failed. Make sure Python 3.9+ is installed and on your PATH.
exit /b 1
