import asyncio
import os
import tempfile
import json
import time
import hashlib
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import speech_recognition as sr
from pydub import AudioSegment
import edge_tts
from llm_service import generate_reply_stream
from tree_service import get_tree_response, get_next_possible_responses

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Recognizer
recognizer = sr.Recognizer()

# TTS Voice and Rate
TTS_VOICE = "pt-BR-AntonioNeural" 
TTS_RATE = "+20%" # Aumenta a velocidade em 20%

# Pasta de Cache Permanente para Áudios
TTS_CACHE_DIR = os.path.join(os.path.dirname(__file__), "tts_cache")
if not os.path.exists(TTS_CACHE_DIR):
    os.makedirs(TTS_CACHE_DIR)
print(f"[INIT] Cache de áudio persistente em: {TTS_CACHE_DIR}")

# In-memory session data
sessions = {}

async def get_cached_tts(text):
    """Retorna o conteúdo do áudio (bytes), gerando-o se não estiver no cache persistente."""
    # Criamos um hash do texto, voz e velocidade para o nome do arquivo
    text_hash = hashlib.md5(f"{text}_{TTS_VOICE}_{TTS_RATE}".encode()).hexdigest()
    cache_path = os.path.join(TTS_CACHE_DIR, f"{text_hash}.mp3")
    
    if not os.path.exists(cache_path):
        print(f"[TTS] Gerando novo áudio (rate {TTS_RATE}) para: \"{text[:30]}...\"")
        communicate = edge_tts.Communicate(text, TTS_VOICE, rate=TTS_RATE)
        await communicate.save(cache_path)
    else:
        print(f"[TTS] Usando cache para: \"{text[:30]}...\"")
    
    with open(cache_path, "rb") as f:
        return f.read()

async def generate_and_send_tts(sentence, websocket, client_id, sentence_count):
    """Gera o áudio (ou pega do cache) e envia via websocket."""
    tts_start = time.time()
    audio_data = await get_cached_tts(sentence)
    await websocket.send_bytes(audio_data)
    print(f"[{client_id}] Sentença {sentence_count} Áudio pronto em: {time.time() - tts_start:.4f}s")

async def pre_cache_next_responses(current_state, session_data):
    """Gera o cache de áudio para todas as próximas falas possíveis da árvore."""
    next_texts = get_next_possible_responses(current_state, session_data)
    if not next_texts:
        return
    
    print(f"[CACHE] Pré-carregando {len(next_texts)} possíveis próximas falas...")
    tasks = [get_cached_tts(text) for text in next_texts]
    await asyncio.gather(*tasks)
    print(f"[CACHE] Pré-carregamento concluído.")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(id(websocket))
    sessions[client_id] = {
        "history": [],
        "mode": "ai",
        "tree_state": "START",
        "debt_info": None,
        "nome_cliente": None
    }
    print(f"\n[CONN] Cliente conectado: {client_id}")
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message:
                data = json.loads(message["text"])
                if data.get("type") == "set_mode":
                    sessions[client_id]["mode"] = data.get("mode", "ai")
                    sessions[client_id]["tree_state"] = "START"
                    sessions[client_id]["history"] = []
                    sessions[client_id]["debt_info"] = None
                    sessions[client_id]["nome_cliente"] = None
                    print(f"[{client_id}] Modo: {sessions[client_id]['mode']}")
                continue

            if "bytes" not in message:
                continue

            data = message["bytes"]
            start_time = time.time()
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_input:
                tmp_input.write(data)
                tmp_input_path = tmp_input.name

            wav_path = tmp_input_path + ".wav"

            try:
                # Convert WebM to WAV
                audio = AudioSegment.from_file(tmp_input_path)
                audio.export(wav_path, format="wav")

                # 1. STT: Transcribe
                stt_start = time.time()
                with sr.AudioFile(wav_path) as source:
                    audio_data = recognizer.record(source)
                    try:
                        user_text = recognizer.recognize_google(audio_data, language="pt-BR")
                    except:
                        user_text = ""
                
                if not user_text:
                    continue

                print(f"[{client_id}] STT ({time.time() - stt_start:.2f}s): \"{user_text}\"")
                await websocket.send_json({"type": "user_transcript", "content": user_text})

                mode = sessions[client_id]["mode"]
                session_data = sessions[client_id]
                
                if mode == "tree":
                    # MODO ÁRVORE PROFISSIONAL
                    ai_text, next_state, updates = get_tree_response(user_text, session_data)
                    
                    session_data.update(updates)
                    session_data["tree_state"] = next_state
                    
                    print(f"[{client_id}] Árvore -> {next_state}")
                    
                    await websocket.send_json({"type": "ai_text_chunk", "content": ai_text})
                    await generate_and_send_tts(ai_text, websocket, client_id, 1)
                    await websocket.send_json({"type": "ai_text_complete", "content": ai_text})
                    
                    session_data["history"].append({"role": "user", "text": user_text})
                    session_data["history"].append({"role": "assistant", "text": ai_text})
                    
                    # Proactive Caching: Gera áudios para os próximos estados possíveis em background
                    asyncio.create_task(pre_cache_next_responses(next_state, session_data))
                    
                else:
                    # MODO IA
                    full_ai_text = ""
                    history = session_data["history"]
                    sentence_count = 0
                    
                    for sentence in generate_reply_stream(user_text, history):
                        if not sentence: continue
                        sentence_count += 1
                        full_ai_text += " " + sentence
                        await websocket.send_json({"type": "ai_text_chunk", "content": sentence})
                        await generate_and_send_tts(sentence, websocket, client_id, sentence_count)
                    
                    history.append({"role": "user", "text": user_text})
                    history.append({"role": "assistant", "text": full_ai_text.strip()})
                    await websocket.send_json({"type": "ai_text_complete", "content": full_ai_text.strip()})
                
                print(f"[{client_id}] Ciclo completo em: {time.time() - start_time:.2f}s\n")

            except Exception as e:
                print(f"[{client_id}] Erro: {e}")
            finally:
                if os.path.exists(tmp_input_path): os.unlink(tmp_input_path)
                if os.path.exists(wav_path): os.unlink(wav_path)

    except WebSocketDisconnect:
        print(f"[CONN] Desconectado: {client_id}")
        if client_id in sessions: del sessions[client_id]
