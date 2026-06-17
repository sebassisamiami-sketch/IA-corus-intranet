@echo off
REM ============================================================
REM  ACTIVAR SERVIDOR - Reactiva la app Corus.
REM  Doble clic para ejecutar (requiere Python y el token de GitHub).
REM ============================================================
cd /d "%~dp0"
echo Activando el servidor...
python control_servidor.py activar
echo.
pause
