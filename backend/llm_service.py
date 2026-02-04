import os
import json
import time
import httpx
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
5. IMPORTANTE: Sempre escreva números e valores monetários por extenso.
6. Se o usuário fornecer um CPF, use IMEDIATAMENTE a ferramenta `get_debt_info`.

MEMÓRIA E FLUXO:
- Antes de pedir qualquer coisa, VERIFIQUE NO HISTÓRICO se a informação já foi dada ou se você já chamou a ferramenta `get_debt_info`.
- Se você já chamou `get_debt_info` e recebeu os dados (nome, valor, empresa), NÃO PEÇA O CPF NOVAMENTE. Use os dados recebidos para negociar.
- Se o cliente aceitar o pagamento, use a ferramenta `fechar_acordo`.

FERRAMENTAS:
- `get_debt_info`: Consulta dívida, nome e score pelo CPF.
- `fechar_acordo`: Registra o fechamento do acordo.
"""

def get_debt_info(cpf: str):
    """Consulta informações de dívida na API Mock."""
    clean_cpf = "".join(filter(str.isdigit, cpf))
    try:
        with httpx.Client() as h_client:
            response = h_client.get(f"http://localhost:8001/debts/{clean_cpf}", timeout=2.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[LLM-TOOL ERROR] {e}")
    return {"error": "Não foi possível localizar os dados para este CPF."}

def fechar_acordo(cpf: str, condicao: str):
    """Registra o fechamento do acordo no sistema."""
    print(f"[LLM-TOOL] ACORDO FECHADO: CPF {cpf} em condição {condicao}")
    return {"status": "sucesso", "mensagem": "Acordo registrado com sucesso!"}

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_debt_info",
            "description": "Busca informações de dívida, nome e score do cliente pelo CPF",
            "parameters": {
                "type": "object",
                "properties": {
                    "cpf": {"type": "string", "description": "O CPF do cliente (apenas números)"}
                },
                "required": ["cpf"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "fechar_acordo",
            "description": "Finaliza a negociação e registra o acordo",
            "parameters": {
                "type": "object",
                "properties": {
                    "cpf": {"type": "string", "description": "O CPF do cliente"},
                    "condicao": {"type": "string", "description": "A condição aceita (ex: à vista, parcelado em 3x)"}
                },
                "required": ["cpf", "condicao"]
            }
        }
    }
]

def generate_reply_stream(text, history=[]):
    if not os.getenv("OPENAI_API_KEY"):
        yield "Erro: Chave da OpenAI não configurada."
        return

    # Prepara as mensagens para a OpenAI
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Converte o histórico para o formato da OpenAI
    for msg in history[-10:]:
        if "tool_calls" in msg:
            # Garante que content seja None se estiver vazio para evitar erros na API
            content = msg.get("text") or None
            messages.append({"role": "assistant", "content": content, "tool_calls": msg["tool_calls"]})
        elif msg["role"] == "tool":
            messages.append({"role": "tool", "tool_call_id": msg["tool_call_id"], "name": msg["name"], "content": msg["content"]})
        else:
            role = "assistant" if msg["role"] in ["assistant", "ai"] else "user"
            messages.append({"role": role, "content": msg["text"]})
    
    # Adiciona a mensagem atual do usuário
    user_msg = {"role": "user", "content": text}
    messages.append(user_msg)
    
    print(f"[LLM-CONTEXT] Enviando {len(messages)} mensagens no contexto.")
    
    # Adiciona ao histórico mutável para persistência (apenas se não for repetido)
    history.append({"role": "user", "text": text})

    try:
        # 1. Primeira chamada para verificar se precisa de ferramenta
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        response_message = response.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            print(f"\n[TOOL_CALL] O Agente decidiu chamar uma função!")
            
            # Adiciona a chamada ao contexto e ao histórico
            messages.append(response_message)
            history.append({
                "role": "assistant", 
                "text": response_message.content, 
                "tool_calls": [tc.model_dump() for tc in tool_calls]
            })

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_result = {}
                if function_name == "get_debt_info":
                    cpf = function_args.get('cpf')
                    print(f"[TOOL_CALL] Função: {function_name} | Argumentos: {function_args}")
                    tool_result = get_debt_info(cpf)
                    print(f"[TOOL_RESULT] Resultado da API: {tool_result}\n")
                elif function_name == "fechar_acordo":
                    print(f"[TOOL_CALL] Função: {function_name} | Argumentos: {function_args}")
                    tool_result = fechar_acordo(function_args.get("cpf"), function_args.get("condicao"))
                    print(f"[TOOL_RESULT] Resultado: {tool_result}\n")

                # Adiciona o resultado ao contexto e ao histórico
                tool_msg = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": json.dumps(tool_result)
                }
                messages.append(tool_msg)
                history.append(tool_msg)
            
            # 2. Segunda chamada com o resultado da ferramenta (agora com stream)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )
        else:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True
            )

        sentence = ""
        full_ai_text = ""
        for chunk in response:
            if chunk.choices[0].delta.content:
                content = chunk.choices[0].delta.content
                sentence += content
                full_ai_text += content
                if any(punct in content for punct in [".", "!", "?", ",", "\n"]):
                    if sentence.strip():
                        yield sentence.strip()
                        sentence = ""
        
        if sentence.strip():
            yield sentence.strip()
            
        # Adiciona a resposta final da IA ao histórico
        history.append({"role": "assistant", "text": full_ai_text.strip()})
            
    except Exception as e:
        print(f"[OPENAI-LLM] Erro: {e}")
        yield "Desculpe, tive um problema técnico. Pode repetir?"
