import os
import logging
import requests
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

# Carrega variáveis do .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
MAKE_WEBHOOK_URL = os.getenv("MAKE_WEBHOOK_URL")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# Configuração de log
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Criação do aplicativo do Telegram
app = Application.builder().token(TELEGRAM_TOKEN).build()

# Função para lidar com fotos enviadas
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.photo:
        return

    caption = message.caption or "sem legenda"
    username = message.from_user.username or "desconhecido"
    file_id = message.photo[-1].file_id  # Última é a de melhor qualidade

    # Envia para canal
    await context.bot.send_photo(
        chat_id=TELEGRAM_CHANNEL_ID,
        photo=file_id,
        caption=f"🧠 Prompt de @{username}:\n\n{caption}",
    )

    # Envia para webhook do MAKE
    payload = {
        "username": username,
        "caption": caption,
        "file_id": file_id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    try:
        response = requests.post(MAKE_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        logger.info("✅ Dados enviados para o Make com sucesso.")
    except Exception as e:
        logger.error(f"❌ Erro ao enviar dados para o Make: {e}")

# Adiciona o handler para mensagens com foto
app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

# Inicializa o bot com polling
if __name__ == "__main__":
    logger.info("🤖 Bot está rodando...")
    app.run_polling(drop_pending_updates=True)
