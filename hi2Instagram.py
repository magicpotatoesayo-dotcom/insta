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
import logging
from flask import Flask, request, jsonify

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Install dependencies if needed
def install_dependencies():
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
        subprocess.check_call([sys.executable, "-m", "pip", "install", "cfonts==1.5.2"])
        from cfonts import render

# Install dependencies
try:
    install_dependencies()
except Exception as e:
    logger.warning(f"Some dependencies failed: {e}")

# Create Flask app for web service
app = Flask(__name__)

# Colors and formatting - Simplified version that won't break
class Colors:
    ED = '\033[38;5;208m'
    BLUE = '\033[94m'
    Z = '\033[1;31m'
    YELLOW = '\033[1;33m'
    O = '\033[2;31m'
    F = '\033[2;32m'
    A = '\033[2;34m'
    C = '\033[2;35m'
    M = '\033[2;36m'
    Y = '\033[1;34m'
    B = "\033[1;30m"
    R = "\033[1;31m"
    G = "\033[1;32m"
    W = "\033[1;37m"
    J = '\033[2;36m'
    N = '\033[1;37m'

# Global variables
used_usernames = set()
lock = Lock()
hit = 0
badig = 0
badmil = 0
dead = 0
is_running = False

def banner():
    try:
        from cfonts import render
        output = render('Insta Checker', colors=['red', 'yellow'], align='center')
        print(output)
        print("=" * 50)
        print("DEV / @sm4ss")
        print("=" * 50)
    except:
        print("Insta Checker")
        print("=" * 50)
        print("DEV / @sm4ss")
        print("=" * 50)

# Get token from environment variable
TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')

if not TOKEN or not CHAT_ID:
    logger.warning("BOT_TOKEN or CHAT_ID not set. Some features will be disabled.")

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
By || @sm4ss
'''
    try:
        with open('hits.txt', 'a') as ff:
            ff.write(f'{msg}\n')
        if TOKEN and CHAT_ID:
            requests.get(f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}", timeout=5)
    except Exception as e:
        logger.error(f"Error sending message: {e}")

def solve_recaptcha():
    try:
        anchor_url = "https://www.google.com/recaptcha/api2/anchor?ar=1&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=ar&v=TnA7HacJFoBWt9hnlunBlYfK&size=invisible&anchor-ms=20000&execute-ms=30000&cb=x552vg5lfo2g"
        params = anchor_url.split('?')[1]
        
        headers = {
            'authority': 'www.google.com',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
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
        
        resp = requests.post('https://www.google.com/recaptcha/api2/reload', data=payload, headers=reload_headers, timeout=10)
        if 'resp","' in resp.text:
            return resp.text.split('resp","')[1].split('"')[0]
        return None
    except Exception as e:
        logger.error(f"Recaptcha error: {e}")
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
        response = requests.post("https://hi2.in/api/custom", data=data, headers=headers, timeout=30)
        res = response.json()
        if "already taken" in str(res) or res.get('status') == 'error':
            badmil += 1
        else:
            info(user)    	
    except Exception as e:
        logger.error(f"Check email error: {e}")
        badmil += 1

def rest(email):
    global bad_user, hit, badig, badmil, dead
    try:
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
        
        # Use httpx with http2 support
        try:
            import httpx
            with httpx.Client(http2=True, timeout=30.0) as client:
                response = client.post(url, data=payload, headers=headers)
                
                if 'email_is_taken' in response.text:
                    check_email(email)
                else:
                    badig += 1
        except Exception as e:
            # Fallback to requests if httpx fails
            logger.warning(f"HTTPX failed, falling back to requests: {e}")
            response = requests.post(url, data=payload, headers=headers, timeout=30)
            if 'email_is_taken' in response.text:
                check_email(email)
            else:
                badig += 1
                
    except Exception as e:
        logger.error(f"Rest error: {e}")
        dead += 1

def users():    
    while is_running:
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
        
        # Add small delay to avoid rate limiting
        time.sleep(0.5)

@app.route('/')
def home():
    return jsonify({
        "status": "running" if is_running else "stopped",
        "hits": hit,
        "bad_ig": badig,
        "bad_mail": badmil,
        "dead": dead,
        "total_checked": hit + badig + badmil + dead,
        "is_running": is_running,
        "bot_configured": bool(TOKEN and CHAT_ID)
    })

@app.route('/start')
def start():
    global is_running
    if not is_running:
        is_running = True
        # Start threads
        for _ in range(5):  # Reduced threads for Render free tier
            Thread(target=users, daemon=True).start()
        return jsonify({"status": "started", "message": "Checker started successfully"})
    return jsonify({"status": "already running", "message": "Checker is already running"})

@app.route('/stop')
def stop():
    global is_running
    if is_running:
        is_running = False
        return jsonify({"status": "stopped", "message": "Checker stopped"})
    return jsonify({"status": "not running", "message": "Checker is not running"})

@app.route('/stats')
def stats():
    return jsonify({
        "hits": hit,
        "bad_ig": badig,
        "bad_mail": badmil,
        "dead": dead,
        "total_checked": hit + badig + badmil + dead,
        "percentage_hit": f"{(hit / (hit + badig + badmil + dead) * 100):.2f}%" if (hit + badig + badmil + dead) > 0 else "0%"
    })

@app.route('/status')
def status():
    return jsonify({
        "service": "Instagram Email Checker",
        "version": "1.0.0",
        "status": "online",
        "bot_token": "configured" if TOKEN else "not configured",
        "chat_id": "configured" if CHAT_ID else "not configured",
        "threads": 5,
        "is_running": is_running
    })

if __name__ == "__main__":
    banner()
    
    # Try to get token from environment variables
    if TOKEN and CHAT_ID:
        logger.info(f"Bot configured with token: {TOKEN[:10]}...")
    else:
        logger.warning("Bot token or chat ID not configured. Running with limited functionality.")
    
    # Auto-start on Render
    if os.environ.get('RENDER'):
        logger.info("Running on Render - Auto-starting checker...")
        is_running = True
        for _ in range(5):
            Thread(target=users, daemon=True).start()
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
