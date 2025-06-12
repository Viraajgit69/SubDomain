import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)
import CloudFlare

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cloudflare configuration
CLOUDFLARE_API_TOKEN = "qEwlnRQFGTgOCiiJDl8LrObdWmm-WhAiLl9KUBJR"
ZONE_ID = "dc34f5360b5d7563d67d4735f3ee8464"
DOMAIN = "fnxdanger.com"  # Update to your domain

# Initialize Cloudflare client
cf = Cloudflare(api_token=CLOUDFLARE_API_TOKEN)

# Conversation states
CHOOSING_ACTION, SUBDOMAIN, IP_ADDRESS = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the conversation and show action options."""
    reply_keyboard = [
        ["Add Domain"],
        ["Remove Domain"],
        ["Update Domain"],
    ]
    await update.message.reply_text(
        "🌟 Domain Manager Bot 🌟\nSelect an action below or use /help for detailed instructions:",
        reply_markup={"keyboard": reply_keyboard, "one_time_keyboard": True},
    )
    return CHOOSING_ACTION

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a help message."""
    await update.message.reply_text(
        "Use the following options:\n"
        "- Add Domain: Create a new subdomain.\n"
        "- Remove Domain: Delete an existing subdomain.\n"
        "- Update Domain: Modify an existing subdomain.\n"
        "Example: Select 'Add Domain' and follow the prompts."
    )

async def action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the user's action choice."""
    context.user_data["action"] = update.message.text
    if update.message.text == "Add Domain":
        await update.message.reply_text("Enter your desired subdomain:")
        return SUBDOMAIN
    elif update.message.text == "Remove Domain":
        await update.message.reply_text("Enter the subdomain to remove:")
        return SUBDOMAIN
    elif update.message.text == "Update Domain":
        await update.message.reply_text("Enter the subdomain to update:")
        return SUBDOMAIN
    return ConversationHandler.END

async def subdomain_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the subdomain input."""
    context.user_data["subdomain"] = update.message.text.lower()
    if context.user_data["action"] == "Add Domain" or context.user_data["action"] == "Update Domain":
        await update.message.reply_text("Please provide the IP address:")
        return IP_ADDRESS
    elif context.user_data["action"] == "Remove Domain":
        try:
            dns_records = cf.dns.records.list(zone_id=ZONE_ID)
            for record in dns_records:
                if record.name == f"{context.user_data['subdomain']}.{DOMAIN}":
                    cf.dns.records.delete(zone_id=ZONE_ID, record_id=record.id)
                    await update.message.reply_text(f"Successfully removed {context.user_data['subdomain']}.{DOMAIN}")
                    return ConversationHandler.END
            await update.message.reply_text(f"Subdomain {context.user_data['subdomain']}.{DOMAIN} not found!")
        except Exception as e:
            logger.error(f"Error removing subdomain: {e}")
            await update.message.reply_text(f"Failed to remove subdomain: {str(e)}")
        return ConversationHandler.END

async def ip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle the IP address input and create/update the DNS record."""
    context.user_data["ip"] = update.message.text
    full_domain = f"{context.user_data['subdomain']}.{DOMAIN}"
    try:
        if context.user_data["action"] == "Add Domain":
            dns_records = cf.dns.records.list(zone_id=ZONE_ID)
            for record in dns_records:
                if record.name == full_domain:
                    await update.message.reply_text(f"Subdomain {full_domain} already exists!")
                    return ConversationHandler.END
            cf.dns.records.create(
                zone_id=ZONE_ID,
                type="A",
                name=context.user_data["subdomain"],
                content=context.user_data["ip"],
                ttl=3600,
                proxied=True
            )
            await update.message.reply_text(f"Success! {full_domain} created with IP {context.user_data['ip']}")
        elif context.user_data["action"] == "Update Domain":
            dns_records = cf.dns.records.list(zone_id=ZONE_ID)
            for record in dns_records:
                if record.name == full_domain:
                    cf.dns.records.update(
                        zone_id=ZONE_ID,
                        record_id=record.id,
                        type="A",
                        name=context.user_data["subdomain"],
                        content=context.user_data["ip"],
                        ttl=3600,
                        proxied=True
                    )
                    await update.message.reply_text(f"Success! {full_domain} updated with IP {context.user_data['ip']}")
                    return ConversationHandler.END
            await update.message.reply_text(f"Subdomain {full_domain} not found!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error creating/updating subdomain: {e}")
        await update.message.reply_text(f"Failed to create/update subdomain: {str(e)}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text("Conversation canceled.")
    return ConversationHandler.END

def main() -> None:
    """Start the bot."""
    application = Application.builder().token("7984340301:AAEGaPuPOEdQ8FTc7TuwC1tLHRm1R_NG4so").build()

    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, action_choice)],
            SUBDOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, subdomain_handler)],
            IP_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ip_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    # Start the bot
    application.run_polling()

if __name__ == "__main__":
    main()
