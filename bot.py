import os
import json
import random
import string
from datetime import datetime
from flask import Flask, request, jsonify
import telebot
from telebot import types

# ── CONFIG ──────────────────────────────────────────────────────────────────
BOT_TOKEN     = os.environ.get('BOT_TOKEN', '8991213205:AAEcLJ60rGkcWvJH_76PcAt-rJznXQ5UHsQ')
ADMIN_ID      = int(os.environ.get('ADMIN_ID', '8323063757'))
MIN_DEPOSIT   = float(os.environ.get('MIN_DEPOSIT', '50'))
AFFILIATE_URL = 'https://broker-qx.pro/sign-up/?lid=1662537'
DB_FILE       = 'database.json'

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ── DATABASE ─────────────────────────────────────────────────────────────────
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'deposits': {}, 'codes': {}, 'users': {}}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

# ── CODE GENERATOR ────────────────────────────────────────────────────────────
def generate_code():
    chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'
    p1 = ''.join(random.choices(chars, k=4))
    p2 = ''.join(random.choices(chars, k=4))
    return f'TR-{p1}-{p2}'

# ── DEVICE ID (simple hash from telegram user id) ────────────────────────────
def get_device_token(telegram_id):
    return f'TG-{telegram_id}'

# ─────────────────────────────────────────────────────────────────────────────
# POSTBACK ENDPOINT — Quotex calls this when deposit happens
# ─────────────────────────────────────────────────────────────────────────────
@app.route('/postback', methods=['GET', 'POST'])
def postback():
    data = request.args if request.method == 'GET' else request.get_json(force=True) or request.form
    
    uid      = str(data.get('uid', '')).strip()
    ftd      = str(data.get('ftd', '')).strip().lower()
    dep      = str(data.get('dep', '')).strip().lower()
    sumdep   = float(data.get('sumdep', 0) or 0)
    status   = str(data.get('status', '')).strip().lower()

    print(f"[POSTBACK] uid={uid} ftd={ftd} dep={dep} sumdep={sumdep} status={status}")

    if not uid:
        return jsonify({'status': 'error', 'msg': 'no uid'}), 400

    # Check if deposit event
    is_deposit = (ftd == 'true' or dep == 'true' or sumdep >= MIN_DEPOSIT or status == 'dep')

    if is_deposit:
        db = load_db()
        prev = db['deposits'].get(uid, {})
        prev_total = float(prev.get('total', 0))
        new_total  = prev_total + sumdep if sumdep > 0 else prev_total + MIN_DEPOSIT

        db['deposits'][uid] = {
            'total'     : new_total,
            'ftd'       : True,
            'timestamp' : datetime.now().isoformat(),
            'verified'  : new_total >= MIN_DEPOSIT
        }
        save_db(db)
        print(f"[POSTBACK] Deposit saved: uid={uid} total={new_total}")

        # Notify admin
        try:
            bot.send_message(
                ADMIN_ID,
                f"💰 *New Deposit!*\n"
                f"UID: `{uid}`\n"
                f"Amount: ${sumdep}\n"
                f"Total: ${new_total}\n"
                f"Verified: {'✅' if new_total >= MIN_DEPOSIT else '❌'}",
                parse_mode='Markdown'
            )
        except:
            pass

    return jsonify({'status': 'ok'}), 200

# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM BOT HANDLERS
# ─────────────────────────────────────────────────────────────────────────────
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    name    = message.from_user.first_name or 'Trader'

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        '🚀 Get Access to Trading Rode Pro',
        callback_data='get_access'
    ))

    bot.send_message(
        user_id,
        f"👋 *Namaste {name}!*\n\n"
        f"Welcome to *Trading Rode Pro* 🔥\n\n"
        f"Ye professional binary trading journal hai jo tumhari trading improve karega.\n\n"
        f"*Access lene ke liye 3 simple steps hain:*\n\n"
        f"1️⃣ Neeche button dabao\n"
        f"2️⃣ Mere affiliate link se Quotex account banao\n"
        f"3️⃣ Min *$50 deposit* karo → Auto access milega! ✅",
        parse_mode='Markdown',
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda c: c.data == 'get_access')
def get_access(call):
    user_id = call.from_user.id
    markup  = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(
        '📈 Open Quotex Account (Affiliate Link)',
        url=AFFILIATE_URL
    ))
    markup.add(types.InlineKeyboardButton(
        '✅ Maine deposit kar diya — UID bhejne ke liye click karo',
        callback_data='submit_uid'
    ))

    bot.edit_message_text(
        f"*Step 1: Quotex Account Banao* 📊\n\n"
        f"➡️ Neeche button dabao aur *mere link se* Quotex pe account banao\n\n"
        f"*Step 2: Deposit Karo* 💰\n\n"
        f"Minimum *$50 deposit* karo apne naye account mein\n\n"
        f"*Step 3: UID Submit Karo* 🔑\n\n"
        f"Deposit hone ke baad apna *Quotex Trader UID* submit karo\n"
        f"Auto verify hoga aur code milega! ✅\n\n"
        f"⚠️ *Important:* Sirf mere affiliate link se banaye account pe hi kaam karega!",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown',
        reply_markup=markup
    )
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == 'submit_uid')
def submit_uid(call):
    user_id = call.from_user.id
    bot.edit_message_text(
        f"*Apna Quotex Trader UID bhejo* 🔢\n\n"
        f"Quotex account mein login karo:\n"
        f"Profile → UID copy karo (sirf numbers)\n\n"
        f"Example: `1234567`\n\n"
        f"Bas UID number type karke bhejo 👇",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='Markdown'
    )
    bot.register_next_step_handler(call.message, process_uid)
    bot.answer_callback_query(call.id)

def process_uid(message):
    user_id  = message.from_user.id
    name     = message.from_user.first_name or 'Trader'
    uid_raw  = message.text.strip() if message.text else ''
    uid      = ''.join(filter(str.isdigit, uid_raw))

    if not uid or len(uid) < 4:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton('🔄 Dobara try karo', callback_data='submit_uid'))
        bot.send_message(
            user_id,
            "❌ *Invalid UID!*\n\nSirf numbers wala UID bhejo.\nExample: `1234567`",
            parse_mode='Markdown',
            reply_markup=markup
        )
        return

    db = load_db()

    # Check if already has code
    existing = db['codes'].get(uid)
    if existing and existing.get('device_id') == get_device_token(user_id):
        bot.send_message(
            user_id,
            f"✅ *Tumhara access code:*\n\n"
            f"`{existing['code']}`\n\n"
            f"App mein ye code daalo! 🔓",
            parse_mode='Markdown'
        )
        return

    # Check deposit
    deposit_info = db['deposits'].get(uid, {})
    total_dep    = float(deposit_info.get('total', 0))
    verified     = deposit_info.get('verified', False) or total_dep >= MIN_DEPOSIT

    if verified:
        # Generate unique code
        code = generate_code()
        while code in [v.get('code') for v in db['codes'].values()]:
            code = generate_code()

        db['codes'][uid] = {
            'code'      : code,
            'device_id' : get_device_token(user_id),
            'telegram_id': user_id,
            'name'      : name,
            'created_at': datetime.now().isoformat(),
            'used'      : False
        }
        save_db(db)

        # Notify admin
        try:
            bot.send_message(
                ADMIN_ID,
                f"🎉 *New Access Granted!*\n"
                f"Name: {name}\n"
                f"Telegram ID: `{user_id}`\n"
                f"Quotex UID: `{uid}`\n"
                f"Code: `{code}`\n"
                f"Deposit: ${total_dep}",
                parse_mode='Markdown'
            )
        except:
            pass

        bot.send_message(
            user_id,
            f"🎉 *Congratulations {name}!*\n\n"
            f"Deposit verify ho gaya! ✅\n\n"
            f"*Tera Access Code:*\n\n"
            f"`{code}`\n\n"
            f"📱 *Ab kya karna hai:*\n"
            f"1. Trading Rode Pro file kholo\n"
            f"2. Ye code daalo\n"
            f"3. Enjoy karo! 🚀\n\n"
            f"⚠️ Ye code sirf is device pe kaam karega.\n"
            f"Support: @Realtradingrode",
            parse_mode='Markdown'
        )
    else:
        # Deposit nahi mila
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            '📈 Quotex pe Deposit Karo',
            url='https://qx.broker/deposit'
        ))
        markup.add(types.InlineKeyboardButton(
            '🔄 Verify Karo (deposit ke baad)',
            callback_data='submit_uid'
        ))

        bot.send_message(
            user_id,
            f"⏳ *UID: `{uid}` — Deposit Nahi Mila*\n\n"
            f"Possible reasons:\n"
            f"• Deposit abhi process ho raha hai (5-10 min wait karo)\n"
            f"• Deposit amount ${MIN_DEPOSIT} se kam hai\n"
            f"• Galat affiliate link se account banaya\n\n"
            f"*Steps:*\n"
            f"1. Mere link se account banao ✅\n"
            f"2. Min *${MIN_DEPOSIT} deposit* karo\n"
            f"3. 5-10 min baad dobara try karo\n\n"
            f"Help chahiye? @Realtradingrode pe contact karo",
            parse_mode='Markdown',
            reply_markup=markup
        )

# ── ADMIN COMMANDS ────────────────────────────────────────────────────────────
@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    total_deposits = len(db['deposits'])
    total_codes    = len(db['codes'])
    verified       = sum(1 for v in db['deposits'].values() if v.get('verified'))

    bot.send_message(
        message.from_user.id,
        f"👑 *Admin Panel — Trading Rode*\n\n"
        f"📊 Total Deposits: {total_deposits}\n"
        f"✅ Verified Users: {verified}\n"
        f"🔑 Codes Generated: {total_codes}\n\n"
        f"*Commands:*\n"
        f"/check UID — Deposit check karo\n"
        f"/grant UID — Manual access do\n"
        f"/revoke UID — Access hatao\n"
        f"/stats — Full stats",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['check'])
def check_uid(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /check UID")
        return
    uid = parts[1].strip()
    db  = load_db()
    dep = db['deposits'].get(uid, {})
    code_info = db['codes'].get(uid, {})

    bot.reply_to(
        message,
        f"*UID: {uid}*\n\n"
        f"Deposit: ${dep.get('total', 0)}\n"
        f"Verified: {'✅' if dep.get('verified') else '❌'}\n"
        f"Code: `{code_info.get('code', 'None')}`\n"
        f"Name: {code_info.get('name', 'N/A')}\n"
        f"Telegram: {code_info.get('telegram_id', 'N/A')}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['grant'])
def grant_access(message):
    if message.from_user.id != ADMIN_ID:
        return
    parts = message.text.split()
    if len(parts) < 2:
        bot.reply_to(message, "Usage: /grant UID")
        return
    uid = parts[1].strip()
    db  = load_db()

    # Mark as verified
    db['deposits'][uid] = {
        'total'    : MIN_DEPOSIT,
        'ftd'      : True,
        'verified' : True,
        'timestamp': datetime.now().isoformat(),
        'manual'   : True
    }
    save_db(db)
    bot.reply_to(message, f"✅ UID {uid} ko manually verified kar diya!\nUser ab /start karke code le sakta hai.")

@bot.message_handler(commands=['stats'])
def stats(message):
    if message.from_user.id != ADMIN_ID:
        return
    db = load_db()
    codes_list = '\n'.join([
        f"• `{uid}` → `{v['code']}` — {v.get('name','?')}"
        for uid, v in list(db['codes'].items())[-10:]
    ]) or "Koi codes nahi"

    bot.reply_to(
        message,
        f"📊 *Last 10 Codes:*\n\n{codes_list}",
        parse_mode='Markdown'
    )

# ── WEBHOOK / POLLING ─────────────────────────────────────────────────────────
@app.route('/')
def index():
    return jsonify({'status': 'Trading Rode Bot Running! 🚀'})

@app.route(f'/webhook/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data(as_text=True)
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"Webhook error: {e}")
    return jsonify({'ok': True})

@app.route('/set_webhook')
def set_webhook():
    RENDER_URL = os.environ.get('RENDER_URL', '')
    if RENDER_URL:
        bot.remove_webhook()
        result = bot.set_webhook(url=f"{RENDER_URL}/webhook/{BOT_TOKEN}")
        return jsonify({'ok': result, 'webhook': f"{RENDER_URL}/webhook/{BOT_TOKEN}"})
    return jsonify({'ok': False, 'msg': 'RENDER_URL not set'})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    RENDER_URL = os.environ.get('RENDER_URL', '')
    if RENDER_URL:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/webhook/{BOT_TOKEN}")
        print(f"Webhook set: {RENDER_URL}/webhook/{BOT_TOKEN}")
    app.run(host='0.0.0.0', port=port)
else:
    # For gunicorn - set webhook on import
    RENDER_URL = os.environ.get('RENDER_URL', '')
    if RENDER_URL:
        try:
            bot.remove_webhook()
            bot.set_webhook(url=f"{RENDER_URL}/webhook/{BOT_TOKEN}")
            print(f"Webhook set on startup: {RENDER_URL}/webhook/{BOT_TOKEN}")
        except Exception as e:
            print(f"Webhook setup error: {e}")
