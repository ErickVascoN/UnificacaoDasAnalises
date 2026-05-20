@echo off
REM Agendador de Tarefas do Windows deve apontar para este arquivo.
REM Ele ativa o venv e executa o script de relatório diário.

cd /d "%~dp0.."
call venv\Scripts\activate.bat
python scripts\relatorio_diario_corte.py
