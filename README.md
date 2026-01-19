# 🎙️ Voz Realtime AI - MVP de Cobrança Inteligente

Uma solução de ponta para comunicação por voz em tempo real, integrando Inteligência Artificial Generativa e Fluxos de Decisão Estruturados. Este projeto foi desenvolvido para simular uma operação de cobrança profissional com latência ultra-baixa e experiência de usuário fluida.

---

## 🚀 Funcionalidades Principais

- **Comunicação Full-Duplex**: Interação por voz em tempo real via WebSockets.
- **Modos de Operação Duplos**:
  - **IA Generativa**: Conversa livre e contextual utilizando OpenAI `gpt-4o-mini`.
  - **Fluxo de Árvore (Decision Tree)**: Máquina de estados profissional para negociação de dívidas, com caminhos dinâmicos para objeções (desemprego, contestação, etc.).
- **Barge-in (Interrupção)**: A IA interrompe a fala imediatamente quando detecta a voz do usuário, permitindo um diálogo natural.
- **Latência Ultra-Baixa**:
  - **Streaming de Áudio**: Respostas processadas em chunks para início imediato da fala.
  - **Cache Persistente de TTS**: Áudios de frases recorrentes são cacheados em disco, reduzindo o tempo de resposta para milissegundos.
- **Extração Inteligente de Dados**: Identificação automática de Nome e CPF durante a conversa.
- **Interface Premium**: UI moderna com visualizador de voz dinâmico, status badges e design responsivo.

---

## 🛠️ Tecnologias Utilizadas

### Backend
- **FastAPI**: Framework web de alta performance.
- **OpenAI API**: Cérebro da aplicação (gpt-4o-mini).
- **Edge-TTS**: Geração de voz de alta qualidade com controle de velocidade.
- **SpeechRecognition**: Transcrição de áudio para texto (STT).
- **Pydub**: Manipulação e conversão de formatos de áudio.

### Frontend
- **React + Vite**: Interface rápida e reativa.
- **Web Audio API**: Processamento de áudio no navegador e VAD (Voice Activity Detection).
- **CSS3 (Vanilla)**: Design moderno com Glassmorphism e animações.

---

## 📋 Pré-requisitos

- **Python 3.10+**
- **Node.js 18+**
- **FFmpeg**: Necessário para a conversão de áudio no backend.
- **Chave de API da OpenAI**: Necessária para o processamento de linguagem natural.

---

## ⚙️ Instalação e Configuração

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/edinaldofcs/voice_bot.git
   cd voice_bot
   ```

2. **Configure as variáveis de ambiente**:
   Crie um arquivo `.env` dentro da pasta `backend/`:
   ```bash
   OPENAI_API_KEY=sua_chave_aqui
   ```

3. **Instalação Automática**:
   O projeto conta com um script que automatiza a limpeza de portas e inicialização:
   ```bash
   chmod +x start.sh
   ./start.sh
   ```

---

## 📖 Como Usar

1. Acesse `http://localhost:5173` no seu navegador.
2. Escolha entre o modo **IA Generativa** (conversa livre) ou **Fluxo de Árvore** (negociação estruturada).
3. Clique no botão de telefone para iniciar a chamada.
4. Fale naturalmente. O sistema detectará o fim da sua frase (após 500ms de silêncio) ou permitirá que você interrompa a IA a qualquer momento.
5. No modo Árvore, tente informar dados como: *"Meu nome é João e meu CPF é 12345678901"* para ver a integração com a API mock.

---

## 📁 Estrutura do Projeto

```text
.
├── backend/
│   ├── main.py            # Servidor FastAPI e lógica de WebSocket
│   ├── tree_service.py    # Lógica da Máquina de Estados (Árvore)
│   ├── llm_service.py     # Integração com OpenAI (Streaming)
│   ├── tts_cache/         # Cache persistente de arquivos de áudio
│   └── requirements.txt   # Dependências Python
├── frontend/
│   ├── src/
│   │   ├── App.jsx        # Componente principal e lógica de áudio
│   │   └── index.css      # Estilização premium
│   └── package.json       # Dependências Node.js
└── start.sh               # Script de inicialização rápida
```

---

## 📄 Licença

Este projeto é um MVP para fins de demonstração técnica. Sinta-se à vontade para explorar e expandir!
