import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token (get from @BotFather)
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"  # Replace with your token
ADMIN_ID = YOUR_ADMIN_ID_HERE  # Replace with your chat ID

# Simple user storage
users_db = {}

async def start(update: Update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"Welcome {user.first_name}!\n\n"
        "To verify your purchase, we need:\n"
        "1. Your phone number\n"
        "2. Purchase receipt photo\n"
        "3. ID photo\n"
        "4. Product photo\n\n"
        "Start by sharing your phone:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Phone", request_contact=True)]],
            resize_keyboard=True
        )
    )
    return "PHONE"

async def phone_handler(update: Update, context):
    contact = update.message.contact
    user_id = update.effective_user.id
    
    # Store user data
    users_db[user_id] = {
        'phone': contact.phone_number,
        'name': update.effective_user.full_name,
        'step': 'RECEIPT'
    }
    
    await update.message.reply_text(
        f"✅ Phone saved: {contact.phone_number}\n\n"
        "Now send photo of your receipt or invoice:",
        reply_markup=ReplyKeyboardRemove()
    )
    return "RECEIPT"

async def receipt_handler(update: Update, context):
    user_id = update.effective_user.id
    
    if update.message.photo:
        users_db[user_id]['receipt'] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ Receipt received!\n\nNow send photo of your ID:")
        return "ID"
    else:
        await update.message.reply_text("Please send a photo of your receipt")
        return "RECEIPT"

async def id_handler(update: Update, context):
    user_id = update.effective_user.id
    
    if update.message.photo:
        users_db[user_id]['id_photo'] = update.message.photo[-1].file_id
        await update.message.reply_text("✅ ID received!\n\nNow send photo of the product:")
        return "PRODUCT"
    else:
        await update.message.reply_text("Please send a photo of your ID")
        return "ID"

async def product_handler(update: Update, context):
    user_id = update.effective_user.id
    
    if update.message.photo:
        users_db[user_id]['product_photo'] = update.message.photo[-1].file_id
        users_db[user_id]['verified'] = False
        
        # Send to admin (you)
        await update.get_bot().send_message(
            chat_id=ADMIN_ID,
            text=f"📦 NEW VERIFICATION REQUEST\n\n"
                 f"User: {users_db[user_id]['name']}\n"
                 f"Phone: {users_db[user_id]['phone']}\n"
                 f"ID: @{update.effective_user.username}"
        )
        
        # Send photos to admin
        await update.get_bot().send_photo(
            chat_id=ADMIN_ID,
            photo=users_db[user_id]['receipt'],
            caption="📄 Receipt"
        )
        
        await update.get_bot().send_photo(
            chat_id=ADMIN_ID,
            photo=users_db[user_id]['id_photo'],
            caption="🆔 ID Photo"
        )
        
        await update.get_bot().send_photo(
            chat_id=ADMIN_ID,
            photo=users_db[user_id]['product_photo'],
            caption="📦 Product Photo"
        )
        
        await update.message.reply_text(
            "✅ All done! Your verification is sent for review.\n"
            "We'll notify you when approved."
        )
        
        return ConversationHandler.END
    else:
        await update.message.reply_text("Please send a photo of your product")
        return "PRODUCT"

async def approve(update: Update, context):
    if update.effective_user.id == ADMIN_ID:
        if context.args:
            user_id = int(context.args[0])
            if user_id in users_db:
                users_db[user_id]['verified'] = True
                await update.get_bot().send_message(
                    chat_id=user_id,
                    text="🎉 Your verification is APPROVED!"
                )
                await update.message.reply_text(f"✅ User {user_id} approved!")
            else:
                await update.message.reply_text("User not found")
        else:
            await update.message.reply_text("Usage: /approve USER_ID")

async def main():
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            "PHONE": [MessageHandler(filters.CONTACT, phone_handler)],
            "RECEIPT": [MessageHandler(filters.PHOTO, receipt_handler)],
            "ID": [MessageHandler(filters.PHOTO, id_handler)],
            "PRODUCT": [MessageHandler(filters.PHOTO, product_handler)],
        },
        fallbacks=[]
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("approve", approve))
    
    # Start the bot
    await app.initialize()
    await app.start()
    print("Bot is running...")
    
    # Keep running
    await app.updater.start_polling()
    
    # Run forever
    await asyncio.Event().wait()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
