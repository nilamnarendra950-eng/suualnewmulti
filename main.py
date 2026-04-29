from flask import Flask, render_template, request, jsonify
from instagrapi import Client
from instagrapi.exceptions import LoginRequired
import threading
import time
import random
import os
import json
import psutil
import logging
from datetime import datetime
import pytz

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[
        logging.FileHandler("main.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = "sujal_hawk_sessionid_2026"

IST = pytz.timezone('Asia/Kolkata')

state = {"running": False, "sent": 0, "logs": [], "start_time": None}
cfg = {
    "sessionids": [],           # ← Changed to sessionids
    "thread_id": 0,
    "messages": [],
    "name_bases": [],
    "message_delay": 50,
    "name_change_delay": 6,
    "switch_delay": 4,
    "cycle_break": 420
}

DEVICES = [
    {"phone_manufacturer": "Google", "phone_model": "Pixel 8 Pro", "android_version": 15, "android_release": "15.0.0", "app_version": "323.0.0.46.109"},
    {"phone_manufacturer": "Samsung", "phone_model": "SM-S928B", "android_version": 15, "android_release": "15.0.0", "app_version": "324.0.0.41.110"},
    {"phone_manufacturer": "OnePlus", "phone_model": "PJZ110", "android_version": 15, "android_release": "15.0.0", "app_version": "322.0.0.40.108"},
    {"phone_manufacturer": "Xiaomi", "phone_model": "23127PN0CC", "android_version": 15, "android_release": "15.0.0", "app_version": "325.0.0.42.111"},
]

def get_system_stats():
    try:
        process = psutil.Process(os.getpid())
        mem_mb = process.memory_info().rss / 1024 / 1024
        cpu = psutil.cpu_percent(interval=0.05)
        return f"RAM: {mem_mb:.1f} MB / 512 MB | CPU: {cpu:.1f}%"
    except:
        return "RAM: N/A | CPU: N/A"

def log(msg):
    stats = get_system_stats()
    now_ist = datetime.now(IST).strftime("%H:%M:%S")
    full_msg = f"[{now_ist}] {stats} | {msg}"
    state["logs"].append(full_msg)
    if len(state["logs"]) > 500:
        state["logs"] = state["logs"][-500:]
    logger.info(full_msg)

def get_client(sessionid):
    session_file = f"session_{sessionid[:10]}.json"   # Short name for file
    cl = Client()
    cl.delay_range = [15, 40]
    device = random.choice(DEVICES)
    cl.set_device(device)
    cl.set_user_agent(f"Instagram {device['app_version']} Android (34/15; 480dpi; 1080x2400; {device['phone_manufacturer']}; {device['phone_model']}; en_IN)")

    if os.path.exists(session_file):
        try:
            cl.load_settings(session_file)
            cl.get_timeline_feed()
            log(f"✅ Session loaded")
            return cl
        except:
            pass

    try:
        cl.login_by_sessionid(sessionid)
        cl.dump_settings(session_file)
        log(f"✅ LOGIN SUCCESS (Session ID)")
        return cl
    except Exception as e:
        log(f"❌ LOGIN FAILED | {str(e)[:60]}")
        return None

def change_name(cl, thread_id, new_name):
    # Hybrid Method
    try:
        cl.direct_thread_update_title(thread_id, new_name)
        return True
    except:
        pass

    for _ in range(3):
        try:
            csrf = cl.private.cookies.get("csrftoken", "")
            cl.private.headers.update({"X-CSRFToken": csrf})
            payload = {"doc_id": "29088580780787855", "variables": json.dumps({"thread_fbid": str(thread_id), "new_title": new_name})}
            r = cl.private.post("https://www.instagram.com/api/graphql/", data=payload, timeout=15)
            if r.status_code == 200:
                return True
        except:
            pass
        time.sleep(8)
    return False

def health_check():
    while True:
        if state["running"]:
            log("💓 HEARTBEAT — Script alive")
        time.sleep(1800)

def bomber():
    clients = {}
    for idx, sid in enumerate(cfg["sessionids"]):
        cl = get_client(sid)
        if cl:
            clients[idx] = cl

    if not clients:
        log("❌ NO WORKING ACCOUNTS!")
        return

    threading.Thread(target=health_check, daemon=True).start()

    SYMBOLS = ["♡", "𝜗ৎ", "𑣲", ".✦ ݁˖", "𐙚", "✶⋆.˚", "ᝰ.ᐟ", "ᥬᩤ", "⋆", "<𝟑 .ᐟ"]
    EMOJIS = ["🔥", "💀", "😈", "🚀", "👑", "💣", "⚡", "🌪️", "🎯", "💥", "🖤", "⚔️", "🌹", "☠️", "🌟", "🔱", "🕷️", "🦅", "⚰️", "🌑"]

    acc_list = list(clients.keys())
    acc_index = 0
    name_index = 0
    message_count = 0

    while state["running"]:
        cl = clients[acc_list[acc_index]]

        try:
            msg = random.choice(cfg["messages"])
            cl.direct_send(msg, thread_ids=[cfg["thread_id"]])
            state["sent"] += 1
            message_count += 1
            log(f"SENT #{state['sent']} (Acc #{acc_index+1})")

            time.sleep(cfg["message_delay"])

            if message_count % 10 == 0 and cfg["name_bases"]:
                base = cfg["name_bases"][name_index % len(cfg["name_bases"])]
                symbol = random.choice(SYMBOLS)
                emoji = random.choice(EMOJIS)
                now_ist = datetime.now(IST).strftime("%I:%M %p")
                new_name = f"{base} {symbol} {emoji} • {now_ist}"
                if change_name(cl, cfg["thread_id"], new_name):
                    log(f"NAME CHANGED (Hybrid) → {new_name}")
                name_index += 1
                time.sleep(cfg["name_change_delay"])

            acc_index = (acc_index + 1) % len(acc_list)
            time.sleep(cfg["switch_delay"])

        except LoginRequired:
            log(f"🔐 Session expired → Relogging...")
            new_cl = get_client(cfg["sessionids"][acc_index])
            if new_cl:
                clients[acc_list[acc_index]] = new_cl
            time.sleep(30)
        except Exception as e:
            log(f"ERROR → {str(e)[:60]}")
            time.sleep(15)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    global state
    state["running"] = False
    time.sleep(1)
    state = {"running": True, "sent": 0, "logs": ["SESSION ID + HYBRID STARTED"], "start_time": time.time()}

    raw_ids = request.form["sessionids"].strip().split("\n")
    cfg["sessionids"] = [s.strip() for s in raw_ids if s.strip()][:5]   # Max 5 accounts

    cfg["thread_id"] = int(request.form["thread_id"])
    cfg["messages"] = [m.strip() for m in request.form["messages"].split("\n") if m.strip()]
    raw_names = request.form.get("name_bases", "").strip().split("\n")
    cfg["name_bases"] = [n.strip() for n in raw_names if n.strip()][:10]
    cfg["message_delay"] = float(request.form.get("message_delay", "50"))
    cfg["name_change_delay"] = float(request.form.get("name_change_delay", "6"))
    cfg["switch_delay"] = float(request.form.get("switch_delay", "4"))
    cfg["cycle_break"] = int(request.form.get("cycle_break", "420"))

    threading.Thread(target=bomber, daemon=True).start()
    return jsonify({"ok": True})

@app.route("/stop")
def stop():
    state["running"] = False
    log("STOPPED BY USER")
    return jsonify({"ok": True})

@app.route("/status")
def status():
    uptime = "00:00:00"
    if state.get("start_time"):
        t = int(time.time() - state["start_time"])
        h, r = divmod(t, 3600)
        m, s = divmod(r, 60)
        uptime = f"{h:02d}:{m:02d}:{s:02d}"
    return jsonify({
        "running": state["running"],
        "sent": state["sent"],
        "uptime": uptime,
        "logs": state["logs"][-100:]
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
