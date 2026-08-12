import os
import re
import json
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

# Nome do arquivo que vai servir como nosso "Banco de Dados"
ARQUIVO_DADOS = 'dados_bot.json'

# Grupos iniciais padrão
GRUPOS_BASE = [
    'PoisonPromos',
    'Fraguas84Oficial',
    'tecnoarthardware',
    'gamerbrasilpromos'
]

def enviar_msg_bot(meu_id, texto):
    texto_formatado = urllib.parse.quote(texto)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={meu_id}&text={texto_formatado}&parse_mode=Markdown"
    try:
        urllib.request.urlopen(url)
    except Exception as e:
        print(f"Erro ao enviar mensagem para o bot: {e}")

def carregar_dados():
    """Lê o arquivo JSON. Se não existir, cria a estrutura básica."""
    if os.path.exists(ARQUIVO_DADOS):
        with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    # Estrutura padrão para a primeira vez que o bot rodar
    return {
        "ultima_mensagem_id": 0,
        "produtos": {},
        "grupos": GRUPOS_BASE
    }

def salvar_dados(dados):
    """Salva as alterações permanentemente no arquivo JSON."""
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def atualizar_banco_pelo_chat(client, dados):
    """Lê APENAS as mensagens novas e atualiza o JSON."""
    ultimo_id = dados.get("ultima_mensagem_id", 0)
    novas_mensagens = []
    
    # Puxa apenas mensagens com ID maior que a última lida
    for msg in client.iter_messages('Monitordepromos99_bot', min_id=ultimo_id):
        novas_mensagens.append(msg)
        
    if not novas_mensagens:
        return dados # Nenhuma novidade no chat
        
    # Inverte a lista para processar da mais antiga para a mais recente
    # (Garante que se você mandar /add e depois /remove, o remove funcione)
    novas_mensagens.reverse()
    
    for msg in novas_mensagens:
        if msg.text:
            txt = msg.text.lower()
            
            if txt.startswith('/add '):
                partes = txt.split()
                if len(partes) >= 3:
                    try:
                        preco = float(partes[-1])
                        nome = " ".join(partes[1:-1]).strip()
                        dados["produtos"][nome] = preco
                        print(f"✅ Salvo no JSON: {nome} (R$ {preco})")
                    except ValueError:
                        continue
                        
            elif txt.startswith('/remove '):
                nome = txt.replace('/remove ', '').strip()
                if nome in dados["produtos"]:
                    del dados["produtos"][nome]
                    print(f"🗑️ Removido do JSON: {nome}")
                    
            elif txt.startswith('/addgrupo '):
                nome = txt.replace('/addgrupo ', '').strip().replace('@', '')
                if nome not in dados["grupos"]:
                    dados["grupos"].append(nome)
                    print(f"✅ Grupo Salvo no JSON: {nome}")
                    
            elif txt.startswith('/removegrupo '):
                nome = txt.replace('/removegrupo ', '').strip().replace('@', '')
                if nome in dados["grupos"]:
                    dados["grupos"].remove(nome)
                    print(f"🗑️ Grupo Removido do JSON: {nome}")

        # Atualiza o "marcador" de leitura
        if msg.id > dados["ultima_mensagem_id"]:
            dados["ultima_mensagem_id"] = msg.id

    return dados

def buscar_promocoes():
    # 1. Carrega o banco de dados permanente
    dados_salvos = carregar_dados()
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id
        
        # 2. Atualiza o banco de dados se houver mensagens novas no chat
        dados_atualizados = atualizar_banco_pelo_chat(client, dados_salvos)
        salvar_dados(dados_atualizados) # Salva no disco
        
        meus_produtos = dados_atualizados["produtos"]
        meus_grupos = dados_atualizados["grupos"]
        
        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de produtos está vazia! Mande:\n`/add playstation 5 3200`")
            return
            
        if not meus_grupos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de grupos está vazia! Mande:\n`/addgrupo @nome_do_grupo`")
            return

        encontrados = []
        nao_encontrados = list(meus_produtos.keys())
        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=10)
        
        # 3. Faz a varredura normal nas promoções
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
