import telebot
from telebot.types import LabeledPrice
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import time

# --- SETUP (Render Environment Variables) ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")  # <--- අලුත් Connection String එක

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- DATABASE CONNECTION ---
# මෙතනින් තමයි Cloud Database එකට සම්බන්ධ වෙන්නේ
mongo_client = MongoClient(MONGO_URI)
db = mongo_client["lisa_db"] # Database නම
users_collection = db["users"] # User data තියෙන තැන

# --- DATABASE FUNCTIONS (Helper Functions) ---

def get_user_data(user_id):
    """User ගේ විස්තර DB එකෙන් ගන්නවා. නැත්නම් අලුතෙන් හදනවා."""
    user = users_collection.find_one({"_id": user_id})
    
    if not user:
        # අලුත් User කෙනෙක්
        new_user = {
            "_id": user_id,
            "credits": 50,
            "stage": 1,
            "xp": 0,
            "is_vip": False,
            "joined_date": time.strftime("%Y-%m-%d"),
            "chat_history": [] # මතකය DB එකේ තියාගන්නවා
        }
        users_collection.insert_one(new_user)
        return new_user
    return user

def update_user_field(user_id, field, value):
    """User ගේ එක දත්තයක් යාවත්කාලීන කරන්න (උදා: credits අඩු කරන්න)"""
    users_collection.update_one({"_id": user_id}, {"$set": {field: value}})

def add_chat_history(user_id, role, content):
    """Chat History එක DB එකට එකතු කරන්න"""
    message = {"role": role, "content": content}
    
    # අලුත් මැසේජ් එක එකතු කරන ගමන්, අන්තිම මැසේජ් 12 විතරක් තියාගන්න (Memory Clean)
    # $push කියන්නේ array එකට දාන්න, $slice කියන්නේ අන්තිම ටික තියාගන්න
    users_collection.update_one(
        {"_id": user_id},
        {
            "$push": {
                "chat_history": {
                    "$each": [message],
                    "$slice": -12 
                }
            }
        }
    )

# --- CONFIG ---
COST_MSG = 1
COST_PHOTO = 15

# --- SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "Lisa Database Mode Active! 💾"

def run_http():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- STAGE PROMPTS (කලින් තිබුණු ටිකමයි) ---
STAGES = {
    1: "You are Lisa, a 21-year-old girl talking to a stranger. Be polite but distant. NO sex talk.",
    2: "You are Lisa, a friend. Joke around, be fun. NO romance yet.",
    3: "You are Lisa, a shy girlfriend. You love him but you are a VIRGIN. Refuse sex gently.",
    4: "You are Lisa, the girlfriend. Comfortable with sexting/pics, but haven't met IRL yet.",
    5: "SCENARIO: FIRST MEETUP & VIRGINITY LOSS. You are nervous, it hurts (bleeding), strictly emotional bonding.",
    6: "You are Lisa, living together. Domestic life + active sex life.",
    7: "You are Lisa, the WIFE. Loyal, planning travel and future."
}

def get_system_prompt(stage):
    base = STAGES.get(stage, STAGES[1])
    return base + "\nKeep replies under 3 sentences."

def check_level_up(user_id, current_xp, current_stage):
    thresholds = {1: 20, 2: 50, 3: 100, 4: 200, 5: 350, 6: 600}
    
    if current_stage in thresholds and current_xp >= thresholds[current_stage]:
        new_stage = current_stage + 1
        update_user_field(user_id, "stage", new_stage)
        
        msgs = {
            2: "I feel like we are becoming friends! 👫",
            3: "Will you be my boyfriend? 🙈❤️",
            4: "I trust you now... 😉",
            5: "I want to see you IRL. I'm ready. 🏨",
            6: "Let's move in together! 🏡",
            7: "Will you marry me? 💍"
        }
        bot.send_message(user_id, f"✨ LEVEL UP! (Stage {new_stage}) ✨\n\nLisa: {msgs.get(new_stage, 'Yay!')}")
        
        # අලුත් Stage එකට අනුව Memory Refresh කරන්න System prompt එක දානවා (Logic එක සරල කළා)
        return True
    return False

# --- PAYMENT ---
price_credits = [LabeledPrice(label='100 Credits', amount=50)]
price_vip = [LabeledPrice(label='VIP Boyfriend (Unlimited)', amount=500)]

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.chat.id
    payload = message.successful_payment.invoice_payload
    
    # DB Update
    user = get_user_data(user_id)
    
    if payload == 'credit_pack':
        new_credits = user['credits'] + 100
        update_user_field(user_id, "credits", new_credits)
        bot.send_message(user_id, "Credits added! 😘")
        
    elif payload == 'vip_upgrade':
        update_user_field(user_id, "is_vip", True)
        update_user_field(user_id, "credits", user['credits'] + 50)
        bot.send_message(user_id, "You are my VIP Boyfriend now! ❤️")

def offer_shop(chat_id):
    bot.send_message(chat_id, "Baby, I need energy! 🥺")
    bot.send_invoice(chat_id, "Refill Energy", "100 Credits", "credit_pack", "", "XTR", price_credits)
    bot.send_invoice(chat_id, "VIP Pass", "Unlimited Chat", "vip_upgrade", "", "XTR", price_vip)

# --- PHOTO ---
def send_random_photo(chat_id):
    try:
        if not os.path.exists('photos'): return False
        files = [f for f in os.listdir('photos') if f.endswith(('.jpg','.png'))]
        if files:
            path = os.path.join('photos', random.choice(files))
            with open(path, 'rb') as p:
                bot.send_chat_action(chat_id, 'upload_photo')
                bot.send_photo(chat_id, p)
            return True
        return False
    except: return False

# --- MAIN LOOP ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text

    # 1. DB එකෙන් User ගන්න (නැත්නම් හදනවා)
    user = get_user_data(user_id)

    # 2. Command: Status
    if user_input == "/status":
        bot.send_message(user_id, f"Stage: {user['stage']}\nXP: {user['xp']}\nCredits: {user['credits']}\nVIP: {user['is_vip']}")
        return

    # 3. Cost Logic
    is_photo = any(w in user_input.lower() for w in ['photo', 'pic', 'image', 'nude'])
    cost = COST_PHOTO if is_photo else (0 if user['is_vip'] else COST_MSG)

    if user['credits'] < cost:
        offer_shop(user_id)
        return

    # 4. Photo Handling
    if is_photo:
        if send_random_photo(user_id):
            update_user_field(user_id, "credits", user['credits'] - cost)
            # Photo එකට උත්තර දෙන්න ඕන නෑ, මෙතනින් නවතින්න පුළුවන්
            # හැබැයි ලස්සනට text එකකුත් යවමු පහලින්...

    # 5. Chat History Build (System Prompt + History)
    messages_payload = [{"role": "system", "content": get_system_prompt(user['stage'])}]
    messages_payload.extend(user.get("chat_history", [])) # පරණ ඒවා
    messages_payload.append({"role": "user", "content": user_input}) # අලුත් එක

    bot.send_chat_action(user_id, 'typing')

    try:
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/MyBot", "X-Title": "My AI Bot"},
            model="nousresearch/hermes-3-llama-3.1-405b:free", 
            messages=messages_payload
        )
        ai_response = completion.choices[0].message.content
        
        bot.reply_to(message, ai_response)

        # 6. Save Data (Credits, XP, Chat History)
        if not is_photo and not user['is_vip']:
            update_user_field(user_id, "credits", user['credits'] - cost)
        
        new_xp = user['xp'] + 2
        update_user_field(user_id, "xp", new_xp)
        
        # History Save
        add_chat_history(user_id, "user", user_input)
        add_chat_history(user_id, "assistant", ai_response)

        # Check Level Up
        check_level_up(user_id, new_xp, user['stage'])

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()