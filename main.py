import os
import re
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Variáveis seguras
API_ID = int(os.environ['API_ID'])
API_HASH = os.environ['API_HASH']
SESSION_STRING = os.environ['SESSION_STRING']
BOT_TOKEN = os.environ['BOT_TOKEN']
GRUPO_ALVO = 'PoisonPromos'

def enviar_msg_bot(meu_id, texto):
    texto_formatado = urllib.parse.quote(texto)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={meu_id}&text={texto_formatado}&parse_mode=Markdown"
    urllib.request.urlopen(url)

def carregar_lista_desejos(client):
    lista = {}
    meu_id = client.get_me().id
    print(f"Buscando comandos no chat privado com ID: {meu_id}")
    
    # Lemos do mais antigo para o mais recente para que o /remove 
    # ocorra depois do /add na cronologia da lista
    for msg in client.iter_messages('Monitordepromos99_bot', limit=50): 
        if msg.text:
            txt = msg.text.lower()
            
            if txt.startswith('/add'):
                partes = txt.split()
                if len(partes) >= 3:
                    try:
                        preco = float(partes[-1])
                        nome = " ".join(partes[1:-1])
                        lista[nome] = preco
                        print(f"   [OK] Adicionado: {nome} por {preco}")
                    except ValueError:
                        print("   [ERRO] Preço inválido.")
            
            # LÓGICA DE REMOÇÃO
            elif txt.startswith('/remove'):
                nome = txt.replace('/remove', '').strip()
                if nome in lista:
                    del lista[nome]
                    print(f"   [OK] Removido: {nome}")
                else:
                    print(f"   [AVISO] Tentativa de remover item inexistente: {nome}")
                    
    return lista

def buscar_promocoes():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id
        meus_produtos = carregar_lista_desejos(client)
        
        # --- LISTAS PARA O RELATÓRIO ---
        encontrados = []
        nao_encontrados = list(meus_produtos.keys())
        
        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Lista vazia! Use /add nome preco.")
            return

        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)
        
        for message in client.iter_messages(GRUPO_ALVO, limit=30):
            if message.date < tempo_limite or not message.text:
                continue
            
            texto_msg = message.text.lower()
            
            for produto, preco_max in meus_produtos.items():
                if produto in texto_msg:
                    # Se encontrou o produto, remove da lista de "não encontrados"
                    if produto in nao_encontrados:
                        nao_encontrados.remove(produto)
                    if produto not in encontrados:
                        encontrados.append(produto)
                        
                    precos = re.findall(r'r\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+)', texto_msg)
                    if precos:
                        menor_preco = min([float(p.replace('.', '').replace(',', '.')) for p in precos])
                        
                        if menor_preco <= preco_max:
                            link = re.search(r'(https?://[^\s]+)', message.text)
                            link_txt = link.group(1) if link else "Link não encontrado."
                            alerta = f"🚨 **Preço Atingido!**\n\n**Produto:** {produto} por R$ {menor_preco:.2f}\n🔗 {link_txt}"
                            enviar_msg_bot(meu_id, alerta)

        # --- ENVIO DO RELATÓRIO FINAL ---
        relatorio = f"📊 **Relatório da Rodada:**\n\n✅ *Encontrados:* {', '.join(encontrados) if encontrados else 'Nenhum'}\n❌ *Não encontrados:* {', '.join(nao_encontrados) if nao_encontrados else 'Nenhum'}"
        enviar_msg_bot(meu_id, relatorio)
        
if __name__ == '__main__':
    buscar_promocoes()
