import os
import logging
import json
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from threading import Thread
from telegram import Update, InputMediaPhoto
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram.constants import ChatAction
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
DESTINATION_CHANNEL_ID = os.getenv("DEST_CHANNEL_ID")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

app = Application.builder().token(TOKEN).build()

# Função principal para tratar mensagens com foto
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        message = update.message
        caption = message.caption
        photos = message.photo
        chat_id = message.chat.id
        username = message.chat.username or "sem_username"

        if not photos:
            return

        # Enviar ação de "enviando imagem"
        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.UPLOAD_PHOTO)

        # Pega a maior resolução da foto (última da lista)
        file_id = photos[-1].file_id

        # Monta legenda final
        final_caption = f"🧠 Prompt de @{username}:\n\n{caption or 'sem legenda'}"

        # Encaminha imagem para o canal
        await context.bot.send_photo(
            chat_id=DESTINATION_CHANNEL_ID,
            photo=file_id,
            caption=final_caption,
        )

# Adiciona o handler para mensagens com foto
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# === WEBHOOK para deploy em serviços como Render/Railway ===

class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)
        update = Update.de_json(json.loads(body), app.bot)
        app.update_queue.put_nowait(update)
        self.send_response(200)
        self.end_headers()

def start_webhook():
    def run_http_server():
        server_address = ("0.0.0.0", int(os.getenv("PORT", 5000)))
        httpd = ThreadingHTTPServer(server_address, WebhookHandler)
        print(f"🚀 Webhook rodando na porta {server_address[1]}")
        httpd.serve_forever()

    thread = Thread(target=run_http_server)
    thread.start()

# === MAIN ===
if __name__ == "__main__":
    print("🤖 Bot iniciado...")
    start_webhook()
    app.run_polling(drop_pending_updates=True)
