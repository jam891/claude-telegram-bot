import os
import anthropic
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from duckduckgo_search import DDGS

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
conversation_history = {}

def search_web(query: str) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=3))
            if results:
                return "\n".join([f"- {r['title']}: {r['body']}" for r in results])
            return "Ничего не найдено"
    except Exception as e:
        return f"Ошибка поиска: {str(e)}"

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
    if chat_id not in conversation_history:
        conversation_history[chat_id] = []
    conversation_history[chat_id].append({"role": "user", "content": f"{user_name}: {text}"})
    conversation_history[chat_id] = conversation_history[chat_id][-50:]
    is_private = message.chat.type == "private"
    is_mentioned = (f"@{context.bot.username}" in text or "стасик" in text.lower() or "ботик" in text.lower())
    is_reply_to_bot = (message.reply_to_message and message.reply_to_message.from_user.id == context.bot.id)
    if not is_private and not is_mentioned and not is_reply_to_bot:
        return
    chat_context = "\n".join([msg["content"] for msg in conversation_history[chat_id][-50:]])
    search_results = search_web(text)
    try:
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=1024,
            system=f"""Ты участник группового чата по имени Стасик. Вот последние сообщения чата:\n\n{chat_context}\n\nРезультаты поиска в интернете по последнему вопросу:\n{search_results}\n\nТы видишь всех участников, знаешь контекст беседы и имеешь доступ к актуальной информации из интернета. Отвечай естественно, обращайся к людям по имени.""",
            messages=[{"role": "user", "content": f"{user_name}: {text}"}]
        )
        reply = response.content[0].text
        conversation_history[chat_id].append({"role": "assistant", "content": reply})
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
