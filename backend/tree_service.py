import os
import json
import time
import re
import httpx
from pydantic import BaseModel
from typing import Optional, List
from openai import OpenAI
from dotenv import load_dotenv
from utils import valor_por_extenso

class TreeAnalysis(BaseModel):
    next_node_id: str
    captured_value: Optional[str] = None
    reasoning: str

# Carrega as variáveis do arquivo .env
load_dotenv()

# Configuração da OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Mock de Banco de Dados de Dívidas
MOCK_DEBTS = {
    "12345678901": {"nome": "João Silva", "valor": 1250.50, "empresa": "Banco Alpha"},
    "98765432100": {"nome": "Maria Oliveira", "valor": 450.00, "empresa": "Loja Beta"},
    "default": {"nome": "Cliente", "valor": 100.00, "empresa": "nossa empresa parceira"}
}

from flow_data import TREE_FLOW_DATA

def mock_api_query(cpf):
    clean_cpf = re.sub(r'\D', '', cpf) if cpf else "default"
    try:
        # Chama a API Mock que criamos (rodando na porta 8001)
        with httpx.Client() as client:
            response = client.get(f"http://localhost:8001/debts/{clean_cpf}", timeout=2.0)
            if response.status_code == 200:
                return response.json()
    except Exception as e:
        print(f"[API ERROR] Falha ao consultar API Mock: {e}")
    
    return MOCK_DEBTS["default"]

def get_template_vars(session_data):
    debt = session_data.get("debt_info") or MOCK_DEBTS["default"]
    valor = debt["valor"]
    
    # Lógica de negócio para variáveis dinâmicas
    captured_input = session_data.get("captured_input")
    
    valor_final = valor
    condicao = "à vista"
    valor_parcela = valor
    
    if session_data.get("agreement_type") == "parcelado":
        num_parcelas = int(session_data.get("num_parcelas", 1))
        valor_final = valor * 1.1 # Juros de 10%
        valor_parcela = valor_final / num_parcelas
        condicao = f"parcelado em {num_parcelas} vezes"
    elif session_data.get("agreement_type") == "desconto":
        valor_final = valor * 0.8 # 20% de desconto
        condicao = "à vista com desconto"
    elif session_data.get("agreement_type") == "data":
        condicao = f"pagamento para o dia {session_data.get('nova_data')}"

    return {
        "valor_divida": valor_por_extenso(valor),
        "valor_parcela": valor_por_extenso(valor_parcela),
        "valor_final": valor_por_extenso(valor_final),
        "condicao": condicao,
        "nome": session_data.get("nome_cliente") or debt["nome"],
        "empresa": debt["empresa"]
    }

def apply_template(text, vars):
    for key, value in vars.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text

def classify_with_llm(user_text, node_id, node_config, history=[]):
    is_internal = user_text.startswith("[SYSTEM]")
    
    system_prompt = f"""
Você é um assistente de voz para cobrança. Analise a situação para o nó '{node_id}'.
Tipo do nó: {node_config.get('type')}
Descrição: {node_config.get('description', 'N/A')}

Sua tarefa é determinar o próximo nó (next_node_id) e extrair valores se necessário.

Configuração do nó:
{json.dumps(node_config, indent=2, ensure_ascii=False)}

Instruções:
1. Se o nó tiver 'intents' ou 'options', mapeie a entrada para a chave correspondente e retorne o VALOR daquela chave (o ID do próximo nó).
2. Se o nó for 'INPUT', extraia o valor para 'captured_value' e use o campo 'next' como 'next_node_id'.
3. Se o nó tiver apenas um campo 'next', use-o como 'next_node_id'.
4. CRÍTICO: Você DEVE escolher um dos IDs de destino presentes na configuração do nó. 
5. Se for uma decisão interna ([SYSTEM]), escolha o caminho mais lógico baseado no histórico.
"""
    
    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-4:]:
        role = "assistant" if msg["role"] in ["assistant", "ai"] else "user"
        messages.append({"role": role, "content": msg["text"]})
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.responses.parse(
            model="gpt-4o-mini",
            input=messages,
            text_format=TreeAnalysis,
        )
        result = response.output_parsed
        # Segurança: Se a IA retornar o mesmo nó em uma decisão automática, forçamos o avanço
        if is_internal and result.next_node_id == node_id:
            options = node_config.get("options", {})
            if options:
                result.next_node_id = list(options.values())[0]
        return result
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return TreeAnalysis(next_node_id=node_id, reasoning=f"Erro: {str(e)}")

def get_tree_response(user_text, session_data):
    current_state = session_data.get("tree_state", "START")
    history = session_data.get("history", [])
    
    accumulated_segments = []
    updates = {}
    
    # 1. Se não for START, processar a entrada do usuário para o estado atual
    next_node_id = None
    if current_state == "START":
        next_node_id = TREE_FLOW_DATA["start_node"]
    else:
        current_node = TREE_FLOW_DATA["nodes"].get(current_state)
        if not current_node:
            next_node_id = TREE_FLOW_DATA["start_node"]
        else:
            llm_result = classify_with_llm(user_text, current_state, current_node, history)
            next_node_id = llm_result.next_node_id
            if llm_result.captured_value:
                updates["captured_input"] = llm_result.captured_value

    # 2. Loop de transição automática
    while next_node_id:
        node = TREE_FLOW_DATA["nodes"].get(next_node_id)
        if not node: break
        
        if "message" in node:
            vars = get_template_vars({**session_data, **updates})
            text = node["message"]
            
            # Divide o texto em partes estáticas e dinâmicas
            parts = re.split(r'(\{\{.*?\}\})', text)
            for part in parts:
                if not part: continue
                if part.startswith("{{") and part.endswith("}}"):
                    var_name = part[2:-2]
                    val = vars.get(var_name, part)
                    accumulated_segments.append({"type": "dynamic", "text": str(val)})
                else:
                    accumulated_segments.append({"type": "static", "text": part})
            
        if node["type"] == "VALIDATION":
            val = updates.get("captured_input") or session_data.get("captured_input")
            rules = node.get("rules", {})
            is_valid = True
            try:
                if "min" in rules and int(val) < rules["min"]: is_valid = False
                if "max" in rules and int(val) > rules["max"]: is_valid = False
                if "min_days_from_today" in rules and not val: is_valid = False
            except: is_valid = False
                
            if is_valid:
                if next_node_id == "validar_parcelas":
                    updates["num_parcelas"] = val
                    updates["agreement_type"] = "parcelado"
                elif next_node_id == "validar_nova_data":
                    updates["nova_data"] = val
                    updates["agreement_type"] = "data"
                next_node_id = node["on_success"]
            else:
                next_node_id = node["on_fail"]
            continue
            
        elif node["type"] == "ACTION":
            if next_node_id == "validar_cpf":
                cpf_input = updates.get("captured_input") or session_data.get("captured_input")
                debt_info = mock_api_query(cpf_input)
                updates["debt_info"] = debt_info
                updates["nome_cliente"] = debt_info["nome"]
                next_node_id = node.get("next")
                continue
            elif next_node_id == "calcular_desconto":
                if time.time() % 10 < 8:
                    updates["agreement_type"] = "desconto"
                    next_node_id = node["on_available"]
                else:
                    next_node_id = node["on_unavailable"]
                continue
            elif next_node_id == "quitar_a_vista":
                updates["agreement_type"] = "avista"
                next_node_id = node.get("next")
                continue
            elif next_node_id == "verificar_necessidade_api":
                # Decisão automática da IA baseada no contexto
                print(f"[AUTO-DECISION] IA decidindo necessidade de API...")
                llm_result = classify_with_llm("[SYSTEM] O sistema está processando os dados. Decida o próximo passo baseado no histórico e perfil do cliente.", next_node_id, node, history)
                next_node_id = llm_result.next_node_id
                print(f"[AUTO-DECISION] IA escolheu: {next_node_id}")
                continue
            elif "options" in node:
                # Handler genérico para decisões automáticas da IA
                llm_result = classify_with_llm("Decisão automática do sistema.", next_node_id, node, history)
                next_node_id = llm_result.next_node_id
                continue
            else:
                next_node_id = node.get("next")
                if not next_node_id: break
                continue

        elif node["type"] == "API":
            # Simulação de chamada de API definida no fluxo
            tag = node.get("tag")
            print(f"[API] Chamando {tag}: {node.get('method')} {node.get('endpoint')}")
            
            # Aqui você faria o request real. Por enquanto, simulamos um resultado.
            if tag == "consultar_score":
                updates["score_cliente"] = 750 # Exemplo de dado retornado
                print(f"[API] Score obtido: 750")
            
            next_node_id = node.get("next")
            continue

        if node["type"] in ["INTENT", "DECISION", "INPUT", "CONFIRMATION", "END_SUCCESS", "END_FAIL"]:
            break
        next_node_id = node.get("next")

    return accumulated_segments, next_node_id, updates

def get_next_possible_responses(current_state, session_data):
    node = TREE_FLOW_DATA["nodes"].get(current_state)
    if not node: return []
    
    possible_next_ids = []
    if node["type"] == "INTENT":
        possible_next_ids = list(node["intents"].values())
    elif node["type"] == "DECISION" or node["type"] == "CONFIRMATION":
        possible_next_ids = list(node["options"].values())
    elif node["type"] == "INPUT":
        if node.get("next"): possible_next_ids = [node["next"]]
    else:
        if node.get("next"): possible_next_ids = [node["next"]]

    all_possible_segments = []
    for next_id in possible_next_ids:
        temp_segments = []
        curr = next_id
        visited = set()
        while curr and curr not in visited:
            visited.add(curr)
            n = TREE_FLOW_DATA["nodes"].get(curr)
            if not n: break
            if "message" in n:
                vars = get_template_vars(session_data)
                text = n["message"]
                parts = re.split(r'(\{\{.*?\}\})', text)
                for part in parts:
                    if not part: continue
                    if part.startswith("{{") and part.endswith("}}"):
                        var_name = part[2:-2]
                        val = vars.get(var_name, part)
                        temp_segments.append({"type": "dynamic", "text": str(val)})
                    else:
                        temp_segments.append({"type": "static", "text": part})
            
            if n["type"] in ["INTENT", "DECISION", "INPUT", "CONFIRMATION", "END_SUCCESS", "END_FAIL"]:
                break
            
            if n["type"] == "VALIDATION":
                curr = n["on_success"]
            elif n["type"] == "ACTION" and "on_available" in n:
                curr = n["on_available"]
            else:
                curr = n.get("next")
        
        if temp_segments:
            all_possible_segments.append(temp_segments)
            
    return all_possible_segments
