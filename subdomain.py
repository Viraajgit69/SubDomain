import logging
import Cloudflare
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cloudflare configuration
CLOUDFLARE_API_TOKEN = "YOUR_CLOUDFLARE_API_TOKEN"  # Replace with your Cloudflare API token
ZONE_ID = "YOUR_CLOUDFLARE_ZONE_ID"  # Replace with your Cloudflare Zone ID
DOMAIN = "example.com"  # Replace with your domain

# Initialize Cloudflare client
cf = Cloudflare.Cloudflare(api_token=CLOUDFLARE_API_TOKEN)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a welcome message when the /start command is issued."""
    await update.message.reply_text(
        "Welcome to the Cloudflare Subdomain Bot! Use /create <subdomain> to create a new subdomain."
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message when the /help command is issued."""
    await update.message.reply_text(
        "Use /create <subdomain> to create a new subdomain on Cloudflare.\n"
        "Example: /create test will create test.example.com"
    )

async def create_subdomain(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /create command to create a subdomain."""
    if not context.args:
        await update.message.reply_text("Please provide a subdomain. Usage: /create <subdomain>")
        return

    subdomain = context.args[0].lower()
    full_domain = f"{subdomain}.{DOMAIN}"

    try:
        # Check if DNS record already exists
        dns_records = cf.dns.records.list(zone_id=ZONE_ID)
        for record in dns_records:
            if record.name == full_domain:
                await update.message.reply_text(f"Subdomain {full_domain} already exists!")
                return

        # Create DNS record (A record pointing to an example IP, e.g., 192.0.2.1)
        dns_record = cf.dns.records.create(
            zone_id=ZONE_ID,
            type="A",
            name=subdomain,
            content="192.0.2.1",  # Replace with your target IP
            ttl=3600,
            proxied=True  # Enable Cloudflare proxy
        )
        await update.message.reply_text(f"Successfully created subdomain: {full_domain}")

    except Exception as e:
        logger.error(f"Error creating subdomain: {e}")
        await update.message.reply_text(f"Failed to create subdomain: {str(e)}")

async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo non-command messages."""
    await update.message.reply_text(
        "Please use /create <subdomain> to create a subdomain or /help for more info."
    )

def main() -> None:
    """Start the bot."""
    # Replace 'YOUR_TELEGRAM_BOT_TOKEN' with the token from BotFather
    application = Application.builder().token("YOUR_TELEGRAM_BOT_TOKEN").build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("create", create_subdomain))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
