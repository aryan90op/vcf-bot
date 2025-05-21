import os
import zipfile
import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from io import BytesIO

user_settings = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_settings[update.effective_chat.id] = {
        'contacts_per_vcf': 100,
        'total_vcfs': 1,
        'file_prefix': 'contacts',
        'contact_prefix': 'Contact',
        'add_plus': False
    }
    keyboard = [
        [InlineKeyboardButton("Set Contacts per VCF", callback_data='set_contacts')],
        [InlineKeyboardButton("Set Total VCFs", callback_data='set_total')],
        [InlineKeyboardButton("Set File Prefix", callback_data='set_file_prefix')],
        [InlineKeyboardButton("Set Contact Prefix", callback_data='set_contact_prefix')],
        [InlineKeyboardButton("Toggle '+' Before Numbers", callback_data='toggle_plus')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Send a .txt file of numbers and configure below:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id
    data = query.data
    context.user_data['setting'] = data

    if data == 'toggle_plus':
        user_settings[chat_id]['add_plus'] = not user_settings[chat_id]['add_plus']
        await query.edit_message_text(f"Add '+' before numbers: {user_settings[chat_id]['add_plus']}")
    else:
        await query.edit_message_text("Send the new value now...")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    setting = context.user_data.get('setting')
    value = update.message.text.strip()
    chat_id = update.effective_chat.id

    if setting == 'set_contacts':
        user_settings[chat_id]['contacts_per_vcf'] = int(value)
        await update.message.reply_text("Updated contacts per VCF.")
    elif setting == 'set_total':
        user_settings[chat_id]['total_vcfs'] = int(value)
        await update.message.reply_text("Updated total VCFs.")
    elif setting == 'set_file_prefix':
        user_settings[chat_id]['file_prefix'] = value
        await update.message.reply_text("Updated file prefix.")
    elif setting == 'set_contact_prefix':
        user_settings[chat_id]['contact_prefix'] = value
        await update.message.reply_text("Updated contact prefix.")
    context.user_data['setting'] = None

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if not document.file_name.endswith('.txt'):
        await update.message.reply_text("Only .txt files are supported.")
        return

    chat_id = update.effective_chat.id
    settings = user_settings.get(chat_id)
    if not settings:
        await update.message.reply_text("Please start with /start.")
        return

    file = await context.bot.get_file(document.file_id)
    data = await file.download_as_bytearray()
    numbers = data.decode('utf-8').splitlines()
    numbers = [n.strip() for n in numbers if n.strip()]

    per_vcf = settings['contacts_per_vcf']
    total = settings['total_vcfs']
    file_prefix = settings['file_prefix']
    contact_prefix = settings['contact_prefix']
    add_plus = settings['add_plus']

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for i in range(total):
            start = i * per_vcf
            end = start + per_vcf
            chunk = numbers[start:end]
            if not chunk:
                break
            vcf_data = ""
            for idx, number in enumerate(chunk):
                if add_plus and not number.startswith('+'):
                    number = '+' + number
                vcf_data += f"BEGIN:VCARD\nVERSION:3.0\nFN:{contact_prefix} {idx + 1}\nTEL:{number}\nEND:VCARD\n"
            filename = f"{file_prefix}_{i + 1}.vcf"
            zipf.writestr(filename, vcf_data)

    zip_buffer.seek(0)
    await update.message.reply_document(document=zip_buffer, filename="vcf_files.zip")

async def main():
    token = os.getenv("BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    print("Bot is running...")
    await app.run_polling()

# Fix for Railway’s already running event loop
import asyncio
try:
    asyncio.get_event_loop().run_until_complete(main())
except RuntimeError:
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())
      
