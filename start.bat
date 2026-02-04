@echo off
echo Limpando portas 8000 e 5173...
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

echo Iniciando o Backend...
cd backend
if not exist venv (
    echo Criando ambiente virtual...
    python -m venv venv
    call venv\Scripts\activate
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate
)
start /B python main.py

echo Iniciando o Frontend...
cd ../frontend
if not exist node_modules (
    echo Instalando dependências do Frontend...
    npm install
)
start /B npm run dev -- --host

echo Sistema iniciado. Abra o navegador em http://localhost:5173
echo Pressione Ctrl+C para encerrar (ou feche esta janela).
pause
