@echo off
REM Abre o Dashboard Unificado no navegador padrao via Streamlit
cd /d "%~dp0"
echo ========================================
echo   Dashboard Unificado - Iniciando...
echo ========================================
echo.
streamlit run app.py
pause
