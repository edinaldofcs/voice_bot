import os
import json
import time
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils import valor_por_extenso

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

TREE_FLOW_DATA = {
  "flow_id": "negociacao_divida_cliente",
  "start_node": "inicio",
  "nodes": {
    "inicio": {
      "type": "START",
      "message": "Olá! Vi que você tem um débito em aberto. Como posso te ajudar hoje?",
      "next": "identificar_intencao"
    },

    "identificar_intencao": {
      "type": "INTENT",
      "tag": "identificar_intencao",
      "description": "Identificar o objetivo principal do cliente",
      "examples": [
        "quero negociar",
        "não consigo pagar agora",
        "preciso de um acordo",
        "quero pagar minha dívida"
      ],
      "intents": {
        "negociar_divida": "escolher_tipo_negociacao",
        "consultar_valor": "consultar_valor_divida",
        "falar_com_atendente": "encaminhar_atendente"
      }
    },

    "consultar_valor_divida": {
      "type": "INFO",
      "tag": "consultar_valor_divida",
      "message": "O valor atual da sua dívida é {{valor_divida}}.",
      "next": "escolher_tipo_negociacao"
    },

    "escolher_tipo_negociacao": {
      "type": "DECISION",
      "tag": "escolher_tipo_negociacao",
      "message": "Qual opção funciona melhor para você? Renegociar a data, parcelar a dívida, solicitar um desconto ou quitar à vista?",
      "options": {
        "renegociar_data": "renegociar_data",
        "parcelar_divida": "parcelar_divida",
        "solicitar_desconto": "solicitar_desconto",
        "quitar_a_vista": "quitar_a_vista"
      }
    },

    "renegociar_data": {
      "type": "ACTION",
      "tag": "renegociar_data",
      "description": "Cliente quer alterar a data de vencimento",
      "examples": [
        "posso pagar outro dia?",
        "mudar a data do boleto",
        "adiar vencimento"
      ],
      "next": "informar_nova_data",
      "back_to": "escolher_tipo_negociacao"
    },

    "informar_nova_data": {
      "type": "INPUT",
      "tag": "informar_nova_data",
      "message": "Qual nova data de vencimento você deseja?",
      "next": "validar_nova_data",
      "back_to": "renegociar_data"
    },

    "validar_nova_data": {
      "type": "VALIDATION",
      "tag": "validar_nova_data",
      "rules": {
        "min_days_from_today": 3,
        "max_days_from_today": 30
      },
      "on_success": "confirmar_acordo",
      "on_fail": "data_invalida"
    },

    "data_invalida": {
      "type": "INFO",
      "message": "Essa data não está disponível. Por favor, informe outra.",
      "next": "informar_nova_data"
    },

    "parcelar_divida": {
      "type": "ACTION",
      "tag": "parcelar_divida",
      "description": "Cliente deseja parcelar a dívida",
      "examples": [
        "posso parcelar?",
        "dividir em vezes",
        "pagar aos poucos"
      ],
      "next": "informar_parcelas",
      "back_to": "escolher_tipo_negociacao"
    },

    "informar_parcelas": {
      "type": "INPUT",
      "tag": "informar_parcelas",
      "message": "Em quantas parcelas você deseja pagar? Podemos fazer de 2 a 12 vezes.",
      "next": "validar_parcelas",
      "back_to": "parcelar_divida"
    },

    "validar_parcelas": {
      "type": "VALIDATION",
      "tag": "validar_parcelas",
      "rules": {
        "min": 2,
        "max": 12
      },
      "on_success": "simular_parcelamento",
      "on_fail": "parcelas_invalidas"
    },

    "parcelas_invalidas": {
      "type": "INFO",
      "message": "Número de parcelas indisponível. Tente outra opção.",
      "next": "informar_parcelas"
    },

    "simular_parcelamento": {
      "type": "INFO",
      "tag": "simular_parcelamento",
      "message": "Cada parcela ficará no valor de {{valor_parcela}}.",
      "next": "confirmar_acordo"
    },

    "solicitar_desconto": {
      "type": "ACTION",
      "tag": "solicitar_desconto",
      "description": "Cliente deseja desconto para quitar a dívida",
      "examples": [
        "tem desconto?",
        "consigo pagar menos?",
        "desconto à vista"
      ],
      "next": "calcular_desconto",
      "back_to": "escolher_tipo_negociacao"
    },

    "calcular_desconto": {
      "type": "ACTION",
      "tag": "calcular_desconto",
      "on_available": "confirmar_acordo",
      "on_unavailable": "oferecer_parcelamento"
    },

    "oferecer_parcelamento": {
      "type": "INFO",
      "message": "No momento não há desconto disponível. Podemos parcelar se preferir.",
      "next": "parcelar_divida"
    },

    "quitar_a_vista": {
      "type": "ACTION",
      "tag": "quitar_a_vista",
      "description": "Cliente deseja quitar a dívida à vista",
      "examples": [
        "quero pagar tudo",
        "quitar agora",
        "pagar à vista"
      ],
      "next": "confirmar_acordo",
      "back_to": "escolher_tipo_negociacao"
    },

    "confirmar_acordo": {
      "type": "CONFIRMATION",
      "tag": "confirmar_acordo",
      "message": "Resumo do acordo: Valor total de {{valor_final}}, na condição de {{condicao}}. Posso confirmar?",
      "options": {
        "confirmar": "final_sucesso",
        "alterar": "escolher_tipo_negociacao",
        "cancelar": "final_falha"
      }
    },

    "final_sucesso": {
      "type": "END_SUCCESS",
      "message": "Perfeito! Seu acordo foi confirmado e o boleto será enviado. Obrigado pelo contato!"
    },

    "final_falha": {
      "type": "END_FAIL",
      "message": "Tudo bem. Se precisar de ajuda novamente, estarei por aqui. Tenha um bom dia."
    },

    "encaminhar_atendente": {
      "type": "END_FAIL",
      "message": "Vou te encaminhar para um atendente humano agora. Por favor, aguarde um momento."
    }
  }
}

def mock_api_query(cpf):
    clean_cpf = re.sub(r'\D', '', cpf) if cpf else "default"
    return MOCK_DEBTS.get(clean_cpf, MOCK_DEBTS["default"])

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
    node_type = node_config["type"]
    
    system_prompt = f"""
Você é um assistente de voz para cobrança. Analise a fala do usuário para o nó '{node_id}' ({node_type}).
"""
    
    if node_type == "INTENT":
        options = node_config["intents"]
        examples = node_config.get("examples", [])
        system_prompt += f"\nDetermine a intenção do usuário entre as opções: {list(options.keys())}."
        system_prompt += f"\nExemplos de referência: {examples}"
        system_prompt += "\nResponda APENAS um JSON: {\"choice\": \"nome_da_opcao\"}"
        
    elif node_type == "DECISION" or node_type == "CONFIRMATION":
        options = node_config["options"]
        system_prompt += f"\nEscolha a melhor opção entre: {list(options.keys())}."
        system_prompt += "\nResponda APENAS um JSON: {\"choice\": \"nome_da_opcao\"}"
        
    elif node_type == "INPUT":
        system_prompt += "\nExtraia o valor solicitado (data, número de parcelas, etc)."
        system_prompt += "\nResponda APENAS um JSON: {\"value\": \"valor_extraido\"}"

    messages = [{"role": "system", "content": system_prompt}]
    for msg in history[-4:]:
        role = "assistant" if msg["role"] in ["assistant", "ai"] else "user"
        messages.append({"role": role, "content": msg["text"]})
    messages.append({"role": "user", "content": user_text})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"[LLM ERROR] {e}")
        return {}

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
            
            if current_node["type"] == "INTENT":
                choice = llm_result.get("choice")
                next_node_id = current_node["intents"].get(choice, current_state)
            elif current_node["type"] == "DECISION" or current_node["type"] == "CONFIRMATION":
                choice = llm_result.get("choice")
                next_node_id = current_node["options"].get(choice, current_state)
            elif current_node["type"] == "INPUT":
                val = llm_result.get("value")
                updates["captured_input"] = val
                next_node_id = current_node.get("next")
            else:
                next_node_id = current_node.get("next")

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
            if next_node_id == "calcular_desconto":
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
            else:
                next_node_id = node.get("next")
                if not next_node_id: break
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
