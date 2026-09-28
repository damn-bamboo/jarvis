@echo off
REM ============================================
REM  J.A.R.V.I.S. - avtomaticheskaya podgotovka
REM  Zapuskat' 1 raz (dvoynoy klik po faylu).
REM  Sam skachaet portativnyy Python 3.12 v papku proekta
REM  i sozdat izolirovannoe okruzhenie .venv.
REM  SYSTEMNYE Python i biblioteki NE MENYAYUTSYA.
REM  Vse deystviya - v fayle bootstrap.py.
REM ============================================
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "BOOT=py -3") else (set "BOOT=python")

%BOOT% --version >nul 2>&1
if %errorlevel% neq 0 (
  echo.
  echo ERROR: Ne nayden nikakoy Python. On nuzhen tolko odin raz,
  echo chtoby nachat' ustanovku. Dalshe DzhARVIS rabotaet AVTONOMNO
  echo v svoey papke i bol'she vashego Python ne sprosit.
  echo.
  echo Skachayte lyuboy sovremennyi Python: https://www.python.org/downloads/windows/
  echo Na pervom shage otmet'te galochku Add python.exe to PATH.
  echo Posle etogo zapustite setup.bat snova.
  pause
  exit /b 1
)

%BOOT% bootstrap.py
if %errorlevel% neq 0 (
  echo.
  echo PODGOTOVKA ZAKONCHILAS OSHIBKOY. Tekst vyshe.
  pause
)
