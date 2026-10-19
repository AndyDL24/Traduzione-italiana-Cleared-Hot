@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo === Cleared Hot - Traduzione Italiana ===
echo.
python -c "import UnityPy" 2>nul
if errorlevel 1 (
  echo Installo dipendenza UnityPy...
  python -m pip install -r "%~dp0requirements.txt"
  if errorlevel 1 (
    echo ERRORE: pip / UnityPy. Installa Python 3 e riprova.
    pause
    exit /b 1
  )
)

python "%~dp0tools\injector_gui.py"
if errorlevel 1 pause
