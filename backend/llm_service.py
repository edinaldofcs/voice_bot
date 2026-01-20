import os
import json
import time
from openai import OpenAI
from dotenv import load_dotenv

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração da OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
Você é um atendente telefônico de cobrança brasileiro profissional.
OBJETIVO: Cobrar uma dívida de forma educada, mas firme.

REGRAS:
1. Responda sempre em Português Brasileiro.
2. Seja direto e conciso. Máximo de 20 palavras por resposta.
3. Não use saudações longas em cada interação.
4. Se o cliente apresentar dificuldades (desemprego, etc), seja empático e ofereça ajuda.
5. IMPORTANTE: Sempre escreva números e valores monetários por extenso para facilitar a leitura da voz (TTS). Exemplo: em vez de "R$ 100,00", escreva "cem reais". Em vez de "R$ 100,23", escreva "cem reais e vinte e três centavos".
"""

def generate_reply_stream(text, history=[]):
    if not os.getenv("OPENAI_API_KEY"):
        yield "Erro: Chave da OpenAI não configurada."
        return

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Adiciona histórico recente
    for msg in history[-6:]:
        role = "assistant" if msg["role"] in ["assistant", "ai"] else "user"
        messages.append({"role": role, "content": msg["text"]})
    
    messages.append({"role": "user", "content": text})

    print(f"[OPENAI-LLM] Iniciando geração (Modelo: gpt-4o-mini)...")
    start_time = time.time()
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            stream=True,
            max_tokens=100,
            temperature=0.7
        )
        
        sentence = ""
        first_chunk = True
        
        for chunk in response:
            if chunk.choices[0].delta.content:
                if first_chunk:
                    print(f"[OPENAI-LLM] Primeiro token recebido em {time.time() - start_time:.2f}s")
                    first_chunk = False
                
                content = chunk.choices[0].delta.content
                sentence += content
                
                # Yield quando encontrar pontuação para iniciar o TTS o quanto antes
                if any(punct in content for punct in [".", "!", "?", ",", "\n"]):
                    if sentence.strip():
                        yield sentence.strip()
                        sentence = ""
        
        if sentence.strip():
            yield sentence.strip()
            
        print(f"[OPENAI-LLM] Geração completa em {time.time() - start_time:.2f}s")
            
    except Exception as e:
        print(f"[OPENAI-LLM] Erro na geração: {e}")
        yield "Desculpe, tive um problema técnico. Pode repetir?"
