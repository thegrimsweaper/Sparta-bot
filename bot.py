# ========== CONFIGURATION ==========
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# Validate
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set in environment variables")
    print("Add in Render → Environment: BOT_TOKEN=your_token")
    exit(1)

if not ADMIN_ID:
    print("⚠️ WARNING: ADMIN_ID not set. Admin features disabled.")
    ADMIN_ID = None
else:
    ADMIN_ID = int(ADMIN_ID)
# ===================================        "To verify your purchase, I'll need:\n"
        "1. 📱 Your phone number\n"
        "2. 📄 Purchase receipt photo\n"
        "3. 🆔 ID photo\n"
        "4. 📦 Product photo\n\n"
        "Send /verify to begin!"
    )

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the verification process."""
    await update.message.reply_text(
        "📱 **Step 1/4: Phone Verification**\n\n"
        "Please share your phone number:",
        reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("📱 Share Phone Number", request_contact=True)]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )
    return PHONE

async def phone_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle phone number submission."""
    contact = update.message.contact
    user_id = update.effective_user.id
    
    # Store user data
    user_data[user_id] = {
        'phone': contact.phone_number,
        'name': update.effective_user.full_name,
        'username': update.effective_user.username,
        'user_id': user_id
    }
    
    await update.message.reply_text(
        f"✅ Phone verified: {contact.phone_number}\n\n"
        "📄 **Step 2/4: Purchase Receipt**\n"
        "Please send a photo of your purchase receipt or invoice:",
        reply_markup=ReplyKeyboardRemove()
    )
    return RECEIPT

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt photo."""
    if not update.message.photo:
        await update.message.reply_text("Please send a photo of your receipt.")
        return RECEIPT
    
    user_id = update.effective_user.id
    user_data[user_id]['receipt_photo'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        "✅ Receipt received!\n\n"
        "🆔 **Step 3/4: ID Verification**\n"
        "Please send a photo of your ID (Passport/Driver's License/National ID):"
    )
    return ID_PHOTO

async def id_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ID photo."""
    if not update.message.photo:
        await update.message.reply_text("Please send a photo of your ID.")
        return ID_PHOTO
    
    user_id = update.effective_user.id
    user_data[user_id]['id_photo'] = update.message.photo[-1].file_id
    
    await update.message.reply_text(
        "✅ ID photo received!\n\n"
        "📦 **Step 4/4: Product Photo**\n"
        "Please send a photo of your actual product:"
    )
    return PRODUCT_PHOTO

async def product_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle product photo and complete verification."""
    if not update.message.photo:
        await update.message.reply_text("Please send a photo of your product.")
        return PRODUCT_PHOTO
    
    user_id = update.effective_user.id
    user_data[user_id]['product_photo'] = update.message.photo[-1].file_id
    user_data[user_id]['status'] = 'pending'
    
    # Send confirmation to user
    await update.message.reply_text(
        "🎉 **Verification Complete!**\n\n"
        "Your submission has been received.\n"
        "We'll review and notify you within 24 hours.\n\n"
        "Thank you for your purchase!"
    )
    
    # Send to admin (you)
    await send_to_admin(context, user_id)
    
    return ConversationHandler.END

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Send verification request to admin."""
    user = user_data[user_id]
    
    try:
        # Send user info
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🆕 **NEW VERIFICATION REQUEST**\n\n"
                 f"👤 Customer: {user['name']}\n"
                 f"📱 Phone: {user['phone']}\n"
                 f"👤 Username: @{user['username']}\n"
                 f"🆔 User ID: `{user_id}`\n"
                 f"📅 Submitted: Just now"
        )
        
        # Send photos
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['receipt_photo'],
            caption="📄 Purchase Receipt"
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['id_photo'],
            caption="🆔 ID Photo"
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['product_photo'],
            caption="📦 Product Photo"
        )
        
        # Send admin commands
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"**Admin Actions:**\n"
                 f"Approve: `/approve_{user_id}`\n"
                 f"Reject: `/reject_{user_id}`"
        )
        
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "📋 **Help - Product Verification Bot**\n\n"
        "**Commands:**\n"
        "/start - Welcome message\n"
        "/verify - Start verification process\n"
        "/help - Show this message\n\n"
        "**Process:**\n"
        "1. Share phone number\n"
        "2. Send purchase receipt photo\n"
        "3. Send ID photo\n"
        "4. Send product photo\n\n"
        "Your data is secure and used only for verification."
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Verification cancelled. Use /verify to start again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def main():
    """Start the bot."""
    # Check if token is set
    if BOT_TOKEN == '8542276438:AAER4o-QIUsZCubaeT6dyNun9T6BVlPOqeQ':
        print("❌ ERROR: Please set BOT_TOKEN")
        print("1. Add in Render → Environment tab")
        print("2. Or update in bot.py file")
        return
    
    print("🚀 Starting Product Verification Bot...")
    
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup conversation handler
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
    
    # Add all handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(conv_handler)
    
    # Start the bot
    print("🤖 Bot is running and ready!")
    application.run_polling()

if __name__ == '__main__':
    main()    
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
