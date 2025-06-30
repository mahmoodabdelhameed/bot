import requests
import os
import time
import yt_dlp
from urllib.parse import urlparse

TOKEN = '8049964577:AAH8gmb3Wy_IV0CZh6W8Pv3OFyclgQphgoE'
URL = f'https://api.telegram.org/bot{TOKEN}/'
last_update_id = 0

admin_id = 6071206764  # حط آيديك هنا عشان تستقبل إشعارات

# ✅ الكوكيز الجديدة
insta_cookies = {
    "sessionid": "74983369637%3AFEtnt5UZPJ32qt%3A16%3AAYeQsQNQjgaauoe8S1RsGRL7DZDQvWtF26Jm-IlqNw",
    "csrftoken": "uHy8eMPi6KU7ZPqdkOLATsPrMXSLdhLc",
    "mid": "Z1hZLwALAAE65bEcQNKHW6cYxDFc",
    "ig_did": "BFF7EA86-5716-4B66-85E9-E91FA6218E62",
    "ds_user_id": "74983369637",
    "datr": "bRHnZjvczma5q3KYxQNeD1Ot",
    "rur": "CLN,74983369637,1782814071:01fedaa98f24a5ebc51a32a940d2c25a11abbd016fb1a3b99eeb1cccf52d6b5cb4482abc"
}

known_users = set()

SUPPORTED_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "twitter.com",
    "facebook.com",
    "tiktok.com",
}

def get_updates():
    global last_update_id
    response = requests.get(URL + 'getUpdates', params={'offset': last_update_id + 1})
    if response.status_code == 200:
        data = response.json()
        if data['ok'] and data['result']:
            last_update_id = data['result'][-1]['update_id']
            return data['result']
    return []

def send_message(chat_id, text):
    requests.post(URL + 'sendMessage', data={'chat_id': chat_id, 'text': text})

def send_file(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(URL + 'sendDocument', data={'chat_id': chat_id}, files={'document': f})

def is_supported_url(url):
    try:
        domain = urlparse(url).netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain in SUPPORTED_DOMAINS
    except:
        return False

def download_media(url):
    if not is_supported_url(url):
        raise Exception("❌ المنصة غير مدعومة حالياً.")
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'format': 'best',
        'quiet': True,
        'cookiesfromdict': insta_cookies,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def main():
    print("✅ البوت شغال... أرسل رابط لأي فيديو")
    while True:
        updates = get_updates()
        for update in updates:
            try:
                if 'message' not in update:
                    continue
                msg = update['message']
                chat_id = msg['chat']['id']

                if msg.get('text') == '/start':
                    user_id = chat_id
                    user_name = msg.get('from', {}).get('first_name', 'بدون اسم')
                    if user_id not in known_users:
                        known_users.add(user_id)
                        send_message(admin_id, f"🆕 دخل البوت:\n👤 الاسم: {user_name}\n🆔 ID: {user_id}\n📈 العدد الكلي: {len(known_users)}")
                    send_message(chat_id, "👋 أهلًا بك في البوت!\n📥 أرسل رابط الفيديو ليتم تحميله وإرساله إليك.")
                    continue

                if 'text' in msg:
                    url = msg['text'].strip()
                    if not url.startswith("http"):
                        send_message(chat_id, "❌ الرابط غير صالح، تأكد من إرساله كاملاً.")
                        continue

                    send_message(chat_id, "⏳ جاري التحميل...")
                    try:
                        file_path = download_media(url)
                        send_file(chat_id, file_path)
                        os.remove(file_path)
                    except Exception as e:
                        send_message(chat_id, f"❌ خطأ أثناء التحميل: {str(e)}")

            except Exception as e:
                send_message(chat_id, f"❌ خطأ غير متوقع: {str(e)}")
        time.sleep(2)

if __name__ == '__main__':
    main()