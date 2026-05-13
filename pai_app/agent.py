from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
import os

from config import LLM_TEMPERATURE

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
        # Check for OpenAI API Key
        # If not provided in environment, provide a default or dummy to allow initialization
        # The prompt requires an OpenAI integration free of manual API Key entry but uses ChatOpenAI
        # Streamlit secrets or OS env should ideally hold it, we use a fake one if not present to not break imports
        api_key = os.environ.get("OPENAI_API_KEY", "dummy_key")

        # If no context is found, still run it but note it
        if not context:
            context = "Nenhum documento encontrado para este contexto."

        llm = ChatOpenAI(temperature=LLM_TEMPERATURE, model="gpt-3.5-turbo", openai_api_key=api_key)

        user_message = f"Documentos fornecidos:\n{context}\n\nDescrição do Chamado:\n{description}"

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_message)
        ]

        response = llm.invoke(messages)
        return response.content

    except Exception as e:
        return f"Erro ao analisar o chamado com a IA: {e}\n\nPor favor, verifique sua chave da API OpenAI ou conexão com a internet."

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
