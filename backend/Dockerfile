# Use a imagem oficial do Python baseada em Alpine para leveza
FROM python:3.12-alpine

# Instala dependências do sistema necessárias para processamento de áudio (FFmpeg e FLAC)
# build-base é necessário para compilar algumas dependências de Python se necessário
RUN apk add --no-cache \
    ffmpeg \
    flac \
    build-base \
    libffi-dev

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia o arquivo de requisitos primeiro para aproveitar o cache das camadas do Docker
COPY requirements.txt .

# Instala as dependências do Python
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do backend para o container
COPY . .

# Cria a pasta de cache de áudio se não existir
RUN mkdir -p tts_cache

# Expõe a porta que o FastAPI utiliza
EXPOSE 8000

# Comando para iniciar o servidor
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
