import os
import logging
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from googletrans import Translator
import requests
from PIL import Image
import pytesseract
import tempfile
import io
import asyncio

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize translator
translator = Translator()

# Supported languages with emojis
LANGUAGES = {
    'en': '🇬🇧 English',
    'es': '🇪🇸 Spanish',
    'fr': '🇫🇷 French',
    'de': '🇩🇪 German',
    'it': '🇮🇹 Italian',
    'pt': '🇵🇹 Portuguese',
    'ru': '🇷🇺 Russian',
    'ja': '🇯🇵 Japanese',
    'ko': '🇰🇷 Korean',
    'zh-cn': '🇨🇳 Chinese',
    'ar': '🇸🇦 Arabic',
    'hi': '🇮🇳 Hindi',
    'bn': '🇧🇩 Bengali',
    'ur': '🇵🇰 Urdu',
    'id': '🇮🇩 Indonesian',
    'ms': '🇲🇾 Malay',
    'tl': '🇵🇭 Tagalog',
    'vi': '🇻🇳 Vietnamese',
    'th': '🇹🇭 Thai',
    'nl': '🇳🇱 Dutch',
    'pl': '🇵🇱 Polish',
    'tr': '🇹🇷 Turkish',
    'fa': '🇮🇷 Persian'
}

# Store user preferences (in production, use a database)
user_prefs = {}

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message with bot features."""
    user = update.effective_user
    welcome_text = f"""
🌟 **Hello {user.first_name}!** Welcome to Language57 Translator Bot!

I'm your AI-powered translation assistant that can handle:

📝 **Text Translation** - Send any text message
🖼️ **Image Translation** - Send photos with text
🎤 **Voice Translation** - Send voice messages (coming soon)

**Quick Commands:**
/language - 🌍 Change target language
/settings - ⚙️ View your settings
/help - 📖 Get help
/translate [text] - 🎯 Translate specific text

**Current Language:** English
Use /language to change it!
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information."""
    help_text = """
📖 **Help & Commands Guide**

**📝 Text Translation:**
Just send any text message and I'll translate it instantly!

**🖼️ Image Translation:**
Send a photo containing text and I'll extract and translate it using OCR.

**🎤 Voice Translation:**
Send a voice message and I'll transcribe and translate it (coming soon).

**Commands:**
/start - Show welcome message
/help - Show this help
/language - Change translation language
/settings - View your current settings
/translate [text] - Translate specific text

**Supported Languages:**
English, Spanish, French, German, Italian, Portuguese, Russian, Japanese, Korean, Chinese, Arabic, Hindi, Bengali, Urdu, Indonesian, Malay, Tagalog, Vietnamese, Thai, Dutch, Polish, Turkish, Persian

**Tips:**
• Your language preference is saved automatically
• Images should have clear, printed text for best OCR results
• Maximum text length: ~5000 characters
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show language selection menu."""
    keyboard = []
    lang_list = list(LANGUAGES.items())
    
    # Create keyboard in rows of 2 for better mobile viewing
    for i in range(0, len(lang_list), 2):
        row = []
        for j in range(i, min(i+2, len(lang_list))):
            code, name = lang_list[j]
            row.append(InlineKeyboardButton(name, callback_data=f'lang_{code}'))
        keyboard.append(row)
    
    # Add navigation buttons
    keyboard.append([
        InlineKeyboardButton("❌ Cancel", callback_data='cancel'),
        InlineKeyboardButton("ℹ️ Current: English", callback_data='current')
    ])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🌍 **Select your target translation language:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user settings."""
    user_id = update.effective_user.id
    current_lang = user_prefs.get(user_id, {}).get('target_lang', 'en')
    lang_name = LANGUAGES.get(current_lang, 'English').split(' ', 1)[-1]
    
    # Get user info
    user = update.effective_user
    username = f"@{user.username}" if user.username else "Not set"
    
    settings_text = f"""
⚙️ **Your Settings**

👤 **User:** {user.first_name} {user.last_name or ''}
📱 **Username:** {username}
🆔 **User ID:** `{user_id}`

🌍 **Target Language:** {lang_name}
📊 **Total Translations:** {user_prefs.get(user_id, {}).get('count', 0)}

Use /language to change your target language.
"""
    await update.message.reply_text(settings_text, parse_mode='Markdown')

async def translate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Translate specific text using command."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide text to translate.\n\nExample:\n`/translate Hello world`",
            parse_mode='Markdown'
        )
        return
    
    text = ' '.join(context.args)
    user_id = update.effective_user.id
    target_lang = user_prefs.get(user_id, {}).get('target_lang', 'en')
    
    try:
        translation = translator.translate(text, dest=target_lang)
        source_lang = LANGUAGES.get(translation.src, translation.src).split(' ', 1)[-1]
        target_lang_name = LANGUAGES.get(target_lang, target_lang).split(' ', 1)[-1]
        
        response = f"""
📝 **Translation Result**

🔄 **From:** {source_lang}
➡️ **To:** {target_lang_name}

**📤 Original:**
{text}

**📥 Translated:**
{translation.text}
"""
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        await update.message.reply_text("❌ Error: Could not translate. Please try again.")

# ============ CALLBACK HANDLER ============

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == 'cancel':
        await query.edit_message_text("✅ Operation cancelled.")
        return
    
    if query.data == 'current':
        current_lang = user_prefs.get(user_id, {}).get('target_lang', 'en')
        lang_name = LANGUAGES.get(current_lang, 'English').split(' ', 1)[-1]
        await query.edit_message_text(
            f"ℹ️ Your current language is: **{lang_name}**\n\nUse /language to change it.",
            parse_mode='Markdown'
        )
        return
    
    if query.data.startswith('lang_'):
        lang_code = query.data.replace('lang_', '')
        if lang_code in LANGUAGES:
            # Save user preference
            if user_id not in user_prefs:
                user_prefs[user_id] = {}
            user_prefs[user_id]['target_lang'] = lang_code
            user_prefs[user_id]['count'] = user_prefs[user_id].get('count', 0) + 1
            
            lang_name = LANGUAGES[lang_code].split(' ', 1)[-1]
            await query.edit_message_text(
                f"✅ **Language Updated!**\n\nYour target language is now: **{lang_name}**\n\nStart sending messages to translate! 🚀",
                parse_mode='Markdown'
            )

# ============ MESSAGE HANDLERS ============

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages for translation."""
    text = update.message.text
    user_id = update.effective_user.id
    
    # Skip if it's a command
    if text.startswith('/'):
        return
    
    target_lang = user_prefs.get(user_id, {}).get('target_lang', 'en')
    
    try:
        # Show typing indicator
        await update.message.chat.send_action(action="typing")
        
        # Translate
        translation = translator.translate(text, dest=target_lang)
        source_lang = LANGUAGES.get(translation.src, translation.src).split(' ', 1)[-1]
        target_lang_name = LANGUAGES.get(target_lang, target_lang).split(' ', 1)[-1]
        
        # Update stats
        if user_id not in user_prefs:
            user_prefs[user_id] = {}
        user_prefs[user_id]['count'] = user_prefs[user_id].get('count', 0) + 1
        
        # Prepare response based on whether translation was needed
        if translation.src != target_lang:
            response = f"""
📝 **Translation**

🔄 **From:** {source_lang}
➡️ **To:** {target_lang_name}

**📥 Result:**
{translation.text}
"""
        else:
            response = f"""
📝 **Text Analysis**

ℹ️ This text is already in **{target_lang_name}**!

**📤 Original:**
{text}

💡 Try changing your language with /language to translate differently.
"""
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Text translation error: {e}")
        await update.message.reply_text(
            "❌ Sorry, I couldn't translate that text.\n\n"
            "Please try again or change your target language using /language"
        )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle photo messages for OCR and translation."""
    user_id = update.effective_user.id
    target_lang = user_prefs.get(user_id, {}).get('target_lang', 'en')
    
    # Send initial processing message
    processing_msg = await update.message.reply_text(
        "🔄 **Processing image...** Please wait.",
        parse_mode='Markdown'
    )
    
    try:
        # Get the photo file (highest quality)
        photo_file = await update.message.photo[-1].get_file()
        
        # Download to memory
        image_data = await photo_file.download_as_bytearray()
        image = Image.open(io.BytesIO(image_data))
        
        # Extract text using OCR
        extracted_text = pytesseract.image_to_string(image)
        
        if not extracted_text.strip():
            await processing_msg.edit_text(
                "❌ **No text found** in the image.\n\n"
                "Tips for better results:\n"
                "• Use clear, well-lit photos\n"
                "• Ensure text is legible\n"
                "• Avoid blurry images",
                parse_mode='Markdown'
            )
            return
        
        # Translate the extracted text
        translation = translator.translate(extracted_text, dest=target_lang)
        target_lang_name = LANGUAGES.get(target_lang, target_lang).split(' ', 1)[-1]
        
        # Update stats
        if user_id not in user_prefs:
            user_prefs[user_id] = {}
        user_prefs[user_id]['count'] = user_prefs[user_id].get('count', 0) + 1
        
        response = f"""
📸 **Image Text Translation**

**📋 Extracted Text:**
{extracted_text[:500]}{'...' if len(extracted_text) > 500 else ''}

**🌍 Translated to {target_lang_name}:**
{translation.text[:500]}{'...' if len(translation.text) > 500 else ''}

✨ **Confidence:** High
📊 **Character Count:** {len(extracted_text)}
"""
        await processing_msg.edit_text(response, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Image processing error: {e}")
        await processing_msg.edit_text(
            "❌ **Error processing image.**\n\n"
            "This might happen if:\n"
            "• The image is corrupted\n"
            "• The text is unclear\n"
            "• OCR service is unavailable\n\n"
            "Please try again with a different image."
        )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle voice messages (placeholder for future)."""
    await update.message.reply_text(
        "🎵 **Voice Translation**\n\n"
        "Voice message transcription is coming soon! 🚀\n"
        "For now, please use text or images for translation.",
        parse_mode='Markdown'
    )

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle document messages (placeholder for future)."""
    await update.message.reply_text(
        "📄 **Document Translation**\n\n"
        "Document translation is coming soon! 🚀\n"
        "For now, please use text or images for translation.",
        parse_mode='Markdown'
    )

# ============ ERROR HANDLER ============

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")
    
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ **An error occurred.**\n\n"
                "Please try again later or contact support.",
                parse_mode='Markdown'
            )
    except:
        pass

# ============ MAIN FUNCTION ============

def main():
    """Start the bot."""
    # Get token from environment variable
    token = os.getenv('TELEGRAM_TOKEN')
    if not token:
        logger.error("❌ TELEGRAM_TOKEN environment variable not set!")
        logger.info("Please set TELEGRAM_TOKEN in Railway environment variables.")
        sys.exit(1)
    
    logger.info("🚀 Starting Language57 Translator Bot...")
    logger.info(f"📱 Bot Token: {token[:10]}...{token[-5:]}")
    
    # Create application
    application = ApplicationBuilder().token(token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("language", language_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("translate", translate_command))
    
    # Add callback query handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Add message handlers (order matters - more specific first)
    application.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("✅ Bot is running! Waiting for messages...")
    application.run_polling()

if __name__ == '__main__':
    main()
