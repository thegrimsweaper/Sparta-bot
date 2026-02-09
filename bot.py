import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set")
    exit(1)

if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = None
# ===================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# States
PHONE, RECEIPT, ID_PHOTO, PRODUCT_PHOTO = range(4)

# Storage
users_db = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send /verify to verify your product purchase.")

async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "📱 **Step 1/4: Phone**\nShare your phone:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Phone", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return PHONE

async def phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    contact = update.message.contact
    user_id = update.effective_user.id
    
    users_db[user_id] = {
        'phone': contact.phone_number,
        'name': update.effective_user.full_name
    }
    
    await update.message.reply_text(
        f"✅ Phone: {contact.phone_number}\n\n"
        "📄 **Step 2/4: Receipt**\nSend receipt photo:",
        reply_markup=ReplyKeyboardRemove()
    )
    return RECEIPT

async def receipt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        user_id = update.effective_user.id
        users_db[user_id]['receipt'] = update.message.photo[-1].file_id
        
        await update.message.reply_text(
            "✅ Receipt!\n\n"
            "🆔 **Step 3/4: ID**\nSend ID photo:"
        )
        return ID_PHOTO
    else:
        await update.message.reply_text("Send a photo please")
        return RECEIPT

async def id_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        user_id = update.effective_user.id
        users_db[user_id]['id'] = update.message.photo[-1].file_id
        
        await update.message.reply_text(
            "✅ ID!\n\n"
            "📦 **Step 4/4: Product**\nSend product photo:"
        )
        return PRODUCT_PHOTO
    else:
        await update.message.reply_text("Send a photo please")
        return ID_PHOTO

async def product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.photo:
        user_id = update.effective_user.id
        users_db[user_id]['product'] = update.message.photo[-1].file_id
        
        await update.message.reply_text("🎉 All submitted! Admin will review.")
        
        # Send to admin
        if ADMIN_ID:
            await send_to_admin(context, user_id)
        
        return ConversationHandler.END
    else:
        await update.message.reply_text("Send a photo please")
        return PRODUCT_PHOTO

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Send verification to admin."""
    try:
        user = users_db[user_id]
        
        # Text info
        await context.bot.send_message(
            ADMIN_ID,
            f"🆕 New verification\nUser: {user['name']}\nPhone: {user['phone']}"
        )
        
        # Photos
        await context.bot.send_photo(ADMIN_ID, user['receipt'], "📄 Receipt")
        await context.bot.send_photo(ADMIN_ID, user['id'], "🆔 ID")
        await context.bot.send_photo(ADMIN_ID, user['product'], "📦 Product")
        
        # Admin commands
        await context.bot.send_message(
            ADMIN_ID,
            f"Approve: /approve_{user_id}\nReject: /reject_{user_id}"
        )
        
    except Exception as e:
        print(f"Admin error: {e}")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Send /verify to start")

async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    
    cmd = update.message.text
    if cmd.startswith('/approve_'):
        try:
            user_id = int(cmd.split('_')[1])
            if user_id in users_db:
                await context.bot.send_message(user_id, "✅ Approved!")
                await update.message.reply_text(f"Approved {user_id}")
        except:
            pass

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if ADMIN_ID and update.effective_user.id != ADMIN_ID:
        return
    
    cmd = update.message.text
    if cmd.startswith('/reject_'):
        try:
            user_id = int(cmd.split('_')[1])
            if user_id in users_db:
                await context.bot.send_message(user_id, "❌ Rejected")
                await update.message.reply_text(f"Rejected {user_id}")
        except:
            pass

def main():
    print("🚀 Starting bot...")
    
    # Create Application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
    conv = ConversationHandler(
        entry_points=[CommandHandler('verify', verify)],
        states={
            PHONE: [MessageHandler(filters.CONTACT, phone)],
            RECEIPT: [MessageHandler(filters.PHOTO, receipt)],
            ID_PHOTO: [MessageHandler(filters.PHOTO, id_photo)],
            PRODUCT_PHOTO: [MessageHandler(filters.PHOTO, product_photo)],
        },
        fallbacks=[]
    )
    
    # Add handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('help', help_cmd))
    app.add_handler(conv)
    
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
