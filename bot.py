import os
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import CommandHandler, MessageHandler, filters, Application, ContextTypes

# Carrega variáveis do .env
load_dotenv()

# Configurações
TOKEN = os.getenv("TELEGRAM_TOKEN")
WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cria aplicação do bot
app = Application.builder().token(TOKEN).build()
bot = Bot(token=TOKEN)

# Comando de inicialização
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Olá! Envie uma imagem e uma legenda que eu reenviarei para o canal.")

app.add_handler(CommandHandler("start", start))

# Tratador de mensagens com imagem
async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    caption = message.caption or ""

    if message.photo:
        # Seleciona a imagem com maior resolução
        photo = message.photo[-1]
        file_id = photo.file_id

        # Envia imagem ao canal
        await bot.send_photo(chat_id=CHANNEL_ID, photo=file_id, caption=caption)
        logger.info("Imagem enviada para o canal.")
    else:
        await message.reply_text("Por favor, envie uma imagem com uma legenda.")

app.add_handler(MessageHandler(filters.PHOTO, handle_image))

# Webhook handler
class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = self.rfile.read(length)

        update = Update.de_json(data.decode("utf-8"), bot)
        app.update_queue.put(update)

        self.send_response(200)
        self.end_headers()

def run_webhook_server():
    port = int(os.getenv("PORT", 5000))
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    logger.info(f"🌐 Servidor Webhook rodando na porta {port}")
    server.serve_forever()

if __name__ == "__main__":
    logger.info("🤖 Iniciando bot com Webhook...")
    bot.delete_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    Thread(target=run_webhook_server).start()
