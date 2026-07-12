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

# --- AQUI VOCÊ ADICIONA OS GRUPOS ---
# Coloque o @username de cada grupo ou ID. Sempre entre aspas e separados por vírgula.
GRUPOS_ALVO = [
    'PoisonPromos',
    'Fraguas84Oficial',    # Substitua pelo username do outro grupo
    'tecnoarthardware',
    'gamerbrasilpromos'# Substitua por outro
]
# ------------------------------------

def enviar_msg_bot(meu_id, texto):
    texto_formatado = urllib.parse.quote(texto)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={meu_id}&text={texto_formatado}&parse_mode=Markdown"
    try:
        urllib.request.urlopen(url)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o bot: {e}")

def carregar_lista_desejos(client):
    lista_final = {}
    itens_processados = set() 
    
    meu_id = client.get_me().id
    print(f"Buscando comandos no histórico do chat...")
    
    for msg in client.iter_messages('Monitordepromos99_bot', limit=200): 
        if msg.text:
            txt = msg.text.lower()
            
            if txt.startswith('/add'):
                partes = txt.split()
                if len(partes) >= 3:
                    try:
                        preco = float(partes[-1])
                        nome = " ".join(partes[1:-1]).strip()
                        
                        if nome not in itens_processados:
                            lista_final[nome] = preco
                            itens_processados.add(nome) 
                            print(f"   [ATIVO] Monitorando: {nome} por R$ {preco}")
                    except ValueError:
                        continue
            
            elif txt.startswith('/remove'):
                nome = txt.replace('/remove', '').strip()
                if nome not in itens_processados:
                    itens_processados.add(nome) 
                    print(f"   [REMOVIDO/IGNORADO] Item: {nome}")
                    
    return lista_final

def buscar_promocoes():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id
        meus_produtos = carregar_lista_desejos(client)
        
        encontrados = []
        nao_encontrados = list(meus_produtos.keys())
        
        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista está vazia! Mande um comando como:\n`/add playstation 5 3200`")
            return

        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)
        
        # O script agora varre cada grupo da sua lista
        for grupo in GRUPOS_ALVO:
            print(f"Vasculhando o grupo: {grupo}")
            try:
                for message in client.iter_messages(grupo, limit=30):
                    if message.date < tempo_limite or not message.text:
                        continue
                    
                    texto_msg = message.text.lower()
                    
                    for produto, preco_max in meus_produtos.items():
                        if produto in texto_msg:
                            if produto in nao_encontrados:
                                nao_encontrados.remove(produto)
                            if produto not in encontrados:
                                encontrados.append(produto)
                                
                            precos = re.findall(r'r\$\s*(\d+(?:\.\d+)*(?:,\d+)?)', texto_msg)
                            if precos:
                                menor_preco = min([float(p.replace('.', '').replace(',', '.')) for p in precos])
                                
                                if menor_preco <= preco_max:
                                    link = re.search(r'(https?://[^\s]+)', message.text)
                                    link_txt = link.group(1) if link else "Link não encontrado na mensagem."
                                    
                                    # Alerta atualizado mostrando de qual grupo veio
                                    alerta = f"🚨 **Preço Atingido!**\n\n**Produto:** {produto} por R$ {menor_preco:.2f}\n📦 **Grupo:** {grupo}\n🔗 {link_txt}"
                                    enviar_msg_bot(meu_id, alerta)
            except Exception as e:
                print(f"Não foi possível ler o grupo {grupo}. Verifique se o nome está correto ou se você participa dele. Erro: {e}")

        # --- ENVIO DO RELATÓRIO FINAL ---
        texto_encontrados = ', '.join(encontrados) if encontrados else 'Nenhum'
        texto_nao_encontrados = ', '.join(nao_encontrados) if nao_encontrados else 'Nenhum'
        
        relatorio = f"📊 **Relatório da Rodada:**\n\n✅ *Encontrados na busca:* {texto_encontrados}\n❌ *Não encontrados:* {texto_nao_encontrados}"
        enviar_msg_bot(meu_id, relatorio)
        
if __name__ == '__main__':
    buscar_promocoes()
