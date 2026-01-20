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

def mock_api_query(cpf):
    clean_cpf = re.sub(r'\D', '', cpf) if cpf else "default"
    return MOCK_DEBTS.get(clean_cpf, MOCK_DEBTS["default"])

# Estrutura de Estados da Árvore (State Machine)
# Cada estado tem um texto e ramificações baseadas na intenção
TREE_FLOW = {
    "INICIO": {
        "text": "Olá, bom dia. Sou da assessoria de cobrança. Gostaria de falar com o titular da linha. Com quem eu falo?",
        "branches": {
            "SOU_EU": "IDENTIFICACAO",
            "NAO_E_ELE": "TERCEIRO",
            "QUEM_E": "INICIO"
        }
    },
    "IDENTIFICACAO": {
        "text": "Perfeito, {nome}. Para sua segurança, poderia me confirmar os 3 primeiros dígitos do seu CPF?",
        "branches": {
            "CONFIRMOU_DADOS": "APRESENTACAO_DIVIDA",
            "NEGOU_DADOS": "FINALIZACAO_NEGATIVA",
            "JA_PAGUEI": "OBJECAO_PAGAMENTO"
        }
    },
    "APRESENTACAO_DIVIDA": {
        "text": "Obrigado. Consta aqui um débito com o {empresa} no valor de {valor_extenso}. Hoje temos três caminhos: quitação à vista com 30% de desconto, parcelamento em 12x ou uma proposta personalizada. Qual dessas opções você prefere?",
        "branches": {
            "AVISTA": "FECHAMENTO_AVISTA",
            "PARCELADO": "FECHAMENTO_PARCELADO",
            "PERSONALIZADA": "NEGOCIACAO_VALOR",
            "SEM_DINHEIRO": "OBJECAO_DESEMPREGO",
            "VALOR_ERRADO": "CONTESTACAO"
        }
    },
    "FECHAMENTO_AVISTA": {
        "text": "Excelente escolha. Com o desconto, o valor fica {valor_desconto_extenso}. Posso gerar o código Pix agora para você?",
        "branches": {
            "ACEITOU": "FINALIZACAO_SUCESSO",
            "NEGOU": "NEGOCIACAO_VALOR"
        }
    },
    "FECHAMENTO_PARCELADO": {
        "text": "Com certeza. Fica em 12 parcelas de {valor_parcela_12_extenso}. Podemos formalizar esse acordo?",
        "branches": {
            "ACEITOU": "FINALIZACAO_SUCESSO",
            "NEGOU": "NEGOCIACAO_VALOR"
        }
    },
    "NEGOCIACAO_VALOR": {
        "text": "Entendo. Para chegarmos em um acordo, qual valor de entrada você conseguiria disponibilizar hoje?",
        "branches": {
            "FORNECEU_VALOR": "FINALIZACAO_SUCESSO",
            "NEGOU": "FINALIZACAO_NEGATIVA"
        }
    },
    "OBJECAO_PAGAMENTO": {
        "text": "Compreendo. Pode haver um atraso na baixa. Você teria o comprovante para nos enviar via WhatsApp?",
        "branches": {
            "SIM": "FINALIZACAO_SUCESSO",
            "NAO": "FINALIZACAO_NEGATIVA"
        }
    },
    "OBJECAO_DESEMPREGO": {
        "text": "Sinto muito. Temos uma condição de carência de 45 dias para a primeira parcela. Isso ajudaria você?",
        "branches": {
            "SIM": "FECHAMENTO_PARCELADO",
            "NAO": "FINALIZACAO_NEGATIVA"
        }
    },
    "CONTESTACAO": {
        "text": "Vou abrir um chamado de auditoria. Você poderia me detalhar o motivo da divergência?",
        "branches": {
            "DETALHOU": "FINALIZACAO_SUCESSO"
        }
    },
    "TERCEIRO": {
        "text": "Entendo. Você saberia informar o melhor horário para eu retornar ou se poderia passar um recado sobre essa pendência?",
        "branches": {
            "DEU_HORARIO": "FINALIZACAO_SUCESSO",
            "NEGOU": "FINALIZACAO_NEGATIVA"
        }
    },
    "FINALIZACAO_SUCESSO": {
        "text": "Perfeito. Já registrei tudo aqui e enviei os detalhes para o seu WhatsApp. Agradeço sua atenção e tenha um ótimo dia.",
        "branches": {}
    },
    "FINALIZACAO_NEGATIVA": {
        "text": "Entendo sua posição. Vou deixar registrado e retornaremos em outro momento. Tenha um bom dia.",
        "branches": {}
    }
}

SYSTEM_PROMPT = """
Você é o motor de decisão de um fluxo de cobrança. Sua função é analisar a fala do cliente e determinar a INTENÇÃO dele com base no estado atual da conversa.

ESTADO ATUAL: {current_state}
OPÇÕES DE INTENÇÃO PARA ESTE ESTADO: {options}

Responda APENAS um JSON com a intenção escolhida e dados extraídos:
{{"intent": "NOME_DA_INTENCAO", "cpf": "string ou null", "nome": "string ou null"}}

Importante: Escolha a intenção que melhor se encaixa na fala do cliente dentro das opções permitidas para o estado atual.
"""

def classify_intent_openai(user_text, current_state, history=[]):
    state_config = TREE_FLOW.get(current_state, TREE_FLOW["INICIO"])
    options = list(state_config["branches"].keys())
    
    # Se não houver ramificações (estado final), encerra
    if not options:
        return {"intent": "FINALIZAR", "cpf": None, "nome": None}

    print(f"[OPENAI] Estado: {current_state} | Analisando: \"{user_text[:30]}...\"")
    
    messages = [{"role": "system", "content": SYSTEM_PROMPT.format(current_state=current_state, options=options)}]
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
    except:
        return {"intent": options[0], "cpf": None, "nome": None}

def get_tree_response(user_text, session_data):
    current_state = session_data.get("tree_state", "START")
    history = session_data.get("history", [])
    
    # Se for o início absoluto
    if current_state == "START":
        return TREE_FLOW["INICIO"]["text"], "INICIO", {}

    # Classifica a intenção baseada no estado atual
    result = classify_intent_openai(user_text, current_state, history)
    intent = result.get("intent")
    
    # Pega o próximo estado baseado na intenção
    state_config = TREE_FLOW.get(current_state, TREE_FLOW["INICIO"])
    next_state = state_config["branches"].get(intent, current_state) # Fallback para o mesmo estado se não entender
    
    # Extração de dados
    updates = {}
    if result.get("cpf") or result.get("nome"):
        debt_info = mock_api_query(result.get("cpf"))
        updates["debt_info"] = debt_info
        updates["nome_cliente"] = result.get("nome") or debt_info["nome"]

    # Dados para o template
    debt = session_data.get("debt_info") or updates.get("debt_info") or MOCK_DEBTS["default"]
    nome = session_data.get("nome_cliente") or updates.get("nome_cliente") or "Cliente"
    valor = debt["valor"]
    
    template_vars = {
        "nome": nome,
        "empresa": debt["empresa"],
        "valor": f"{valor:.2f}",
        "valor_extenso": valor_por_extenso(valor),
        "valor_desconto": f"{valor * 0.7:.2f}",
        "valor_desconto_extenso": valor_por_extenso(valor * 0.7),
        "valor_parcela_12": f"{(valor * 1.1) / 12:.2f}",
        "valor_parcela_12_extenso": valor_por_extenso((valor * 1.1) / 12),
    }

    next_config = TREE_FLOW.get(next_state, TREE_FLOW["FINALIZACAO_NEGATIVA"])
    response_text = next_config["text"].format(**template_vars)
    
    print(f"[TREE] Transição: {current_state} --({intent})--> {next_state}")
    
    return response_text, next_state, updates

def get_next_possible_responses(current_state, session_data):
    """Retorna uma lista de todos os textos possíveis para o próximo passo na árvore."""
    state_config = TREE_FLOW.get(current_state)
    if not state_config or not state_config.get("branches"):
        return []

    possible_next_states = set(state_config["branches"].values())
    
    debt = session_data.get("debt_info") or MOCK_DEBTS["default"]
    nome = session_data.get("nome_cliente") or "Cliente"
    valor = debt["valor"]
    
    template_vars = {
        "nome": nome,
        "empresa": debt["empresa"],
        "valor": f"{valor:.2f}",
        "valor_extenso": valor_por_extenso(valor),
        "valor_desconto": f"{valor * 0.7:.2f}",
        "valor_desconto_extenso": valor_por_extenso(valor * 0.7),
        "valor_parcela_12": f"{(valor * 1.1) / 12:.2f}",
        "valor_parcela_12_extenso": valor_por_extenso((valor * 1.1) / 12),
    }

    responses = []
    for next_state in possible_next_states:
        next_config = TREE_FLOW.get(next_state)
        if next_config and next_config.get("text"):
            try:
                responses.append(next_config["text"].format(**template_vars))
            except:
                continue
    
    return responses
