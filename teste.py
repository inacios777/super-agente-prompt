import requests
import json
import time
from openai import OpenAI
from dotenv import load_dotenv
import os

# Carregar variáveis de ambiente (para a API do ChatGPT)
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# URL do Super Agentes (sem necessidade de API Key)
AGENT_ID = "cm7jhhqln00ez116u2hg1e0t7"
URL_SUPER_AGENTES = f"https://dash.superagentes.ai/api/agents/{AGENT_ID}/query"

# Configuração do cliente OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Perguntas de teste e o que era esperado
PERGUNTAS_TESTE = [
    {"pergunta": "O que é Engenharia de Prompt?", "esperado": "item_respondido"},
    {"pergunta": "Qual a cor da camisa do Cruzeiro?", "esperado": "fallback"},
    {"pergunta": "qual melhor prompt de sistema que o rafael iancio usa em seus videos?", "esperado": "Parcialmente respondido"},
    {"pergunta": "O que são embeddings em NLP?", "esperado": "fallback"},
    {"pergunta": "O que é Engenharia de Prompt?", "esperado": "item_respondido"}
]

# Instruções para o ChatGPT avaliar as respostas
INSTRUCOES_CHATGPT = """
Você é um avaliador especializado em Engenharia de Prompt e sua tarefa é classificar respostas de um assistente conforme os seguintes critérios:

1️⃣ **Item respondido** ✅  
   - Quando a resposta do agente **cobre completamente a intenção da pergunta do usuário**.  
   - A resposta contém informações precisas, bem estruturadas e não omite detalhes essenciais.  

2️⃣ **Parcialmente respondido** ⚠️  
   - Quando a resposta do agente **cobre parcialmente a intenção da pergunta**, mas falta alguma informação relevante.  
   - Quando a resposta contém informações corretas, mas incompletas ou com algum erro conceitual leve.  
   - Se a resposta menciona que há informações incompletas e sugere fontes externas, marque como parcial.  

3️⃣ **Fallback** 🔄  
   - Se a pergunta está fora do escopo do agente e ele corretamente responde que não pode ajudar.  
   - Se a resposta inclui um aviso de limitação e não tenta inventar uma resposta.  

🔍 **Formato esperado de resposta (JSON):**  

{
  "correto": true/false,  
  "parcialmente_correto": true/false,  
  "fallback": true/false  
}
"""

def chatbot_resposta(pergunta, resposta):
    """Envia a resposta do agente para o ChatGPT avaliar"""
    mensagem = f"""
    Pergunta: {pergunta}
    Resposta do Agente: {resposta}
    """

    resposta = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": INSTRUCOES_CHATGPT},
            {"role": "user", "content": mensagem},
        ]
    )
    return resposta.choices[0].message.content


def enviar_pergunta(pergunta):
    """Envia uma pergunta para o Super Agentes via API"""
    payload = {
        "query": pergunta,
        "temperature": 0.7,
        "modelName": "gpt_4o_mini",
        "maxTokens": 2000
    }
    response = requests.post(URL_SUPER_AGENTES, json=payload)

    try:
        resposta_json = response.json()
        return resposta_json.get("answer", "❌ Erro: Resposta não encontrada!")
    except requests.exceptions.JSONDecodeError:
        print(f"❌ Erro ao tentar decodificar JSON. Resposta do servidor:\n{response.text}")
        return None


# Contadores para métricas
respostas_totais = 0
respostas_parciais = 0
fallbacks_ativados = 0

respostas_totais_erradas = 0
respostas_parciais_erradas = 0
fallbacks_ativados_errados = 0

# Testando cada pergunta
for teste in PERGUNTAS_TESTE:
    print(f"🔍 Testando: {teste['pergunta']}...")

    # Enviar pergunta ao Agente e esperar a resposta
    resposta_agente = enviar_pergunta(teste["pergunta"])
    print(f"🤖 Resposta do Agente: {resposta_agente}")

    # Enviar para ChatGPT avaliar
    avaliacao = chatbot_resposta(teste["pergunta"], resposta_agente)

    # Verificar a resposta antes de converter para JSON
    print(f"🔍 Resposta da Avaliação do ChatGPT:\n{avaliacao}")

    # Converter JSON de resposta do ChatGPT
    try:
        avaliacao_json = json.loads(avaliacao)
    except json.JSONDecodeError:
        print("❌ Erro: A resposta do ChatGPT não pôde ser convertida em JSON.")
        avaliacao_json = {"correto": False, "parcialmente_correto": False, "fallback": False}

    # Atualizar métricas conforme esperado
    if avaliacao_json["correto"]:
        respostas_totais += 1
        if teste["esperado"] != "item_respondido":
            respostas_totais_erradas += 1  # Era para ser fallback, mas foi respondido

    elif avaliacao_json["parcialmente_correto"]:
        respostas_parciais += 1
        if teste["esperado"] != "parcialmente_respondido":
            respostas_parciais_erradas += 1  # Errou ao dar uma resposta parcial

    elif avaliacao_json["fallback"]:
        fallbacks_ativados += 1
        if teste["esperado"] != "fallback":
            fallbacks_ativados_errados += 1  # Não deveria ter ativado o fallback

    time.sleep(2)  # Pequeno delay para evitar rate limit

# Cálculo das métricas
total_perguntas = len(PERGUNTAS_TESTE)
taxa_respostas_precisas = ((total_perguntas - (respostas_totais_erradas + respostas_parciais_erradas + fallbacks_ativados_errados)) / total_perguntas) * 100

# Relatório final atualizado
print("\n📊 **Resultados dos Testes**")
print(f"✅ Item respondido: {respostas_totais}")
print(f"⚠️ Parcialmente respondido: {respostas_parciais}")
print(f"🔄 Fallbacks Ativados: {fallbacks_ativados}")
print(f"❌ Item respondido errado: {respostas_totais_erradas}")
print(f"❌ Parcialmente respondido errado: {respostas_parciais_erradas}")
print(f"❌ Fallbacks Ativados Errados: {fallbacks_ativados_errados}")
print(f"📈 **Taxa de Respostas Precisas:** {taxa_respostas_precisas:.2f}%")
