def valor_por_extenso(valor):
    """Converte um valor numérico para uma string por extenso em português."""
    inteiro = int(valor)
    centavos = int(round((valor - inteiro) * 100))
    
    unidades = ["", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove"]
    dezenas_10_19 = ["dez", "onze", "doze", "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
    dezenas = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
    centenas = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]
    
    def converter_bloco(n):
        if n == 0: return ""
        if n == 100: return "cem"
        
        res = []
        c = n // 100
        d = (n % 100) // 10
        u = n % 10
        
        if c > 0: res.append(centenas[c])
        
        if d == 1:
            res.append(dezenas_10_19[u])
        else:
            if d > 1: res.append(dezenas[d])
            if u > 0: res.append(unidades[u])
            
        return " e ".join([x for x in res if x])

    def converter_inteiro(n):
        if n == 0: return "zero"
        
        milhares = n // 1000
        resto = n % 1000
        
        partes = []
        if milhares > 0:
            if milhares == 1:
                partes.append("mil")
            else:
                partes.append(converter_bloco(milhares) + " mil")
        
        if resto > 0:
            # Regra do "e" entre milhar e centena: 
            # Se o resto for menor que 100 ou múltiplo de 100, usa "e"
            if milhares > 0:
                if resto < 100 or resto % 100 == 0:
                    partes.append("e " + converter_bloco(resto))
                else:
                    partes.append(converter_bloco(resto))
            else:
                partes.append(converter_bloco(resto))
            
        return " ".join(partes).replace("  ", " ").strip()

    resultado = ""
    if inteiro > 0:
        resultado += converter_inteiro(inteiro)
        resultado += " real" if inteiro == 1 else " reais"
        
    if centavos > 0:
        if inteiro > 0: resultado += " e "
        resultado += converter_bloco(centavos)
        resultado += " centavo" if centavos == 1 else " centavos"
        
    return resultado or "zero reais"
