import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ========== CONFIGURATION ==========
# Get from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# Validate
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set")
    print("Set it in Render → Environment tab")
    exit(1)

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    print("⚠️ WARNING: ADMIN_ID not set")
    ADMIN_ID = None
# ===================================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
PHONE, RECEIPT, ID_PHOTO, PRODUCT_PHOTO = range(4)

# Store user data
users = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Welcome! I'll help verify your product purchase.\n\n"
        "Send /verify to begin."
    )

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start verification process."""
    await update.message.reply_text(
        "📱 **Step 1: Phone Verification**\n\n"
        "Please share your phone number:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Phone", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return PHONE

async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number."""
    contact = update.message.contact
    user_id = update.effective_user.id
    
    # Store user data
    users[user_id] = {
        'phone': contact.phone_number,
        'name': update.effective_user.full_name,
        'username': update.effective_user.username
    }
    
    await update.message.reply_text(
        f"✅ Phone: {contact.phone_number}\n\n"
        "📄 **Step 2: Receipt**\n"
        "Send photo of purchase receipt:",
        reply_markup=ReplyKeyboardRemove()
    )
    return RECEIPT

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt photo."""
    if update.message.photo:
        user_id = update.effective_user.id
        users[user_id]['receipt'] = update.message.photo[-1].file_id
        
        await update.message.reply_text(
            "✅ Receipt received!\n\n"
            "🆔 **Step 3: ID**\n"
            "Send photo of your ID:"
        )
        return ID_PHOTO
    else:
        await update.message.reply_text("Please send a photo")
        return RECEIPT

async def id_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ID photo."""
    if update.message.photo:
        user_id = update.effective_user.id
        users[user_id]['id_photo'] = update.message.photo[-1].file_id
        
        await update.message.reply_text(
            "✅ ID received!\n\n"
            "📦 **Step 4: Product**\n"
            "Send photo of your product:"
        )
        return PRODUCT_PHOTO
    else:
        await update.message.reply_text("Please send a photo")
        return ID_PHOTO

async def product_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle product photo."""
    if update.message.photo:
        user_id = update.effective_user.id
        users[user_id]['product_photo'] = update.message.photo[-1].file_id
        
        # Confirm to user
        await update.message.reply_text(
            "🎉 **All done!**\n\n"
            "Your verification is submitted.\n"
            "We'll review and notify you soon."
        )
        
        # Send to admin
        if ADMIN_ID:
            await send_to_admin(context, user_id)
        
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please send a photo")
        return PRODUCT_PHOTO

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Send to admin."""
    try:
        user = users[user_id]
        
        # Send info
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 New verification\nUser: {user['name']}\nPhone: {user['phone']}"
        )
        
        # Send photos
        await context.bot.send_photo(ADMIN_ID, user['receipt'], "📄 Receipt")
        await context.bot.send_photo(ADMIN_ID, user['id_photo'], "🆔 ID")
        await context.bot.send_photo(ADMIN_ID, user['product_photo'], "📦 Product")
        
        # Send admin commands
        await context.bot.send_message(
            ADMIN_ID,
            f"Commands:\n/approve_{user_id}\n/reject_{user_id}"
        )
        
    except Exception as e:
        logger.error(f"Admin error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command."""
    await update.message.reply_text(
        "Send /verify to start verification.\n"
        "You'll need:\n"
        "1. Phone number\n"
        "2. Receipt photo\n"
        "3. ID photo\n"
        "4. Product photo"
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel."""
    await update.message.reply_text("Cancelled. Use /verify to restart.")
    return ConversationHandler.END

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin approve."""
    if update.effective_user.id != ADMIN_ID:
        return
    
    cmd = update.message.text
    if cmd.startswith('/approve_'):
        user_id = int(cmd.split('_')[1])
        
        if user_id in users:
            # Notify user
            await context.bot.send_message(
                user_id,
                "✅ Your verification is approved!"
            )
            await update.message.reply_text(f"Approved user {user_id}")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin reject."""
    if update.effective_user.id != ADMIN_ID:
        return
    
    cmd = update.message.text
    if cmd.startswith('/reject_'):
        user_id = int(cmd.split('_')[1])
        
        if user_id in users:
            # Notify user
            await context.bot.send_message(
                user_id,
                "❌ Verification rejected. Please try again."
            )
            await update.message.reply_text(f"Rejected user {user_id}")

def main():
    """Start the bot."""
    print("🚀 Starting bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('verify', verify_command)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, phone_handler)],
            RECEIPT: [MessageHandler(filters.PHOTO, receipt_handler)],
            ID_PHOTO: [MessageHandler(filters.PHOTO, id_photo_handler)],
            PRODUCT_PHOTO: [MessageHandler(filters.PHOTO, product_photo_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Add handlers
    app.add_handler(CommandHandler('start', start_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(conv_handler)
    
    # Admin handlers
    app.add_handler(MessageHandler(
        filters.Regex(r'^/approve_\d+$'),
        admin_approve
    ))
    app.add_handler(MessageHandler(
        filters.Regex(r'^/reject_\d+$'),
        admin_reject
    ))
    
    print("✅ Bot running!")
    app.run_polling()

if __name__ == '__main__':
    main()
