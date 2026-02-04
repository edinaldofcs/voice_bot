from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Mock Debt API")

# Mock de Banco de Dados de Dívidas
MOCK_DEBTS = {
    "12345678901": {
        "nome": "João Silva", 
        "valor": 1250.50, 
        "empresa": "Banco Alpha",
        "score": 750,
        "status": "em_atraso"
    },
    "98765432100": {
        "nome": "Maria Oliveira", 
        "valor": 450.00, 
        "empresa": "Loja Beta",
        "score": 420,
        "status": "em_atraso"
    }
}

class DebtResponse(BaseModel):
    nome: str
    valor: float
    empresa: str
    score: int
    status: str

@app.get("/debts/{cpf}", response_model=DebtResponse)
async def get_debt(cpf: str):
    # Remove caracteres não numéricos
    clean_cpf = "".join(filter(str.isdigit, cpf))
    
    if clean_cpf in MOCK_DEBTS:
        return MOCK_DEBTS[clean_cpf]
    
    # Retorno padrão para CPFs não encontrados (simulando um cliente novo ou genérico)
    return {
        "nome": "Cliente",
        "valor": 100.00,
        "empresa": "Empresa Parceira",
        "score": 500,
        "status": "regular"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
