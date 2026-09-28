@echo off
chcp 1251 >nul
REM ============================================
REM  J.A.R.V.I.S. - avtomaticheskaya ustanovka
REM  Zapuskat' 1 raz (dvoynoy klik po faylu).
REM ============================================
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py -3") else (set "PY=python")

%PY% --version >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo ERROR: Python ne nayden.
  echo Ustanovite Python: https://www.python.org/downloads/
  echo Na pervom shage otmet'te galochku Add python.exe to PATH
  echo Posle etogo zapustite setup.bat snova.
  pause
  exit /b 1
)

echo [1/3] Obnovlyayu pip...
%PY% -m pip install --upgrade pip --quiet

echo [2/3] Stavlyu biblioteki (nuzhen internet, 3-5 minut)...
%PY% -m pip install SpeechRecognition pyttsx3 pynput pygetwindow psutil requests comtypes PyQt6 PyQt6-WebEngine

echo [3/3] Stavlyu pyaudio (mikrofon)...
%PY% -m pip install pyaudio --quiet
if %errorlevel% neq 0 (
  echo Obychnaya ustanovka ne udalas, probuyu cherez pipwin...
  %PY% -m pip install pipwin --quiet
  %PY% -m pipwin install pyaudio
)

echo.
echo ============================================
echo  GOTOVO! Zapusk: dvoynoy klik na start.bat
echo  Nastroiki: config.json ili knopka v okne.
echo ============================================
pause
