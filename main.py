import os
import zipfile
from io import BytesIO
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("7868650608:AAGKQgCpc6rM-W3Fsq-WbQPvfkSx7YK-PNY")

user_configs = {}

def get_keyboard(user_id):
    cfg = user_configs.get(user_id, {})
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Contacts/VCF: {cfg.get('contacts_per_vcf', 10)}", callback_data='set_contacts')],
        [InlineKeyboardButton(f"Total VCFs: {cfg.get('total_vcfs', 1)}", callback_data='set_vcfs')],
        [InlineKeyboardButton(f"File Prefix: {cfg.get('file_prefix', 'contacts')}", callback_data='set_file_prefix')],
        [InlineKeyboardButton(f"Name Prefix: {cfg.get('contact_prefix', 'contact')}", callback_data='set_contact_prefix')],
        [InlineKeyboardButton(f"Add +: {'Yes' if cfg.get('plus_prefix', False) else 'No'}", callback_data='toggle_plus')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_configs[update.effective_user.id] = {}
    await update.message.reply_text("Configure your VCF settings:", reply_markup=get_keyboard(update.effective_user.id))

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    cfg = user_configs.setdefault(user_id, {})

    if query.data == 'toggle_plus':
        cfg['plus_prefix'] = not cfg.get('plus_prefix', False)
        await query.edit_message_text("Configure your VCF settings:", reply_markup=get_keyboard(user_id))
    else:
        context.user_data['awaiting_input'] = query.data
        await query.message.reply_text("Please send the new value (number or text).")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    awaiting = context.user_data.get('awaiting_input')
    if not awaiting:
        return

    val = update.message.text
    cfg = user_configs.setdefault(user_id, {})

    try:
        if awaiting == 'set_contacts':
            cfg['contacts_per_vcf'] = int(val)
        elif awaiting == 'set_vcfs':
            cfg['total_vcfs'] = int(val)
        elif awaiting == 'set_file_prefix':
            cfg['file_prefix'] = val.strip()
        elif awaiting == 'set_contact_prefix':
            cfg['contact_prefix'] = val.strip()
        await update.message.reply_text("Updated setting!", reply_markup=get_keyboard(user_id))
    except Exception as e:
        await update.message.reply_text(f"Invalid input: {e}")

    context.user_data['awaiting_input'] = None

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    file = update.message.document

    if not file.file_name.endswith(".txt"):
        await update.message.reply_text("Please upload a .txt file.")
        return

    cfg = user_configs.get(user_id, {
        "contacts_per_vcf": 10,
        "total_vcfs": 1,
        "file_prefix": "contacts",
        "contact_prefix": "contact",
        "plus_prefix": False
    })

    telegram_file = await file.get_file()
    file_bytes = await telegram_file.download_as_bytearray()
    numbers = file_bytes.decode('utf-8').splitlines()

    os.makedirs('output', exist_ok=True)
    created_files = []
    idx = 0

    for vcf_num in range(cfg['total_vcfs']):
        filename = f"output/{cfg['file_prefix']}_{vcf_num+1}.vcf"
        with open(filename, 'w', encoding='utf-8') as f:
            for _ in range(cfg['contacts_per_vcf']):
                if idx >= len(numbers): break
                number = numbers[idx].strip()
                if not number: continue
                if cfg['plus_prefix'] and not number.startswith('+'):
                    number = '+' + number
                f.write(f"BEGIN:VCARD\nVERSION:3.0\nFN:{cfg['contact_prefix']}_{idx+1}\nTEL:{number}\nEND:VCARD\n")
                idx += 1
        created_files.append(filename)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zipf:
        for file_path in created_files:
            zipf.write(file_path, os.path.basename(file_path))
    zip_buffer.seek(0)

    await update.message.reply_document(InputFile(zip_buffer, filename='vcfs.zip'))

    for file in created_files:
        os.remove(file)

async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    print("Bot is running...")
    await app.run_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
  
