import os
import re
import json
import urllib.request
import urllib.parse
import urllib.error
from datetime import datetime, timedelta, timezone
from telethon.sync import TelegramClient
from telethon.sessions import StringSession

# Variáveis seguras de ambiente
API_ID = int(os.environ['API_ID'])
API_HASH = os.environ['API_HASH']
SESSION_STRING = os.environ['SESSION_STRING']
BOT_TOKEN = os.environ['BOT_TOKEN']

# ID do grupo de destino (tenta o ID normal e possui fallback automático para Supergrupo -100)
GRUPO_DESTINO_ID = "-4362764481"

# Caminho absoluto para garantir que o crontab sempre ache o JSON na pasta correta
DIRETORIO_ATUAL = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_DADOS = os.path.join(DIRETORIO_ATUAL, 'dados_bot.json')

# Grupos iniciais padrão
GRUPOS_BASE = [
    'PoisonPromos',
    'Fraguas84Oficial',
    'tecnoarthardware',
    'gamerbrasilpromos'
]

def disparar_telegram(chat_id, texto):
    """Função interna que faz a requisição HTTP em modo HTML (não quebra com links)."""
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
    """Envia mensagem pelo bot e tenta corrigir automaticamente se o grupo virou Supergrupo (-100)."""
    try:
        disparar_telegram(chat_id, texto)
    except urllib.error.HTTPError as e:
        erro_detalhe = e.read().decode('utf-8', errors='ignore')
        print(f"⚠️ Erro na API do Telegram para o ID {chat_id}: {erro_detalhe}")
        
        # Se o grupo normal virou Supergrupo, tenta automaticamente com o prefixo -100
        str_id = str(chat_id)
        if str_id.startswith("-") and not str_id.startswith("-100"):
            supergrupo_id = "-100" + str_id[1:]
            print(f"🔄 Tentando reenviar como Supergrupo ({supergrupo_id})...")
            try:
                disparar_telegram(supergrupo_id, texto)
                print("✅ Enviado com sucesso usando o prefixo -100!")
            except Exception as e2:
                print(f"❌ Falha também no ID {supergrupo_id}: {e2}")
    except Exception as e:
        print(f"❌ Erro de conexão ao enviar mensagem: {e}")

def carregar_dados():
    """Lê o arquivo JSON. Se não existir, cria a estrutura básica."""
    if os.path.exists(ARQUIVO_DADOS):
        try:
            with open(ARQUIVO_DADOS, 'r', encoding='utf-8') as f:
                dados = json.load(f)
                # Garante que a chave de controle anti-spam exista em JSONs antigos
                if "alertas_enviados" not in dados:
                    dados["alertas_enviados"] = []
                return dados
        except Exception as e:
            print(f"Erro ao ler JSON, recriando estrutura: {e}")

    return {
        "ultima_mensagem_id": 0,
        "produtos": {},
        "grupos": GRUPOS_BASE,
        "alertas_enviados": []
    }

def salvar_dados(dados):
    """Salva as alterações permanentemente no arquivo JSON."""
    # Mantém apenas os últimos 300 alertas no histórico para o arquivo nunca crescer demais
    dados["alertas_enviados"] = dados.get("alertas_enviados", [])[-300:]
    with open(ARQUIVO_DADOS, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=4, ensure_ascii=False)

def atualizar_banco_pelo_chat(client, dados):
    """Lê APENAS as mensagens novas enviadas ao bot e atualiza o JSON."""
    ultimo_id = dados.get("ultima_mensagem_id", 0)
    novas_mensagens = []

    for msg in client.iter_messages('Monitordepromos99_bot', min_id=ultimo_id):
        novas_mensagens.append(msg)

    if not novas_mensagens:
        return dados

    novas_mensagens.reverse()

    for msg in novas_mensagens:
        if msg.text:
            txt = msg.text.lower().strip()

            if txt.startswith('/add '):
                partes = txt.split()
                if len(partes) >= 3:
                    try:
                        preco = float(partes[-1].replace(',', '.'))
                        nome = " ".join(partes[1:-1]).strip()
                        dados["produtos"][nome] = preco
                        print(f"✅ Salvo no JSON: {nome} (R$ {preco:.2f})")
                        enviar_msg_bot(GRUPO_DESTINO_ID, f"✅ <b>Monitorando novo item:</b> {nome} (Até R$ {preco:.2f})")
                    except ValueError:
                        continue

            elif txt.startswith('/remove '):
                nome = txt.replace('/remove ', '').strip()
                if nome in dados["produtos"]:
                    del dados["produtos"][nome]
                    print(f"🗑️ Removido do JSON: {nome}")
                    enviar_msg_bot(GRUPO_DESTINO_ID, f"🗑️ <b>Item removido:</b> {nome}")

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

            elif txt == '/lista':
                resumo = "📋 <b>Produtos Monitorados:</b>\n"
                for p, v in dados["produtos"].items():
                    resumo += f"• {p}: R$ {v:.2f}\n"
                enviar_msg_bot(GRUPO_DESTINO_ID, resumo)

        if msg.id > dados["ultima_mensagem_id"]:
            dados["ultima_mensagem_id"] = msg.id

    return dados

def buscar_promocoes():
    dados_salvos = carregar_dados()

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    with client:
        meu_id = client.get_me().id

        # Atualiza o banco de dados com comandos novos
        dados_atualizados = atualizar_banco_pelo_chat(client, dados_salvos)
        meus_produtos = dados_atualizados["produtos"]
        meus_grupos = dados_atualizados["grupos"]
        alertas_enviados = dados_atualizados["alertas_enviados"]

        if not meus_produtos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de produtos está vazia! Mande:\n<code>/add playstation 5 3200</code>")
            salvar_dados(dados_atualizados)
            return

        if not meus_grupos:
            enviar_msg_bot(meu_id, "⚠️ Sua lista de grupos está vazia! Mande:\n<code>/addgrupo @nome_do_grupo</code>")
            salvar_dados(dados_atualizados)
            return

        tempo_limite = datetime.now(timezone.utc) - timedelta(hours=2)

        for grupo in meus_grupos:
            print(f"Vasculhando o grupo: {grupo}")
            try:
                for message in client.iter_messages(grupo, limit=35):
                    if not message.date or message.date < tempo_limite or not message.text:
                        continue

                    texto_msg = message.text.lower()

                    for produto, preco_max in meus_produtos.items():
                        # Verifica se todas as palavras do produto estão na mensagem
                        palavras_produto = produto.split()
                        if all(palavra in texto_msg for palavra in palavras_produto):
                            
                            # Cria identificador único para não repetir a mesma oferta a cada 15 min
                            id_unico_oferta = f"{grupo}_{message.id}_{produto}"
                            if id_unico_oferta in alertas_enviados:
                                continue

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
                                        link = re.search(r'(https?://[^\s]+)', message.text)
                                        link_txt = link.group(1) if link else "Link não encontrado na mensagem."

                                        alerta = (
                                            f"🚨 <b>Preço Atingido!</b>\n\n"
                                            f"🛒 <b>Produto:</b> {produto} por <b>R$ {menor_preco:.2f}</b>\n"
                                            f"📦 <b>Grupo:</b> @{grupo}\n"
                                            f"🔗 {link_txt}"
                                        )
                                        enviar_msg_bot(GRUPO_DESTINO_ID, alerta)
                                        alertas_enviados.append(id_unico_oferta)
                                        print(f"🎯 Oferta enviada: {produto} por R$ {menor_preco:.2f}")
            except Exception as e:
                print(f"Não foi possível ler o grupo {grupo}. Erro: {e}")

        # Salva o JSON ao final com a lista de alertas já enviados atualizada
        salvar_dados(dados_atualizados)

if __name__ == '__main__':
    buscar_promocoes()
