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

# Grupos base (Grupos fixos que sempre serão lidos, a menos que você os remova pelo chat)
GRUPOS_BASE = [
    'PoisonPromos',
    'Fraguas84Oficial',
    'tecnoarthardware',
    'gamerbrasilpromos',
    'OQMDVPROMO'
]

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
    
    print("Buscando comandos de produtos no histórico do chat...")
    
    # Aumentado para 1000 para não esquecer os comandos antigos
    for msg in client.iter_messages('Monitordepromos99_bot', limit=1000): 
        if msg.text:
            txt = msg.text.lower()
            
            # Espaço adicionado para não confundir com /addgrupo
            if txt.startswith('/add '):
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
            
            elif txt.startswith('/remove '):
                nome = txt.replace('/remove ', '').strip()
                if nome not in itens_processados:
                    itens_processados.add(nome) 
                    print(f"   [REMOVIDO/IGNORADO] Item: {nome}")
                    
    return lista_final

def carregar_lista_grupos(client):
    grupos_finais = set(GRUPOS_BASE)
    grupos_processados = set()

    print("Buscando comandos de grupos no histórico do chat...")
    
    # Aumentado para 1000 para não esquecer os comandos antigos
    for msg in client.iter_messages('Monitordepromos99_bot', limit=1000):
        if msg.text:
            txt = msg.text.lower()
            
            if txt.startswith('/addgrupo '):
                # Limpa o comando e remove o '@' se você digitar
                nome = txt.replace('/addgrupo ', '').strip().replace('@', '')
                if nome not in grupos_processados:
                    grupos_finais.add(nome)
                    grupos_processados.add(nome)
                    print(f"   [GRUPO ADICIONADO] {nome}")
                    
            elif txt.startswith('/removegrupo '):
                nome = txt.replace('/removegrupo ', '').strip().replace('@', '')
                if nome not in grupos_processados:
                    if nome in grupos_finais:
                        grupos_finais.remove(nome)
                    grupos_processados.add(nome)
                    print(f"   [GRUPO REMOVIDO] {nome}")

    return list(grupos_finais)

def buscar_promocoes():
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id
        meus_produtos = carregar_lista_desejos(client)
        meus_grupos = carregar_lista_grupos(client)
        
        encontrados = []
        nao_encontrados = list(meus_produtos.keys())
        
        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de produtos está vazia! Mande:\n`/add playstation 5 3200`")
            return
            
        if not meus_grupos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de grupos está vazia! Mande:\n`/addgrupo @nome_do_grupo`")
            return

        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)
        
        # Agora itera sobre a lista dinâmica de grupos
        for grupo in meus_grupos:
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
                                    
                                    alerta = f"🚨 **Preço Atingido!**\n\n**Produto:** {produto} por R$ {menor_preco:.2f}\n📦 **Grupo:** {grupo}\n🔗 {link_txt}"
                                    enviar_msg_bot(meu_id, alerta)
            except Exception as e:
                print(f"Não foi possível ler o grupo {grupo}. Verifique se o nome está correto ou se você participa dele. Erro: {e}")

if __name__ == '__main__':
    buscar_promocoes()
