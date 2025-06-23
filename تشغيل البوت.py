import requests
import os
import time
import yt_dlp

TOKEN = '8049964577:AAH8gmb3Wy_IV0CZh6W8Pv3OFyclgQphgoE'
URL = f'https://api.telegram.org/bot{TOKEN}/'
last_update_id = 0

admin_id = 6071206764  # حط آيديك هنا عشان تستقبل إشعارات

# ✅ تم تحديث الكوكيز هنا
insta_cookies = {
    "datr": "_Lo4aPVIhr8NrUn4xrtejdVg",
    "ig_did": "C03A340B-7F8A-41B4-A9A3-8B8EEDE332C7",
    "mid": "aDi6_AABAAFdw8uX1mZaUFHqy2sO",
    "ds_user_id": "74983369637",
    "dpr": "2.8125",
    "ps_l": "1",
    "ps_n": "1",
    "wd": "384x702",
    "csrftoken": "v8g7v8WAvkUGKP71vGHbdJS8mYvaPjZF",
    "sessionid": "74983369637%3ASj67m5omVuy3yX%3A6%3AAYdbev8jV-xGINHX0aRLHiHSVGjcukQxXbBue31aQw",
    "rur": "CLN,74983369637,1781762900:01fe2e43ab05a33a421a4ce53b755e17bc4ec43c777635bf5b6fb0100c33e3a8b6a0343c",
}

known_users = set()

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

def download_media(url):
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

                # تحقق من الأمر /start
                if msg.get('text') == '/start':
                    user_id = chat_id
                    user_name = msg.get('from', {}).get('first_name', 'بدون اسم')
                    if user_id not in known_users:
                        known_users.add(user_id)
                        send_message(admin_id, f"🆕 دخل البوت:\n👤 الاسم: {user_name}\n🆔 ID: {user_id}\n📈 العدد الكلي: {len(known_users)}")
                    send_message(chat_id, "أهلًا في البوت! أرسل رابط لتحميل الفيديو.")
                    continue

                # التعامل مع أي رسالة نصية أخرى كـ رابط تحميل
                if 'text' in msg:
                    send_message(chat_id, "⏳ جاري التحميل...")
                    file_path = download_media(msg['text'])
                    send_file(chat_id, file_path)
                    os.remove(file_path)

            except Exception as e:
                send_message(chat_id, f"❌ خطأ: {str(e)}")
        time.sleep(2)

if __name__ == '__main__':
    main()