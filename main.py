import requests
import os
import time
import yt_dlp
import json

TOKEN = '8049964577:AAH8gmb3Wy_IV0CZh6W8Pv3OFyclgQphgoE'
URL = f'https://api.telegram.org/bot{TOKEN}/'
last_update_id = 0

admin_id = 6071206764  # حط آيديك عشان توصلك الإشعارات

youtube_cookies = {
    "GPS": "1",
    "YSC": "fa5VWO7QqEE",
    "VISITOR_INFO1_LIVE": "CzwApWJckGY",
    "VISITOR_PRIVACY_METADATA": "CgJTQRIEGgAgbQ%3D%3D",
    "PREF": "tz=Asia.Riyadh",
    "__Secure-1PSIDTS": "sidts-CjEB5H03P-WDZPo6T1zEJH8q7Bs2bT3T6fTrJpvY8QAjs71aIaXLICCNLNfECf65aQXHEAA",
    "__Secure-3PSIDTS": "sidts-CjEB5H03P-WDZPo6T1zEJH8q7Bs2bT3T6fTrJpvY8QAjs71aIaXLICCNLNfECf65aQXHEAA",
    "HSID": "ADdwERVDL19oN3rUG",
    "SSID": "AYbzQat65RuAhaa_T",
    "APISID": "azvSH3ZPx4Vs4nqI/Ac0ZTcpThyWEgpApO",
    "SAPISID": "LKjjgN5YQkMf0IBB/AxAWa_kW65hu3sK0g",
    "__Secure-1PAPISID": "LKjjgN5YQkMf0IBB/AxAWa_kW65hu3sK0g",
    "__Secure-3PAPISID": "LKjjgN5YQkMf0IBB/AxAWa_kW65hu3sK0g",
    "SID": "g.a000ygjnVzLeOsblnU7Q4rpWoxPC3QqxilGCOfXTD-4fpnIXu3wxRmD35sandk2O89cbsDMizgACgYKAW0SARcSFQHGX2Mimo-qpB_YrscPfzDOS6nN3hoVAUF8yKo6HGFNwqHkKKNxYBLgUuH80076",
    "__Secure-1PSID": "g.a000ygjnVzLeOsblnU7Q4rpWoxPC3QqxilGCOfXTD-4fpnIXu3wxUKuWBoFHs7Pas9r2oKx_8QACgYKAdsSARcSFQHGX2MiHPzP5qCvL-3_MMTWERO3MhoVAUF8yKoeldxog2zjNELXzq9fQn9S0076",
    "__Secure-3PSID": "g.a000ygjnVzLeOsblnU7Q4rpWoxPC3QqxilGCOfXTD-4fpnIXu3wxFQknwhKTGaJxt2owOsMVuQACgYKAcwSARcSFQHGX2Mii-y5223c-XjhwYZFMajczxoVAUF8yKoSjixw-rAeX1w2nw3JTYwg0076",
    "LOGIN_INFO": "AFmmF2swRQIgZO9iVEtdIMx3hJnY_aJVU11OhSVo38stBXyoBM8zwFECIQD5FdQ67HPawBDlY6QcBrKzfW3SLl4kfv3Km8gKqgtlAw:QUQ3MjNmelJreDJ6VXZKSWxKTGc4SkdnMDdNTXhjY3VMRktDQnFjSWw1QmpnUHNPcHZTMzVQZi0yRk9kRGtWNzdKV21fc2VMM0JDTEQ3cENTb0NJbEJmbTFCYkliTHNCa0xUUzgxczVKeUR2N2t5XzVwNXZmTkpFTlNqajBDN3Q4cHl2OFhpck1id3JMeWJVZkhXNENPbTUzVUFmdmJrUlln",
    "__Secure-ROLLOUT_TOKEN": "CKe7g86_5brK7wEQmKD1p4aZjgMYy7muwIaZjgM%3D",
    "SIDCC": "AKEyXzUmUs2wTHLGG7Vh2P_s_dD7Krp4akgqpCKFGsTXP7S3zR7mupZcEftQ1n3iF9XkSK1tXA",
    "__Secure-1PSIDCC": "AKEyXzWnq0RtBAvvv0KSKLa2zMruNJ6eqX3iLGI7OdF670HHIju3U2-98G0ouVd_nXdHNHAH",
    "__Secure-3PSIDCC": "AKEyXzU5xwXia40oPGfh9HrwcWibky2sb9_eL6cV_eNB-jMsM89OobUUgQMtv9MV0X4I2lQAlQ",
}

known_users = set()
pending_downloads = {}

def get_updates():
    global last_update_id
    response = requests.get(URL + 'getUpdates', params={'offset': last_update_id + 1})
    if response.status_code == 200:
        data = response.json()
        if data['ok'] and data['result']:
            last_update_id = data['result'][-1]['update_id']
            return data['result']
    return []

def send_message(chat_id, text, reply_markup=None):
    data = {'chat_id': chat_id, 'text': text}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(URL + 'sendMessage', data=data)

def send_video(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(URL + 'sendVideo', data={'chat_id': chat_id}, files={'video': f})

def send_audio(chat_id, file_path):
    with open(file_path, 'rb') as f:
        requests.post(URL + 'sendAudio', data={'chat_id': chat_id}, files={'audio': f})

def download_media(url, media_type):
    os.makedirs("downloads", exist_ok=True)
    ydl_opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'merge_output_format': 'mp4',
    }
    if 'youtube.com' in url or 'youtu.be' in url:
        ydl_opts['cookiesfromdict'] = youtube_cookies
        if media_type == 'video':
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
        elif media_type == 'audio':
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '320',
            }]
    else:
        ydl_opts['format'] = 'best'

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info)

def main():
    print("✅ البوت شغال...")
    while True:
        updates = get_updates()
        for update in updates:
            try:
                if 'message' in update:
                    msg = update['message']
                    chat_id = msg['chat']['id']

                    if msg.get('text') == '/start':
                        user_id = chat_id
                        user_name = msg.get('from', {}).get('first_name', 'بدون اسم')
                        if user_id not in known_users:
                            known_users.add(user_id)
                            send_message(admin_id, f"🆕 دخل البوت:\n👤 الاسم: {user_name}\n🆔 ID: {user_id}\n📈 العدد الكلي: {len(known_users)}")
                        send_message(chat_id, "👋 أهلًا بك! أرسل رابط يوتيوب أو أي رابط تحميل.")
                        continue

                    text = msg.get('text', '')
                    if 'youtube.com' in text or 'youtu.be' in text:
                        pending_downloads[chat_id] = text
                        keyboard = {
                            "inline_keyboard": [
                                [{"text": "🎬 تحميل فيديو", "callback_data": "yt_video"}],
                                [{"text": "🎵 تحميل صوت", "callback_data": "yt_audio"}]
                            ]
                        }
                        send_message(chat_id, "اختر نوع التحميل:", reply_markup=json.dumps(keyboard))
                    else:
                        send_message(chat_id, "⏳ جاري التحميل...")
                        file_path = download_media(text, 'video')
                        send_video(chat_id, file_path)
                        os.remove(file_path)

                elif 'callback_query' in update:
                    query = update['callback_query']
                    chat_id = query['message']['chat']['id']
                    data = query['data']
                    url = pending_downloads.get(chat_id)
                    if not url:
                        send_message(chat_id, "❌ لم أجد الرابط.")
                        continue

                    send_message(chat_id, "🚀")
                    if data == 'yt_video':
                        file_path = download_media(url, 'video')
                        send_video(chat_id, file_path)
                    elif data == 'yt_audio':
                        file_path = download_media(url, 'audio')
                        send_audio(chat_id, file_path)
                    os.remove(file_path)
                    pending_downloads.pop(chat_id, None)

            except Exception as e:
                send_message(chat_id, f"❌ خطأ: {str(e)}")
        time.sleep(2)

if __name__ == '__main__':
    main()
