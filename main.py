import os
import random
import requests
from requests.adapters import HTTPAdapter, Retry
from concurrent.futures import ThreadPoolExecutor

# قراءة المتغيرات من بيئة التشغيل
BOT_TOKEN = os.getenv('TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
SEND_URL = f'https://api.telegram.org/bot{TOKEN}/sendMessage'

COOKIES = {
    'datr': '_Lo4aPVIhr8NrUn4xrtejdVg',
    'ig_did': 'C03A340B-7F8A-41B4-A9A3-8B8EEDE332C7',
    'mid': 'aDi6_AABAAFdw8uX1mZaUFHqy2sO',
    'ds_user_id': '74983369637',
    'dpr': '2.8125',
    'ps_l': '1',
    'ps_n': '1',
    'csrftoken': 'v8g7v8WAvkUGKP71vGHbdJS8mYvaPjZF',
    'sessionid': '74983369637%3ASj67m5omVuy3yX%3A6%3AAYdbev8jV-xGINHX0aRLHiHSVGjcukQxXbBue31aQw',
    'wd': '384x716',
    'rur': '"CLN\\05474983369637\\0541782392488:01fe0246e54e0435f92b61d6824b0d0a1bcb00018bd1439676fb17e021c82"'
}

session = requests.Session()
retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500,502,503,504])
session.mount('https://', HTTPAdapter(max_retries=retries))
session.cookies.update(COOKIES)
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
})

def generate_user():
    chars = "abcdefghijklmnopqrstuvwxyz0123456789"
    under_index = random.randint(0, 3)
    return ''.join('_' if i == under_index else random.choice(chars) for i in range(4))

def check_username(user):
    url = f"https://www.instagram.com/{user}/"
    try:
        r = session.get(url, timeout=4)
        if r.status_code == 404:
            print(f"[✅] @{user}")
            session.post(SEND_URL, data={"chat_id": CHAT_ID, "text": f"🔥 متاح: @{user}"})
            with open("available.txt", "a") as f:
                f.write(user + "\n")
        else:
            print(f"[❌] {user}")
    except:
        pass

def main():
    print("🚀 بدء الفحص السريع بخيوط متعددة (10 خيوط)...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        while True:
            user = generate_user()
            executor.submit(check_username, user)

if __name__ == "__main__":
    main()
