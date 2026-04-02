import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
conversation_history = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я бот на базе Claude. Задай мне любой вопрос!")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conversation_history[user_id] = []
    await update.message.reply_text("История диалога очищена.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    chat_id = message.chat_id
    user_name = message.from_user.first_name or "Участник"
    text = message.text

    # Инициализируем историю чата
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []

    # Всегда сохраняем сообщение в историю с именем автора
    conversation_history[chat_id].append({
        "role": "user",
        "content": f"{user_name}: {text}"
    })

    # Ограничиваем историю последними 50 сообщениями
    conversation_history[chat_id] = conversation_history[chat_id][-50:]

    # Проверяем нужно ли отвечать
    is_private = message.chat.type == "private"
    is_mentioned = (
        f"@{context.bot.username}" in text or
        "стасик" in text.lower() or
        "ботик" in text.lower()
    )
    is_reply_to_bot = (
        message.reply_to_message and
        message.reply_to_message.from_user.id == context.bot.id
    )

    if not is_private and not is_mentioned and not is_reply_to_bot:
        return

    # Отвечаем
    history = conversation_history[chat_id][-50:]
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system="Ты участник группового чата по имени Стасик. Ты читаешь все сообщения группы и знаешь контекст беседы. Отвечай естественно, как живой участник чата. Обращайся к людям по имени.",
            messages=history
        )
        reply = response.content[0].text
        conversation_history[chat_id].append({
            "role": "assistant",
            "content": reply
        })
        await message.reply_text(reply)
    except Exception as e:
        await message.reply_text(f"Ошибка: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Бот запущен...")
    app.run_polling()
