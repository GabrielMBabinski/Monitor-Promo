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
    lista_final = {}
    itens_processados = set() # Memória do que o script já resolveu
    
    meu_id = client.get_me().id
    print(f"Buscando comandos no histórico do chat...")
    
    # Lê as últimas 200 mensagens (da mais NOVA para a mais VELHA)
    for msg in client.iter_messages('Monitordepromos99_bot', limit=200): 
        if msg.text:
            txt = msg.text.lower()
            
            # Se for um comando de ADICIONAR
            if txt.startswith('/add'):
                partes = txt.split()
                if len(partes) >= 3:
                    try:
                        preco = float(partes[-1])
                        nome = " ".join(partes[1:-1]).strip()
                        
                        # Se é a primeira vez que vemos esse item (ou seja, é a ordem mais recente sua)
                        if nome not in itens_processados:
                            lista_final[nome] = preco
                            itens_processados.add(nome) # Marca que já sabemos o destino desse item
                            print(f"   [ATIVO] Monitorando: {nome} por R$ {preco}")
                    except ValueError:
                        continue
            
            # Se for um comando de REMOVER
            elif txt.startswith('/remove'):
                nome = txt.replace('/remove', '').strip()
                
                # Se achamos um remover ANTES de achar um adicionar (lendo do presente pro passado), 
                # significa que sua decisão mais recente foi deletar esse item!
                if nome not in itens_processados:
                    itens_processados.add(nome) # Bloqueia qualquer /add antigo desse item
                    print(f"   [REMOVIDO/IGNORADO] Item: {nome}")
                    
    return lista_final

def buscar_promocoes():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id
        meus_produtos = carregar_lista_desejos(client)
        
        # --- LISTAS PARA O RELATÓRIO ---
        encontrados = []
        nao_encontrados = list(meus_produtos.keys())
        
        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista está vazia! Mande um comando como:\n`/add playstation 5 3200`")
            return

        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)
        
        for message in client.iter_messages(GRUPO_ALVO, limit=30):
            if message.date < tempo_limite or not message.text:
                continue
            
            texto_msg = message.text.lower()
            
            for produto, preco_max in meus_produtos.items():
                if produto in texto_msg:
                    # Registra no relatório que achou o item na varredura
                    if produto in nao_encontrados:
                        nao_encontrados.remove(produto)
                    if produto not in encontrados:
                        encontrados.append(produto)
                        
                    precos = re.findall(r'r\$\s*(\d{1,3}(?:\.\d{3})*(?:,\d{2})?|\d+)', texto_msg)
                    if precos:
                        menor_preco = min([float(p.replace('.', '').replace(',', '.')) for p in precos])
                        
                        if menor_preco <= preco_max:
                            link = re.search(r'(https?://[^\s]+)', message.text)
                            link_txt = link.group(1) if link else "Link não encontrado na mensagem."
                            alerta = f"🚨 **Preço Atingido!**\n\n**Produto:** {produto} por R$ {menor_preco:.2f}\n🔗 {link_txt}"
                            enviar_msg_bot(meu_id, alerta)

        # --- ENVIO DO RELATÓRIO FINAL ---
        texto_encontrados = ', '.join(encontrados) if encontrados else 'Nenhum'
        texto_nao_encontrados = ', '.join(nao_encontrados) if nao_encontrados else 'Nenhum'
        
        relatorio = f"📊 **Relatório da Rodada:**\n\n✅ *Encontrados no grupo:* {texto_encontrados}\n❌ *Não encontrados no grupo:* {texto_nao_encontrados}"
        enviar_msg_bot(meu_id, relatorio)
        
if __name__ == '__main__':
    buscar_promocoes()
