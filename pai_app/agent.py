import os
from g4f.client import Client

# Standard required prompt
SYSTEM_PROMPT = """Você é um analista corporativo especialista.

Analise o chamado utilizando SOMENTE os documentos fornecidos.

Você deve:
* classificar o chamado
* identificar criticidade
* identificar impactos
* validar compliance e legislação
* identificar riscos
* sugerir possíveis causas
* recomendar próximos passos
* sugerir squad responsável
* rejeitar solicitações ilegais

Nunca invente informações fora da documentação.
Se não houver informação suficiente:
declare explicitamente.

A IA deve responder exatamente neste formato markdown:

Classificação
Criticidade
Impacto
Compliance
Riscos
Possíveis causas
Próximos passos
Squad responsável
Conclusão
Documentos utilizados
"""

def analyze_ticket(description: str, context: str) -> str:
    """
    Analyzes the ticket description using the provided context and the specified formatting rules.
    """
    try:
        # If no context is found, still run it but note it
        if not context:
            context = "Nenhum documento encontrado para este contexto."

        client = Client()
        user_message = f"Documentos fornecidos:\n{context}\n\nDescrição do Chamado:\n{description}"

        response = client.chat.completions.create(
            model="", # using empty string or generic to allow G4F to find the best available free model
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0
        )
        return response.choices[0].message.content

    except Exception as e:
        return f"Erro ao analisar o chamado com a IA: {e}\n\nPor favor, tente novamente mais tarde."

def extract_criticality(analysis: str) -> str:
    """
    Attempts to extract the criticality from the markdown analysis.
    Returns 'Alta', 'Média', 'Baixa' or 'Desconhecida'.
    """
    try:
        lines = analysis.split('\n')
        for i, line in enumerate(lines):
            if line.strip().lower().startswith('criticidade'):
                # Extract value after 'Criticidade' or on the next line
                val = line.replace('Criticidade', '').replace(':', '').strip()
                if not val and i + 1 < len(lines):
                    val = lines[i+1].strip()

                val_lower = val.lower()
                if 'alta' in val_lower or 'crític' in val_lower:
                    return 'Alta'
                if 'média' in val_lower or 'media' in val_lower:
                    return 'Média'
                if 'baixa' in val_lower:
                    return 'Baixa'
        return 'Desconhecida'
    except:
        return 'Desconhecida'
