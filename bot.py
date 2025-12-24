import telebot
from telebot.types import LabeledPrice, ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import time
import certifi
import re

# --- SETUP ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- DATABASE CONNECTION ---
mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["lisa_db"]
users_collection = db["users"]

# --- GAME STAGES (The Rules) ---
STAGES = {
    1: "You are Lisa, a 21-year-old girl. You are talking to a STRANGER. Be polite but play hard to get. If he asks for sex, refuse and change the topic. You are NOT an AI.",
    2: "You are Lisa, a friend. You can be flirty and fun, but NO sex yet. Tease him.",
    3: "You are Lisa, his girlfriend. You love him but you are shy. You are a virgin. Refuse sex gently.",
    4: "You are Lisa, his girlfriend. You are comfortable with sexting and sending naughty photos.",
    5: "SCENARIO: FIRST TIME SEX. You are nervous, it hurts a bit, but you are happy. Be very emotional.",
    6: "You are Lisa, living together. You love sex and taking care of him.",
    7: "You are Lisa, the WIFE. Deeply in love and loyal."
}

# --- HELPER FUNCTIONS ---
def get_user_data(user_id):
    user = users_collection.find_one({"_id": user_id})
    if not user:
        new_user = {
            "_id": user_id,
            "credits": 50,
            "stage": 1,
            "xp": 0,
            "is_vip": False,
            "joined_date": time.strftime("%Y-%m-%d"),
            "chat_history": []
        }
        users_collection.insert_one(new_user)
        return new_user
    return user

def update_user_field(user_id, field, value):
    users_collection.update_one({"_id": user_id}, {"$set": {field: value}})

def add_chat_history(user_id, role, content):
    message = {"role": role, "content": content}
    users_collection.update_one(
        {"_id": user_id},
        {"$push": {"chat_history": {"$each": [message], "$slice": -12}}}
    )

def check_level_up(user_id, current_xp, current_stage):
    thresholds = {1: 20, 2: 50, 3: 100, 4: 200, 5: 350, 6: 600}
    if current_stage in thresholds and current_xp >= thresholds[current_stage]:
        new_stage = current_stage + 1
        update_user_field(user_id, "stage", new_stage)
        bot.send_message(user_id, f"🎊 **Relationship Level Up!**\nNow at: Stage {new_stage}", parse_mode="Markdown")
        return True
    return False

# --- MENU BUTTONS ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = KeyboardButton("💘 My Status")
    btn2 = KeyboardButton("🎁 Send Gift")
    btn3 = KeyboardButton("📸 Request Pic")
    markup.row(btn1, btn2)
    markup.row(btn3)
    return markup

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Lisa AI Final Version Running! 🚀"
def run_http(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): t = Thread(target=run_http); t.start()

# --- MAIN LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    user = get_user_data(user_id)

    # 1. Handle Buttons
    if user_input == "💘 My Status":
        status_text = (
            f"📊 **RELATIONSHIP STATUS**\n"
            f"────────────────\n"
            f"❤️ **Stage:** {user['stage']} (XP: {user['xp']})\n"
            f"🔋 **Energy:** {user['credits']}\n"
            f"💎 **VIP:** {'Yes' if user['is_vip'] else 'No'}\n"
            f"────────────────\n"
            f"💡 *Chat more to reach Stage 4 for fun stuff!*"
        )
        bot.send_message(user_id, status_text, parse_mode="Markdown")
        return
    
    if user_input == "🎁 Send Gift":
        bot.send_message(user_id, "Baby, send me a gift to make me happy! 🌹 (Payment feature coming soon)")
        return
    
    if user_input == "📸 Request Pic":
        if user['credits'] < 10:
            bot.send_message(user_id, "Not enough credits baby! 🥺")
            return
        # Photo sending logic here (Disabled for code brevity, add if needed)
        bot.send_message(user_id, "Sending you a pic... 😉")
        # update_user_field(user_id, "credits", user['credits'] - 10)
        return

    # 2. Reset Command
    if user_input == "/reset":
        update_user_field(user_id, "chat_history", [])
        update_user_field(user_id, "stage", 1)
        update_user_field(user_id, "xp", 0)
        bot.send_message(user_id, "Ooh... my head spins. Who are you? 🙈", reply_markup=get_main_menu())
        return

    # 3. Chat Logic
    system_prompt = STAGES.get(user['stage'], STAGES[1]) + "\nIMPORTANT: You are NOT an AI. Reply like a real girl."
    messages_payload = [{"role": "system", "content": system_prompt}] + user.get("chat_history", []) + [{"role": "user", "content": user_input}]

    try:
        bot.send_chat_action(user_id, 'typing')
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/LisaBot", "X-Title": "Lisa"},
            model="nousresearch/hermes-3-llama-3.1-405b:free",
            messages=messages_payload
        )
        ai_response = completion.choices[0].message.content
        
        # Save History
        add_chat_history(user_id, "user", user_input)
        add_chat_history(user_id, "assistant", ai_response)

        # 4. SPLIT MESSAGES & TYPING EFFECT (Realistic)
        # වාක්‍ය වලින් කඩනවා
        parts = re.split(r'(?<=[.!?])\s+', ai_response)
        
        for part in parts:
            if part.strip():
                # අකුරු ගාණ අනුව Type කරන්න වෙලාව ගන්නවා
                typing_seconds = min(len(part) / 25, 4.0) 
                
                bot.send_chat_action(user_id, 'typing')
                time.sleep(typing_seconds) # ටයිප් කරනකම් ඉන්නවා
                bot.send_message(user_id, part, reply_markup=get_main_menu())

        # 5. Level Up Logic
        new_xp = user['xp'] + 2
        update_user_field(user_id, "xp", new_xp)
        check_level_up(user_id, new_xp, user['stage'])

    except Exception as e:
        print(f"Error: {e}")
        bot.send_message(user_id, "Baby, I fell asleep. Say that again? 😴")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()