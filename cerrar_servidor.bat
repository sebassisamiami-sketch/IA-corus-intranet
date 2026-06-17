@echo off
REM ============================================================
REM  CERRAR SERVIDOR - Pone la app Corus en mantenimiento.
REM  Doble clic para ejecutar (requiere Python y el token de GitHub).
REM ============================================================
cd /d "%~dp0"
echo Cerrando el servidor (modo mantenimiento)...
python control_servidor.py cerrar
echo.
pause
