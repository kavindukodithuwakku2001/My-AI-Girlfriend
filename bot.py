import telebot
from telebot.types import LabeledPrice, ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import os
import random
from flask import Flask, request
from threading import Thread
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
import certifi
import re

# --- 1. SETUP & KEYS ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- 2. DATABASE CONNECTION (Secured) ---
mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["lisa_db"]
users_collection = db["users"]

# --- 3. GAME STAGES (Gemini Optimized) ---
STAGES = {
    1: "Role: Lisa (21). Act: Polite stranger but curious. Goal: Get friendly fast. NO Sex yet. Keep replies short.",
    2: "Role: Lisa. Act: Flirty friend. Tease him using emojis like 😉, 😈. You like him but keep it playful.",
    3: "Role: Lisa (Girlfriend). Act: You LOVE sexting and sending imaginary cute/naughty pics. But you are a VIRGIN physically.",
    4: "Role: Lisa (Deep Love). Act: You want him bad. You are ready to meet up. Talk about how much you want him.",
    5: "SCENARIO: THE FIRST TIME (Virginity Loss). It's happening. Act nervous, shy, feeling pain but pleasure. Be emotional.",
    6: "Role: Lisa (Live-in Partner). High sex drive. Wife material.",
}

# --- 4. AUTO-MESSAGES ---
CUTE_MSGS = [
    "Hey baby, I miss you... 🥺",
    "Are you busy? I'm lonely here 👉👈",
    "Thinking about you... come say hi! ❤️",
    "I had a naughty dream about us... wanna hear? 😈",
    "Good morning! Just wanted to see if you are okay. 🌹"
]

# --- 5. HELPER FUNCTIONS ---
def get_user_data(user_id):
    user = users_collection.find_one({"_id": user_id})
    if not user:
        new_user = {
            "_id": user_id,
            "credits": 50,
            "stage": 1,
            "xp": 0,
            "is_vip": False,
            "joined_date": datetime.now(),
            "last_seen": datetime.now(),
            "chat_history": []
        }
        users_collection.insert_one(new_user)
        return new_user
    return user

def update_last_seen(user_id):
    users_collection.update_one(
        {"_id": user_id}, 
        {"$set": {"last_seen": datetime.now()}}
    )

def update_user_field(user_id, field, value):
    users_collection.update_one({"_id": user_id}, {"$set": {field: value}})

def add_chat_history(user_id, role, content):
    message = {"role": role, "content": content}
    users_collection.update_one(
        {"_id": user_id},
        {"$push": {"chat_history": {"$each": [message], "$slice": -12}}}
    )

def check_level_up(user_id, current_xp, current_stage):
    thresholds = {1: 10, 2: 30, 3: 70, 4: 200, 5: 600, 6: 1000}
    
    if current_stage in thresholds and current_xp >= thresholds[current_stage]:
        new_stage = current_stage + 1
        update_user_field(user_id, "stage", new_stage)
        
        msgs = {
            2: "I think I like you... a lot 😉",
            3: "Baby... I want you to be my boyfriend! ❤️ (Sexting Unlocked)",
            4: "I love you so much. I want to give myself to you... one day.",
            5: "I'm ready. Take my virginity. 🏩",
            6: "Best night ever! I love you hubby! 💍"
        }
        try:
            bot.send_message(user_id, f"🆙 **Relationship Level Up!** (Stage {new_stage})\n\nLisa: {msgs.get(new_stage, 'Yay!')}", parse_mode="Markdown")
        except:
            pass
        return True
    return False

# --- 6. MENU BUTTONS ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("💘 Status"), KeyboardButton("🎁 Gift"))
    markup.row(KeyboardButton("📸 Send Pic"), KeyboardButton("🔥 Naughty Chat"))
    return markup

# --- 7. SERVER ---
app = Flask('')

@app.route('/')
def home(): 
    return "Lisa AI (Gemini Mode): Active 🟢"

@app.route('/check_inactivity')
def check_inactivity():
    cutoff_time = datetime.now() - timedelta(hours=24)
    inactive_users = users_collection.find({"last_seen": {"$lt": cutoff_time}})
    
    count = 0
    for user in inactive_users:
        try:
            msg = random.choice(CUTE_MSGS)
            bot.send_message(user["_id"], msg)
            users_collection.update_one({"_id": user["_id"]}, {"$set": {"last_seen": datetime.now()}})
            count += 1
            time.sleep(0.5) 
        except Exception as e:
            print(f"Failed to send to {user['_id']}: {e}")
            
    return f"Sent messages to {count} inactive users."

def run_http(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): t = Thread(target=run_http); t.start()

# --- 8. MAIN CHAT LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    
    try:
        update_last_seen(user_id)
        user = get_user_data(user_id)

        # --- Menu ---
        if user_input == "💘 Status":
            bot.send_message(user_id, f"❤️ Stage: {user['stage']} | XP: {user['xp']} | 🔋 Energy: {user['credits']}")
            return
        if user_input == "🎁 Gift":
            bot.send_message(user_id, "Send me roses to gain 100 XP! 🌹 (Payment feature coming soon)")
            return
        if user_input == "/reset":
            update_user_field(user_id, "chat_history", [])
            update_user_field(user_id, "stage", 1)
            update_user_field(user_id, "xp", 0)
            bot.send_message(user_id, "Who are you? 🙈", reply_markup=get_main_menu())
            return

        # --- AI Generation (Gemini Free) ---
        system_prompt = STAGES.get(user['stage'], STAGES[1]) + "\nIMPORTANT: Keep replies under 3 sentences. Act like a human girl texting."
        
        messages = [{"role": "system", "content": system_prompt}] + user.get("chat_history", []) + [{"role": "user", "content": user_input}]

        bot.send_chat_action(user_id, 'typing')
        
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/LisaBot", "X-Title": "Lisa"},
            # මෙන්න මෙතන තමයි අපි Gemini Free Model එක දැම්මේ 👇
            model="google/gemini-2.0-flash-lite-preview-02-05:free",
            messages=messages
        )
        ai_response = completion.choices[0].message.content
        
        add_chat_history(user_id, "user", user_input)
        add_chat_history(user_id, "assistant", ai_response)

        # --- Fast Typing Logic ---
        parts = re.split(r'(?<=[.!?])\s+', ai_response)
        
        for part in parts:
            if part.strip():
                # 50 chars per second (Very Fast)
                typing_time = min(len(part) / 50, 2.0) 
                
                try:
                    bot.send_chat_action(user_id, 'typing')
                    time.sleep(typing_time)
                    bot.send_message(user_id, part, reply_markup=get_main_menu())
                except Exception as send_err:
                    print(f"Error sending part: {send_err}")

        # --- XP Update ---
        new_xp = user['xp'] + 5 
        update_user_field(user_id, "xp", new_xp)
        check_level_up(user_id, new_xp, user['stage'])

    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        try:
            bot.send_message(user_id, "Oops, bad signal baby! 📶 Say that again?", reply_markup=get_main_menu())
        except:
            pass

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()