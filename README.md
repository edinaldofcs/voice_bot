# Voz Realtime com IA

Aplicação de conversa em tempo real usando WebSocket, IA Generativa (Ollama) e Voz.

## Requisitos

- Python 3.10+
- Node.js 18+
- Ollama instalado e rodando (`ollama serve`)
- Modelo `phi3:mini` baixado (`ollama pull phi3:mini`)
- FFmpeg instalado (para conversão de áudio)

## Instalação e Execução

### Método Rápido

Execute o script `start.sh` na raiz do projeto:

```bash
./start.sh
```

Isso iniciará o backend (porta 8000) e o frontend (porta 5173).

### Método Manual

#### Backend

1. Entre na pasta `backend`:
   ```bash
   cd backend
   ```
2. Crie e ative o ambiente virtual:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Execute o servidor:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

#### Frontend

1. Entre na pasta `frontend`:
   ```bash
   cd frontend
   ```
2. Instale as dependências:
   ```bash
   npm install
   ```
3. Execute o servidor de desenvolvimento:
   ```bash
   npm run dev
   ```

## Uso

1. Abra o navegador no endereço indicado pelo frontend (geralmente `http://localhost:5173`).
2. Clique no botão de microfone para começar a gravar.
3. Fale sua mensagem.
4. Clique novamente para parar e enviar.
5. Aguarde a resposta em áudio e texto.
