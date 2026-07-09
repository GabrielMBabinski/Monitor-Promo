import os
import re
from datetime import datetime, timedelta, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Variáveis seguras (Puxadas do GitHub Secrets)
API_ID = int(os.environ['API_ID'])
API_HASH = os.environ['API_HASH']
SESSION_STRING = os.environ['SESSION_STRING']

# --- SUAS CONFIGURAÇÕES ---
# IMPORTANTE: Use o @username do grupo ou o link de convite. 
# O nome "Poison indicações e promoções" não funciona aqui, precisa ser o ID ou Username (ex: 'poison_promos')
GRUPO_ALVO = 'PoisonPromos' 
PRODUTO = 'filtro de linha' # Deixe sempre em minúsculo
PRECO_MAXIMO = 50 
# --------------------------

tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)

def buscar_promocoes():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    with client:

        client.send_message(-5140734700, "✅ O script rodou no GitHub e conseguiu acessar o grupo!")
        # Pega as últimas 30 mensagens do grupo
        for message in client.iter_messages(GRUPO_ALVO, limit=30):
            # Ignora mensagens mais antigas que 15 minutos para não mandar alertas duplicados
            if message.date < tempo_limite:
                continue
                
            if message.text:
                texto_mensagem = message.text.lower()
                
                # Verifica se o produto está na mensagem
                if PRODUTO in texto_mensagem:
                    # Captura todos os valores em reais (ex: R$ 229, R$999, r$ 1.200,90)
                    precos_encontrados = re.findall(r'r\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+)', texto_mensagem)
                    
                    if precos_encontrados:
                        # Encontra o menor preço na mensagem (resolve o problema do "De R$ X por R$ Y")
                        menor_preco = float('inf')
                        for p in precos_encontrados:
                            # Formata para converter em decimal
                            valor_formatado = p.replace('.', '').replace(',', '.')
                            valor_float = float(valor_formatado)
                            if valor_float < menor_preco:
                                menor_preco = valor_float
                        
                        # Se o menor preço da mensagem estiver dentro do seu orçamento
                        if menor_preco <= PRECO_MAXIMO:
                            # Isola o link de compra (procura qualquer coisa que comece com http)
                            link_match = re.search(r'(https?://[^\s]+)', message.text)
                            link_produto = link_match.group(1) if link_match else "Link não encontrado na mensagem."
                            
                            # Monta o alerta limpo
                            alerta = (
                                f"🚨 **Preço Atingido!**\n\n"
                                f"**Produto:** O item contendo '{PRODUTO}' apareceu por R$ {menor_preco:.2f}\n\n"
                                f"🔗 **Link:** {link_produto}\n\n"
                                f"*(Mensagem extraída do grupo {GRUPO_ALVO})*"
                            )
                            
                            # Envia a notificação para suas "Mensagens Salvas"
                            client.send_message(-5140734700, alerta)

if __name__ == '__main__':
    buscar_promocoes()
