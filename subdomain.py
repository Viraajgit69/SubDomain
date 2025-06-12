import logging
from telegram import Update, ReplyKeyboardMarkup
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
CLOUDFLARE_API_TOKEN = "valtAAlNQyJf1-7mpjQQmUN3zCE3w_vWt2uVt3PR"
ZONE_ID = "dc34f5360b5d7563d67d4735f3ee8464"
DOMAIN = "fnxdanger.com"

# Initialize Cloudflare client
cf = CloudFlare.CloudFlare(token=CLOUDFLARE_API_TOKEN)

# Conversation states
CHOOSING_ACTION, SUBDOMAIN, IP_ADDRESS = range(3)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["Add Domain"], ["Remove Domain"], ["Update Domain"]]
    markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "\U0001F31F Domain Manager Bot \U0001F31F\nSelect an action below or use /help for detailed instructions:",
        reply_markup=markup
    )
    return CHOOSING_ACTION

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Use the following options:\n"
        "- Add Domain: Create a new subdomain.\n"
        "- Remove Domain: Delete an existing subdomain.\n"
        "- Update Domain: Modify an existing subdomain.\n"
        "Example: Select 'Add Domain' and follow the prompts."
    )

async def action_choice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
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
    context.user_data["subdomain"] = update.message.text.lower()
    full_domain = f"{context.user_data['subdomain']}.{DOMAIN}"
    if context.user_data["action"] in ["Add Domain", "Update Domain"]:
        await update.message.reply_text("Please provide the IP address:")
        return IP_ADDRESS
    elif context.user_data["action"] == "Remove Domain":
        try:
            dns_records = cf.zones.dns_records.get(ZONE_ID)
            for record in dns_records:
                if record["name"] == full_domain:
                    cf.zones.dns_records.delete(ZONE_ID, record["id"])
                    await update.message.reply_text(f"Successfully removed {full_domain}")
                    return ConversationHandler.END
            await update.message.reply_text(f"Subdomain {full_domain} not found!")
        except Exception as e:
            logger.error(f"Error removing subdomain: {e}")
            await update.message.reply_text(f"Failed to remove subdomain: {str(e)}")
        return ConversationHandler.END

async def ip_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["ip"] = update.message.text
    full_domain = f"{context.user_data['subdomain']}.{DOMAIN}"
    try:
        dns_records = cf.zones.dns_records.get(ZONE_ID)
        if context.user_data["action"] == "Add Domain":
            for record in dns_records:
                if record["name"] == full_domain:
                    await update.message.reply_text(f"Subdomain {full_domain} already exists!")
                    return ConversationHandler.END
            cf.zones.dns_records.post(ZONE_ID, data={
                "type": "A",
                "name": context.user_data["subdomain"],
                "content": context.user_data["ip"],
                "ttl": 3600,
                "proxied": True
            })
            await update.message.reply_text(f"Success! {full_domain} created with IP {context.user_data['ip']}")
        elif context.user_data["action"] == "Update Domain":
            for record in dns_records:
                if record["name"] == full_domain:
                    cf.zones.dns_records.put(ZONE_ID, record["id"], data={
                        "type": "A",
                        "name": context.user_data["subdomain"],
                        "content": context.user_data["ip"],
                        "ttl": 3600,
                        "proxied": True
                    })
                    await update.message.reply_text(f"Success! {full_domain} updated with IP {context.user_data['ip']}")
                    return ConversationHandler.END
            await update.message.reply_text(f"Subdomain {full_domain} not found!")
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error creating/updating subdomain: {e}")
        await update.message.reply_text(f"Failed to create/update subdomain: {str(e)}")
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Conversation canceled.")
    return ConversationHandler.END

def main() -> None:
    application = Application.builder().token("7984340301:AAEGaPuPOEdQ8FTc7TuwC1tLHRm1R_NG4so").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, action_choice)],
            SUBDOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, subdomain_handler)],
            IP_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ip_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.run_polling()

if __name__ == "__main__":
    main()
