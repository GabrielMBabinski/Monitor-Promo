import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Variáveis seguras de ambiente
API_ID = int(os.environ['API_ID'])
API_HASH = os.environ['API_HASH']
SESSION_STRING = os.environ['SESSION_STRING']
BOT_TOKEN = os.environ['BOT_TOKEN']

# Configurações de destino e controle
GRUPO_DESTINO_ID = "-4362764481"
BOT_COMANDOS = 'Monitordepromos99_bot'

DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_ATUAL, 'dados_bot.json')

GRUPOS_BASE = [
    'PoisonPromos',
    'Fraguas84Oficial',
    'tecnoarthardware',
    'gamerbrasilpromos'
]

def disparar_telegram(chat_id, texto):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    dados_post = urllib.parse.urlencode({
        'chat_id': str(chat_id),
        'text': texto,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'false'
    }).encode('utf-8')
    req = urllib.request.Request(url, data=dados_post)
    urllib.request.urlopen(req, timeout=10)

def enviar_msg_bot(chat_id, texto):
    try:
        disparar_telegram(chat_id, texto)
    except urllib.error.HTTPError as e:
        str_id = str(chat_id)
        if str_id.startswith("-") and not str_id.startswith("-100"):
            try:
                disparar_telegram("-100" + str_id[1:], texto)
            except Exception as e2:
                print(f"❌ Erro ao enviar para supergrupo: {e2}")
        else:
            print(f"⚠️ Erro HTTP na API do Telegram: {e}")
    except Exception as e:
        print(f"❌ Erro de conexão: {e}")

def carregar_dados():
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao ler JSON: {e}")
    return {"produtos": {}, "grupos": GRUPOS_BASE}

def salvar_dados(dados):
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

# Carrega os dados na memória ao iniciar
dados = carregar_dados()

# Inicializa o cliente Telethon
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

# 1. ESCUTA COMANDOS ENVIADOS AO SEU BOT EM TEMPO REAL
@client.on(events.NewMessage(chats=BOT_COMANDOS))
async def gerenciar_comandos(event):
    if not event.text:
        return

    txt = event.text.lower().strip()

    if txt.startswith('/add '):
        partes = txt.split()
        if len(partes) >= 3:
            try:
                preco = float(partes[-1].replace(',', '.'))
                nome = " ".join(partes[1:-1]).strip()
                dados["produtos"][nome] = preco
                salvar_dados(dados)
                print(f"✅ Produto adicionado: {nome} (R$ {preco:.2f})")
                enviar_msg_bot(GRUPO_DESTINO_ID, f"✅ <b>Monitorando em tempo real:</b> {nome} (Até R$ {preco:.2f})")
            except ValueError:
                pass

    elif txt.startswith('/remove '):
        nome = txt.replace('/remove ', '').strip()
        if nome in dados["produtos"]:
            del dados["produtos"][nome]
            salvar_dados(dados)
            print(f"🗑️ Produto removido: {nome}")
            enviar_msg_bot(GRUPO_DESTINO_ID, f"🗑️ <b>Item removido:</b> {nome}")

    elif txt.startswith('/addgrupo '):
        nome = txt.replace('/addgrupo ', '').strip().replace('@', '')
        if nome.lower() not in [g.lower() for g in dados["grupos"]]:
            dados["grupos"].append(nome)
            salvar_dados(dados)
            print(f"✅ Grupo adicionado: {nome}")
            enviar_msg_bot(GRUPO_DESTINO_ID, f"📡 <b>Novo grupo monitorado:</b> @{nome}")

    elif txt.startswith('/removegrupo '):
        nome = txt.replace('/removegrupo ', '').strip().replace('@', '')
        for g in list(dados["grupos"]):
            if g.lower() == nome.lower():
                dados["grupos"].remove(g)
                salvar_dados(dados)
                print(f"🗑️ Grupo removido: {g}")
                enviar_msg_bot(GRUPO_DESTINO_ID, f"🗑️ <b>Grupo removido:</b> @{g}")

    elif txt == '/lista':
        if not dados["produtos"]:
            enviar_msg_bot(GRUPO_DESTINO_ID, "⚠️ Nenhum produto cadastrado no momento.")
            return
        resumo = "📋 <b>Produtos Monitorados (Tempo Real):</b>\n"
        for p, v in dados["produtos"].items():
            resumo += f"• {p}: R$ {v:.2f}\n"
        enviar_msg_bot(GRUPO_DESTINO_ID, resumo)

# 2. ESCUTA AS PROMOÇÕES NOS GRUPOS NO EXATO SEGUNDO EM QUE CAEM
@client.on(events.NewMessage(incoming=True))
async def monitorar_promocoes(event):
    if not event.text or not event.chat:
        return

    username_grupo = getattr(event.chat, 'username', None)
    if not username_grupo:
        return

    # Verifica se a mensagem veio de um dos grupos monitorados
    grupos_monitorados = [g.lower() for g in dados.get("grupos", [])]
    if username_grupo.lower() not in grupos_monitorados:
        return

    texto_msg = event.text.lower()
    meus_produtos = dados.get("produtos", {})

    for produto, preco_max in meus_produtos.items():
        palavras_produto = produto.split()
        if all(palavra in texto_msg for palavra in palavras_produto):
            precos = re.findall(r'r\$\s*(\d+(?:\.\d+)*(?:,\d+)?)', texto_msg)
            if precos:
                valores_convertidos = []
                for p in precos:
                    try:
                        valores_convertidos.append(float(p.replace('.', '').replace(',', '.')))
                    except ValueError:
                        continue

                if valores_convertidos:
                    menor_preco = min(valores_convertidos)
                    if menor_preco <= preco_max:
                        link = re.search(r'(https?://[^\s]+)', event.text)
                        link_txt = link.group(1) if link else f"https://t.me/{username_grupo}/{event.id}"

                        alerta = (
                            f"🚨 <b>Oferta em Tempo Real!</b>\n\n"
                            f"🛒 <b>Produto:</b> {produto} por <b>R$ {menor_preco:.2f}</b>\n"
                            f"📦 <b>Grupo:</b> @{username_grupo}\n"
                            f"🔗 {link_txt}"
                        )
                        enviar_msg_bot(GRUPO_DESTINO_ID, alerta)
                        print(f"🎯 Alerta instantâneo enviado: {produto} por R$ {menor_preco:.2f}")

if __name__ == '__main__':
    print("🚀 Iniciando Monitor de Promoções em Tempo Real (24/7)...")
    client.start()
    print("✅ Conectado! Escutando grupos e comandos ao vivo...")
    client.run_until_disconnected()
