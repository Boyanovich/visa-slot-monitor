import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- CONFIGURATION ---
# IMPORTANT: Replace with your actual bot token or use environment variables
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_TOKEN_HERE" 
SUBSCRIBERS_FILE = "subscribers.txt"
MAX_SUBSCRIBERS = 5

WELCOME_MESSAGE = "✅ You have successfully subscribed to slot notifications! Subscriber limit: 5."
ALREADY_SUBSCRIBED_MESSAGE = "ℹ️ You are already subscribed to notifications."
LIMIT_REACHED_MESSAGE = "🚫 Sorry, the maximum number of subscribers (5) has been reached."
ERROR_MESSAGE = "❌ An error occurred while adding you to the list. Please try again later."
UNSUBSCRIBE_MESSAGE = "📭 You have successfully unsubscribed from notifications."
NOT_SUBSCRIBED_MESSAGE = "❓ You were not subscribed to notifications."
UNSUBSCRIBE_ERROR_MESSAGE = "❌ An error occurred while unsubscribing. Please try again later."

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

def load_subscribers():
    try:
        with open(SUBSCRIBERS_FILE, "r") as f:
            return [line.strip() for line in f if line.strip().isdigit()]
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error loading subscribers: {e}")
        return []

def save_subscribers(subscribers):
    try:
        with open(SUBSCRIBERS_FILE, "w") as f:
            for sub_id in subscribers:
                f.write(f"{sub_id}\n")
        return True
    except Exception as e:
        logger.error(f"Error saving subscribers: {e}")
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    current_subscribers = load_subscribers()
    
    if user_id in current_subscribers:
        await update.message.reply_text(ALREADY_SUBSCRIBED_MESSAGE)
        return

    if len(current_subscribers) >= MAX_SUBSCRIBERS:
        await update.message.reply_text(LIMIT_REACHED_MESSAGE)
        return

    current_subscribers.append(user_id)
    if save_subscribers(current_subscribers):
        await update.message.reply_text(WELCOME_MESSAGE)
        logger.info(f"User {user_id} successfully added.")
    else:
        await update.message.reply_text(ERROR_MESSAGE)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    
    current_subscribers = load_subscribers()
    
    if user_id not in current_subscribers:
        await update.message.reply_text(NOT_SUBSCRIBED_MESSAGE)
        return

    try:
        current_subscribers.remove(user_id)
        if save_subscribers(current_subscribers):
            await update.message.reply_text(UNSUBSCRIBE_MESSAGE)
            logger.info(f"User {user_id} unsubscribed.")
        else:
            await update.message.reply_text(UNSUBSCRIBE_ERROR_MESSAGE)
    except Exception as e:
         await update.message.reply_text(UNSUBSCRIBE_ERROR_MESSAGE)
         logger.error(f"Error unsubscribing user {user_id}: {e}")

def main() -> None:
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    
    logger.info("Subscription management bot has started.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()