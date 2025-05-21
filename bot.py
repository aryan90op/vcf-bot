import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters
)
from collections import defaultdict

# Get bot token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is missing!")

# === User settings store ===
user_settings = defaultdict(lambda: {
    "file_prefix": "Contacts",
    "contact_prefix": "Person",
    "contacts_per_file": 50
})

# === VCF Generator Function ===
def txt_to_vcf_from_lines(lines, file_prefix, contact_prefix, contacts_per_file):
    os.makedirs("vcf_output", exist_ok=True)
    numbers = [line.strip() for line in lines if line.strip()]
    files = []
    total = len(numbers)
    file_count = 1
    contact_count = 1

    for i in range(0, total, contacts_per_file):
        chunk = numbers[i:i+contacts_per_file]
        filename = f"{file_prefix}_{file_count}.vcf"
        file_path = os.path.join("vcf_output", filename)
        with open(file_path, 'w', encoding='utf-8') as vcf:
            for number in chunk:
                number = number if number.startswith('+') else f"+{number}"
                name = f"{contact_prefix}_{contact_count}"
                vcf.write(f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL;TYPE=CELL:{number}\nEND:VCARD\n")
                contact_count += 1
        files.append(file_path)
        file_count += 1

    return files

# === Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Send me a .txt file of phone numbers (one per line).\n"
        "Use /setcount 50 to set contacts per file\n"
        "Use /setfileprefix GroupName to set the VCF file prefix\n"
        "Use /setcontactprefix Friend to set contact name prefix"
    )

async def set_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        count = int(context.args[0])
        if count < 1:
            raise ValueError
        user_settings[user_id]["contacts_per_file"] = count
        await update.message.reply_text(f"Set contacts per VCF file to {count}.")
    except:
        await update.message.reply_text("Usage: /setcount 50")

async def set_file_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefix = ' '.join(context.args).strip()
    if prefix:
        user_settings[user_id]["file_prefix"] = prefix
        await update.message.reply_text(f"Set VCF file prefix to: {prefix}")
    else:
        await update.message.reply_text("Usage: /setfileprefix Friends")

async def set_contact_prefix(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    prefix = ' '.join(context.args).strip()
    if prefix:
        user_settings[user_id]["contact_prefix"] = prefix
        await update.message.reply_text(f"Set contact name prefix to: {prefix}")
    else:
        await update.message.reply_text("Usage: /setcontactprefix Buddy")

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = user_settings[user_id]

    doc = update.message.document
    if doc.mime_type != "text/plain":
        await update.message.reply_text("Please upload a valid .txt file.")
        return

    file = await doc.get_file()
    file_content = await file.download_as_bytes()
    lines = file_content.decode("utf-8").splitlines()

    vcf_files = txt_to_vcf_from_lines(
        lines,
        file_prefix=settings["file_prefix"],
        contact_prefix=settings["contact_prefix"],
        contacts_per_file=settings["contacts_per_file"]
    )

    for path in vcf_files:
        with open(path, 'rb') as f:
            await update.message.reply_document(document=f)
        await asyncio.sleep(0.5)  # avoid flood limits
        os.remove(path)  # delete file after sending

# === Main ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setcount", set_count))
    app.add_handler(CommandHandler("setfileprefix", set_file_prefix))
    app.add_handler(CommandHandler("setcontactprefix", set_contact_prefix))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))

    app.run_polling()

if __name__ == "__main__":
    main()
