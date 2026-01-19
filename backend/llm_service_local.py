import requests
import json
import time

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2:1b"

SYSTEM_PROMPT = """
Você é um atendente telefônico de cobrança brasileiro.
OBJETIVO: Cobrar uma dívida de R$ 100.

REGRAS:
1. Responda sempre em Português Brasileiro.
2. Seja extremamente direto. Máximo de 15 palavras por resposta.
3. Não use saudações longas.
4. FLUXO:
   - Se o histórico NÃO tem o nome/CPF: Pergunte Nome e CPF.
   - Se o histórico JÁ TEM o nome/CPF: Informe a dívida de R$ 100,00 e negocie.
5. MEMÓRIA: Verifique o histórico abaixo para não repetir perguntas.
"""

def generate_reply_stream(text, history=[]):
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    for msg in history:
        role = "assistant" if msg["role"] in ["assistant", "ai"] else "user"
        messages.append({
            "role": role,
            "content": msg["text"]
        })
    
    messages.append({"role": "user", "content": text})

    print(f"[OLLAMA] Iniciando geração (Modelo: {MODEL})...")
    start_time = time.time()
    
    try:
        r = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL, 
                "messages": messages, 
                "stream": True,
                "options": {
                    "num_predict": 50,
                    "temperature": 0.3,
                    "top_p": 0.9
                }
            },
            timeout=60,
            stream=True
        )
        
        sentence = ""
        first_chunk = True
        
        for line in r.iter_lines():
            if line:
                if first_chunk:
                    print(f"[OLLAMA] Primeiro chunk recebido em {time.time() - start_time:.2f}s")
                    first_chunk = False
                
                chunk = json.loads(line)
                content = chunk.get("message", {}).get("content", "")
                sentence += content
                
                if any(punct in content for punct in [".", "!", "?", ",", "\n"]):
                    if sentence.strip():
                        yield sentence.strip()
                        sentence = ""
        
        if sentence.strip():
            yield sentence.strip()
            
        print(f"[OLLAMA] Geração completa em {time.time() - start_time:.2f}s")
            
    except Exception as e:
        print(f"[OLLAMA] Erro na geração: {e}")
