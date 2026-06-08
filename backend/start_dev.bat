@echo off
:: Inicia el backend con hot-reload limitado solo a archivos fuente.
:: NO uses "uvicorn main:app --reload" directamente — eso vigila outputs/
:: y node_modules, causando reinicios infinitos durante npm install.
set AI_PROTO_BACKEND_RELOAD=true
python main.py
