#!/bin/bash

# Mata processos que possam estar usando as portas do Backend (8000) e Frontend (5173)
echo "Limpando portas 8000 e 5173..."
fuser -k 8000/tcp 5173/tcp 2>/dev/null || true

# Iniciar o Backend
echo "Iniciando o Backend..."
cd backend
source venv/bin/activate
# Usar uvicorn para garantir que o servidor suba corretamente e com reload
python -m uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Iniciar o Frontend
echo "Iniciando o Frontend..."
cd ../frontend
npm run dev &
FRONTEND_PID=$!

# Função para encerrar ambos os processos ao fechar o script
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" SIGINT SIGTERM

# Manter o script rodando e mostrar logs
echo "Sistema iniciado. Pressione Ctrl+C para encerrar."
wait
