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
BOT_TOKEN = os.getenv("BOT_TOKEN")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYP_
