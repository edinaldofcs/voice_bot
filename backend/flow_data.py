TREE_FLOW_DATA = {
  "flow_id": "negociacao_divida_cliente",
  "start_node": "capturar_cpf",
  "nodes": {
    "capturar_cpf": {
      "type": "INPUT",
      "tag": "capturar_cpf",
      "message": "Olá! Para começarmos, por favor, me informe o seu CPF.",
      "description": "Solicita o CPF do cliente para identificação",
      "next": "validar_cpf"
    },

    "validar_cpf": {
      "type": "ACTION",
      "tag": "validar_cpf",
      "message": "Só um momento enquanto localizo seus dados...",
      "description": "Valida o CPF e busca informações do cliente",
      "next": "verificar_necessidade_api"
    },

    "verificar_necessidade_api": {
      "type": "ACTION",
      "tag": "verificar_necessidade_api",
      "description": "IA decide se precisa consultar o score de crédito do cliente antes de prosseguir para oferecer condições especiais",
      "options": {
        "consultar_score": "api_consultar_score",
        "prosseguir_direto": "capturar_nome"
      }
    },

    "api_consultar_score": {
      "type": "API",
      "tag": "consultar_score",
      "endpoint": "https://api.exemplo.com/v1/score",
      "method": "GET",
      "next": "capturar_nome"
    },

    "capturar_nome": {
      "type": "INFO",
      "tag": "capturar_nome",
      "message": "Obrigado. Localizei seu cadastro, {{nome}}. Como posso te ajudar hoje?",
      "next": "identificar_intencao"
    },

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
