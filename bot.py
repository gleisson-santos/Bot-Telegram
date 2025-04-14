import os
import logging
import json
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from collections import defaultdict
import asyncio

# Configuração de logging para depuração
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Carrega variáveis de ambiente do arquivo .env
logger.info("Tentando carregar o arquivo .env...")
load_dotenv()
logger.info("Arquivo .env carregado com sucesso.")

# Verifica o caminho do arquivo .env
env_path = Path(".") / ".env"
logger.info(f"Procurando o arquivo .env em: {env_path.resolve()}")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Verifica se as variáveis de ambiente estão definidas
if not TELEGRAM_TOKEN or not MAKE_WEBHOOK_URL or not TELEGRAM_CHANNEL_ID:
    logger.error("As variáveis TELEGRAM_TOKEN, MAKE_WEBHOOK_URL e TELEGRAM_CHANNEL_ID não foram encontradas.")
    raise ValueError("As variáveis TELEGRAM_TOKEN, MAKE_WEBHOOK_URL e TELEGRAM_CHANNEL_ID devem ser definidas no arquivo .env")
logger.info("Variáveis carregadas com sucesso.")

# Inicializa a aplicação do Telegram
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Dicionário para armazenar imagens de uma galeria por media_group_id
media_groups = defaultdict(list)
processed_media_groups = set()

# Classe para o servidor HTTP
class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    pass

class WebhookHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/ping":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"Pong! Online")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data.decode('utf-8'))

            if "file_url" not in data:
                self.send_response(400)
                self.end_headers()
                return

            file_url = data["file_url"]
            caption = data.get("caption", "Imagem processada.")

            loop = asyncio.get_event_loop()
            coro = application.bot.send_photo(
                chat_id=TELEGRAM_CHANNEL_ID,
                photo=file_url,
                caption=caption
            )
            asyncio.run_coroutine_threadsafe(coro, loop).result()

            self.send_response(200)
            self.end_headers()

        except Exception as e:
            logger.error("Erro no webhook: %s", str(e))
            self.send_response(500)
            self.end_headers()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Olá! Envie uma imagem ou galeria.")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    media_group_id = message.media_group_id

    caption = message.caption if message.caption else ""
    source_chat_name = message.forward_from_chat.title if message.forward_from_chat else message.chat.title or "Desconhecido"
    source_chat_id = str(message.forward_from_chat.id) if message.forward_from_chat else str(message.chat.id)

    if not media_group_id:
        await process_single_image(update, context, caption, source_chat_name, source_chat_id)
        return

    media_groups[media_group_id].append((update, caption, source_chat_name, source_chat_id))
    await asyncio.sleep(2)

    if media_group_id in processed_media_groups:
        return

    if media_group_id in media_groups:
        updates_with_metadata = media_groups[media_group_id]

        highest_resolution_photo = None
        highest_resolution_update = None
        selected_caption = None
        selected_source_chat_name = None
        selected_source_chat_id = None
        max_resolution = 0

        for u, cap, name, cid in updates_with_metadata:
            photo = max(u.message.photo, key=lambda p: p.width * p.height)
            resolution = photo.width * photo.height
            if resolution > max_resolution:
                max_resolution = resolution
                highest_resolution_photo = photo
                highest_resolution_update = u
                selected_caption = cap
                selected_source_chat_name = name
                selected_source_chat_id = cid

        if highest_resolution_photo:
            await process_single_image(highest_resolution_update, context, selected_caption, selected_source_chat_name, selected_source_chat_id)

        processed_media_groups.add(media_group_id)
        del media_groups[media_group_id]

async def process_single_image(update: Update, context: ContextTypes.DEFAULT_TYPE, caption: str, source_chat_name: str, source_chat_id: str) -> None:
    try:
        if not update.message.photo:
            await update.message.reply_text("Envie uma imagem válida.")
            return

        highest_resolution_photo = max(update.message.photo, key=lambda p: p.width * p.height)
        file = await context.bot.get_file(highest_resolution_photo.file_id)
        file_url = file.file_path

        payload = {
            "file_url": file_url,
            "caption": caption,
            "source_chat_name": source_chat_name,
            "source_chat_id": source_chat_id
        }

        response = requests.post(MAKE_WEBHOOK_URL, json=payload)

        if response.status_code == 200:
            await update.message.reply_text("Imagem enviada com sucesso!")
        else:
            await update.message.reply_text("Erro ao enviar a imagem.")

    except Exception as e:
        logger.error("Erro ao processar imagem: %s", str(e))
        await update.message.reply_text("Ocorreu um erro ao processar a imagem.")

# Registra os handlers no bot
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Inicia o servidor HTTP em uma thread separada
thread = Thread(target=run_http_server := lambda: ThreadingHTTPServer(("0.0.0.0", int(os.getenv("PORT", 5000))), WebhookHandler).serve_forever())
thread.start()

# Inicia o bot
if __name__ == "__main__":
    application.run_polling()
