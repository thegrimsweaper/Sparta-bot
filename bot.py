import os
import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# ========== CONFIGURATION ==========
# Get credentials from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')

# Validate bot token
if not BOT_TOKEN:
    print("=" * 60)
    print("❌ ERROR: BOT_TOKEN environment variable is not set!")
    print("=" * 60)
    print("To fix this:")
    print("1. Go to Render dashboard → Sparta-bot")
    print("2. Click 'Environment' tab")
    print("3. Add: BOT_TOKEN=8542276438:AAR4o-QIUsZCubaeT6dyNun9T6BV1P0qeQ")
    print("4. Add: ADMIN_ID=1117780787")
    print("5. Save and redeploy")
    print("=" * 60)
    exit(1)

# Convert ADMIN_ID to integer if set
if ADMIN_ID:
    ADMIN_ID = int(ADMIN_ID)
else:
    ADMIN_ID = None
    print("⚠️ WARNING: ADMIN_ID not set. Admin features disabled.")

print("=" * 60)
print("🚀 PRODUCT VERIFICATION BOT STARTING")
print(f"✅ Bot Token: {'Set' if BOT_TOKEN else 'Missing'}")
print(f"✅ Admin ID: {ADMIN_ID if ADMIN_ID else 'Not set'}")
print("=" * 60)
# ===================================

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
PHONE, RECEIPT, ID_PHOTO, PRODUCT_PHOTO = range(4)

# Simple database (in production, use real database)
users_db = {}

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "👋 **Welcome to Product Verification Bot!**\n\n"
        "I'll help verify your product purchase in 4 simple steps:\n\n"
        "1. 📱 **Phone Number** - Share your contact\n"
        "2. 📄 **Purchase Proof** - Send receipt/invoice photo\n"
        "3. 🆔 **Identity** - Send ID photo\n"
        "4. 📦 **Product** - Send product photo\n\n"
        "Send /verify to begin verification!"
    )

async def verify_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the verification process."""
    user_id = update.effective_user.id
    
    # Check if user already has pending verification
    if user_id in users_db and users_db[user_id].get('status') == 'pending':
        await update.message.reply_text(
            "⏳ You already have a pending verification.\n"
            "We'll notify you when it's reviewed."
        )
        return ConversationHandler.END
    
    # Initialize user data
    users_db[user_id] = {
        'name': update.effective_user.full_name,
        'username': update.effective_user.username,
        'user_id': user_id,
        'status': 'in_progress'
    }
    
    await update.message.reply_text(
        "📱 **Step 1 of 4: Phone Verification**\n\n"
        "Please share your phone number using the button below:",
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
    
    # Verify it's the user's own phone
    if contact.user_id != user_id:
        await update.message.reply_text(
            "Please share your own phone number.",
            reply_markup=ReplyKeyboardMarkup(
                [[KeyboardButton("📱 Share Phone Number", request_contact=True)]],
                resize_keyboard=True
            )
        )
        return PHONE
    
    # Store phone number
    users_db[user_id]['phone'] = contact.phone_number
    users_db[user_id]['phone_verified'] = True
    
    await update.message.reply_text(
        f"✅ **Phone Verified:** {contact.phone_number}\n\n"
        "📄 **Step 2 of 4: Purchase Proof**\n\n"
        "Please send a clear photo of your:\n"
        "• Purchase receipt\n"
        "• Invoice\n"
        "• Order confirmation\n"
        "• Payment proof",
        reply_markup=ReplyKeyboardRemove()
    )
    return RECEIPT

async def receipt_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle receipt photo upload."""
    if not update.message.photo:
        await update.message.reply_text(
            "📸 Please send a photo of your purchase receipt."
        )
        return RECEIPT
    
    user_id = update.effective_user.id
    # Get the highest resolution photo
    photo_id = update.message.photo[-1].file_id
    users_db[user_id]['receipt_photo'] = photo_id
    
    await update.message.reply_text(
        "✅ **Receipt Received!**\n\n"
        "🆔 **Step 3 of 4: Identity Verification**\n\n"
        "Please send a clear photo of your ID:\n"
        "• Passport\n"
        "• Driver's License\n"
        "• National ID\n\n"
        "Make sure:\n"
        "• Photo is clear\n"
        "• All details readable\n"
        "• No glare/reflections"
    )
    return ID_PHOTO

async def id_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle ID photo upload."""
    if not update.message.photo:
        await update.message.reply_text(
            "📸 Please send a photo of your ID."
        )
        return ID_PHOTO
    
    user_id = update.effective_user.id
    photo_id = update.message.photo[-1].file_id
    users_db[user_id]['id_photo'] = photo_id
    
    await update.message.reply_text(
        "✅ **ID Photo Received!**\n\n"
        "📦 **Step 4 of 4: Product Verification**\n\n"
        "Please send a photo of the actual product:\n"
        "• Show the product clearly\n"
        "• Good lighting\n"
        "• Multiple angles (you can send multiple photos)\n"
        "• Show any serial numbers or labels"
    )
    return PRODUCT_PHOTO

async def product_photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle product photo upload and complete verification."""
    if not update.message.photo:
        await update.message.reply_text(
            "📸 Please send a photo of your product."
        )
        return PRODUCT_PHOTO
    
    user_id = update.effective_user.id
    photo_id = update.message.photo[-1].file_id
    users_db[user_id]['product_photo'] = photo_id
    users_db[user_id]['status'] = 'pending'
    
    # Send confirmation to user
    await update.message.reply_text(
        "🎉 **VERIFICATION COMPLETE!** 🎉\n\n"
        "✅ **Summary:**\n"
        f"• 📱 Phone: {users_db[user_id]['phone']}\n"
        f"• 👤 Name: {users_db[user_id]['name']}\n"
        f"• 📄 Receipt: ✅ Received\n"
        f"• 🆔 ID: ✅ Received\n"
        f"• 📦 Product: ✅ Received\n\n"
        "Your verification has been submitted for review.\n"
        "We'll notify you within 24 hours.\n\n"
        "Thank you for your purchase! 🙏"
    )
    
    # Send to admin (you)
    await send_to_admin(context, user_id)
    
    return ConversationHandler.END

async def send_to_admin(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Send verification request to admin."""
    if not ADMIN_ID:
        return  # Admin features disabled
    
    user = users_db[user_id]
    
    try:
        # Create admin message
        admin_message = (
            f"🆕 **NEW VERIFICATION REQUEST**\n\n"
            f"👤 **Customer:** {user['name']}\n"
            f"📱 **Phone:** {user['phone']}\n"
            f"👤 **Username:** @{user['username']}\n"
            f"🆔 **User ID:** `{user_id}`\n\n"
            f"**Status:** Pending review"
        )
        
        # Send text info to admin
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=admin_message,
            parse_mode='Markdown'
        )
        
        # Send receipt photo
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['receipt_photo'],
            caption="📄 **Purchase Receipt/Invoice**"
        )
        
        # Send ID photo
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['id_photo'],
            caption="🆔 **ID Photo**"
        )
        
        # Send product photo
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=user['product_photo'],
            caption="📦 **Product Photo**"
        )
        
        # Send admin actions
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"**Admin Actions:**\n\n"
                f"✅ Approve this user:\n"
                f"`/approve_{user_id}`\n\n"
                f"❌ Reject this user:\n"
                f"`/reject_{user_id}`\n\n"
                f"Or reply to this message for manual review."
            ),
            parse_mode='Markdown'
        )
        
        logger.info(f"Verification sent to admin for user {user_id}")
        
    except Exception as e:
        logger.error(f"Error sending to admin: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    await update.message.reply_text(
        "📋 **Product Verification Bot Help**\n\n"
        "**Commands:**\n"
        "• `/start` - Welcome message\n"
        "• `/verify` - Start verification process\n"
        "• `/help` - Show this help message\n"
        "• `/status` - Check your verification status\n\n"
        "**Verification Requirements:**\n"
        "1. Phone number (shared via button)\n"
        "2. Purchase receipt/invoice photo\n"
        "3. Government ID photo\n"
        "4. Actual product photo\n\n"
        "**Privacy:** Your data is secure and used only for verification."
    )

async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    user_id = update.effective_user.id
    
    if user_id not in users_db:
        await update.message.reply_text(
            "You haven't started verification yet.\n"
            "Use `/verify` to begin."
        )
        return
    
    status = users_db[user_id].get('status', 'not_started')
    
    if status == 'pending':
        await update.message.reply_text(
            "⏳ **Status: Pending Review**\n\n"
            "Your verification is under review.\n"
            "Average processing time: 24 hours."
        )
    elif status == 'approved':
        await update.message.reply_text(
            "✅ **Status: Approved**\n\n"
            "Your product verification has been approved!\n"
            "Thank you for your purchase!"
        )
    elif status == 'rejected':
        await update.message.reply_text(
            "❌ **Status: Rejected**\n\n"
            "Your verification was rejected.\n"
            "Please try again with `/verify`"
        )
    else:
        await update.message.reply_text(
            "🔄 **Status: In Progress**\n\n"
            "Complete your verification with `/verify`"
        )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the conversation."""
    await update.message.reply_text(
        "Verification cancelled. Use `/verify` to start again.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

# ========== ADMIN COMMANDS ==========
async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Approve a user's verification."""
    # Check if sender is admin
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return
    
    command = update.message.text
    if command.startswith('/approve_'):
        try:
            user_id = int(command.split('_')[1])
            
            if user_id in users_db:
                # Update status
                users_db[user_id]['status'] = 'approved'
                
                # Notify user
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🎉 **VERIFICATION APPROVED!** 🎉\n\n"
                        "Your product verification has been approved!\n\n"
                        "✅ You now have access to:\n"
                        "• Customer support\n"
                        "• Product warranty\n"
                        "• Updates and news\n"
                        "• Exclusive content\n\n"
                        "Thank you for your purchase!"
                    )
                )
                
                # Confirm to admin
                user_name = users_db[user_id]['name']
                user_phone = users_db[user_id]['phone']
                await update.message.reply_text(
                    f"✅ **User Approved!**\n\n"
                    f"👤 Customer: {user_name}\n"
                    f"📱 Phone: {user_phone}\n"
                    f"🆔 User ID: {user_id}"
                )
                
                logger.info(f"Admin approved user {user_id}")
            else:
                await update.message.reply_text("❌ User not found.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use: `/approve_USER_ID`")
        except Exception as e:
            logger.error(f"Error in admin_approve: {e}")
            await update.message.reply_text("❌ Error processing approval.")

async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin: Reject a user's verification."""
    if not ADMIN_ID or update.effective_user.id != ADMIN_ID:
        return
    
    command = update.message.text
    if command.startswith('/reject_'):
        try:
            user_id = int(command.split('_')[1])
            
            if user_id in users_db:
                # Update status
                users_db[user_id]['status'] = 'rejected'
                
                # Notify user
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "❌ **Verification Rejected**\n\n"
                        "Your verification request was rejected.\n\n"
                        "**Possible reasons:**\n"
                        "• Unclear photos\n"
                        "• Invalid receipt\n"
                        "• ID doesn't match\n"
                        "• Wrong product shown\n\n"
                        "Please try again with `/verify`"
                    )
                )
                
                await update.message.reply_text(f"❌ User {user_id} rejected.")
                logger.info(f"Admin rejected user {user_id}")
            else:
                await update.message.reply_text("❌ User not found.")
                
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use: `/reject_USER_ID`")
# ===================================

def main():
    """Start the bot."""
    print("=" * 60)
    print("🚀 PRODUCT VERIFICATION BOT INITIALIZING...")
    print("=" * 60)
    
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
    
    # Add user command handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('status', status_command))
    application.add_handler(conv_handler)
    
    # Add admin command handlers
    application.add_handler(MessageHandler(
        filters.Regex(r'^/approve_\d+$'),
        admin_approve
    ))
    application.add_handler(MessageHandler(
        filters.Regex(r'^/reject_\d+$'),
        admin_reject
    ))
    
    print("✅ All handlers registered successfully")
    print("🤖 Starting bot polling...")
    print("=" * 60)
    
    # Start the bot
    application.run_polling()

# ========== ENTRY POINT ==========
if __name__ == '__main__':
    main()
# =================================        reply_markup=ReplyKeyboardMarkup(
            # This is likely what you need around line 473:
keyboard = [
    [KeyboardButton("Share Phone", request_contact=True)],  # Line 473
]
reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
    main()    cmd = update.message.text
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
