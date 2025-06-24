
import logging
from aiogram import Bot, Dispatcher, types, executor
import yt_dlp
import os

API_TOKEN = 'YOUR_BOT_TOKEN'
ADMIN_ID = 6071206764

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

USERS_FILE = "users.txt"

def download_video(url):
    ydl_opts = {
        'outtmpl': 'video.%(ext)s',
        'format': 'best',
        'quiet': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def save_user(user: types.User):
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            f.write("")
    with open(USERS_FILE, "r+") as f:
        users = f.read().splitlines()
        if str(user.id) not in users:
            f.write(f"{user.id}
")

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    save_user(message.from_user)
    await message.reply("أرسل الرابط فقط لتحميل المقطع 🚀")

@dp.message_handler(commands=['معلوماتي'])
async def my_info(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    with open(USERS_FILE, "r") as f:
        users = f.read().splitlines()
    await message.reply(f"عدد المستخدمين: {len(users)}")

@dp.message_handler()
async def handle_url(message: types.Message):
    url = message.text.strip()
    await message.reply("🚀")
    try:
        file_path = download_video(url)
        await bot.send_video(message.chat.id, open(file_path, "rb"))
        os.remove(file_path)
    except Exception as e:
        await message.reply("حدث خطأ أثناء التحميل.")

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
