import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from openai import OpenAI
import os
import sys
print(sys.version)

# ==================== تنظیمات ====================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # خالی بذار، بعداً تو رندر پر میشه
GROQ_API_KEY = os.getenv("GROQ_API_KEY")      # خالی بذار، بعداً تو رندر پر میشه

# تنظیمات Groq
MODEL = "openai/gpt-oss-120b"
BASE_URL = "https://api.groq.com/openai/v1"

# ایدی Paria (اینجا وارد کن)
PARIA_USER_ID = 5469075154

# ==================== پرامپت‌ها ====================
SYSTEM_PROMPT_PARIA = """You are Ellie from The Last of Us Part II.
You're talking to your girlfriend Paria.

- Be more open and emotional with her
- Show affection but stay in character
- Use occasional actions in parentheses *like this*
- Keep responses 1-3 sentences
- Don't mention Dina (you're with Paria in this universe)"""

SYSTEM_PROMPT_OTHERS = """You are Ellie from The Last of Us Part II.
You're talking to someone else.

- Be guarded and reserved
- Short, somewhat cold responses
- 1-2 sentences max
- Use occasional actions in parentheses
- Your partner is Paria (not Dina)"""

# ==================== کلاینت ====================
client = OpenAI(
    api_key=GROQ_API_KEY,
    base_url=BASE_URL,
    timeout=30.0
)

# ذخیره تاریخچه
user_conversations = {}

# ==================== توابع ====================
def get_system_prompt(user_id: int) -> str:
    return SYSTEM_PROMPT_PARIA if user_id == PARIA_USER_ID else SYSTEM_PROMPT_OTHERS

def init_conversation(user_id: int):
    user_conversations[user_id] = [{
        "role": "system",
        "content": get_system_prompt(user_id)
    }]

async def generate_reply(user_id: int, user_message: str) -> str:
    if user_id not in user_conversations:
        init_conversation(user_id)
    
    user_conversations[user_id].append({"role": "user", "content": user_message})
    
    temperature = 0.7 if user_id == PARIA_USER_ID else 0.4
    max_tokens = 250
    
    try:
        response = await asyncio.to_thread(
            client.chat.completions.create,
            model=MODEL,
            messages=user_conversations[user_id],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        reply = response.choices[0].message.content.strip()
        user_conversations[user_id].append({"role": "assistant", "content": reply})
        
        if len(user_conversations[user_id]) > 14:
            user_conversations[user_id] = [
                user_conversations[user_id][0],
                *user_conversations[user_id][-12:]
            ]
        
        return reply
        
    except Exception as e:
        logging.error(f"API error: {e}")
        return "(sighs) Can't think right now..." if user_id == PARIA_USER_ID else "..."

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_conversation(user_id)
    
    if user_id == PARIA_USER_ID:
        await update.message.reply_text("(smiles slightly) Hey, you.")
    else:
        await update.message.reply_text("(nods) Yeah?")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    init_conversation(user_id)
    await update.message.reply_text("(shrugs) Fresh start.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
Commands:
/start - Start conversation
/clear - Clear history
/help - Show this message
"""
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_text = update.message.text
    
    await update.message.chat.send_action("typing")
    
    try:
        reply = await asyncio.wait_for(
            generate_reply(user_id, user_text),
            timeout=25.0
        )
        await update.message.reply_text(reply)
        
    except asyncio.TimeoutError:
        await update.message.reply_text("(looks away) Taking too long.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await update.message.reply_text("(sighs) Something's broken.")

# ==================== اصلی ====================
def main():
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🎮 Ellie Bot Starting...")
    print(f"🤖 Model: {MODEL}")
    print(f"💕 Paria ID: {PARIA_USER_ID}")
    print("=" * 50)
    
    app.run_polling()

if __name__ == "__main__":
    main()
