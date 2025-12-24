import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import time
from datetime import datetime, timedelta
import certifi
import re

# --- 1. SETUP ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
MONGO_URI = os.environ.get("MONGO_URI")

# Check if keys exist
if not BOT_TOKEN or not OPENROUTER_API_KEY or not MONGO_URI:
    print("CRITICAL: Environment variables missing!")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

mongo_client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = mongo_client["lisa_db"]
users_collection = db["users"]

# --- STAGES ---
STAGES = {
    1: "Role: Lisa (21). Act: Polite stranger. Goal: Get friendly. NO Sex.",
    2: "Role: Lisa. Act: Flirty friend. Tease him.",
    3: "Role: Lisa (Girlfriend). Act: LOVE sexting. But VIRGIN.",
    4: "Role: Lisa (Deep Love). Act: Ready for sex.",
    5: "SCENARIO: FIRST TIME SEX. Nervous & Emotional.",
    6: "Role: Lisa (Wife). High sex drive.",
}

def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(KeyboardButton("💘 Status"), KeyboardButton("🎁 Gift"))
    markup.row(KeyboardButton("📸 Send Pic"), KeyboardButton("🔥 Naughty Chat"))
    return markup

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Lisa Debug Mode: Active 🟡"
def run_http(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): t = Thread(target=run_http); t.start()

# --- MAIN LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    
    try:
        # User Data Check
        user = users_collection.find_one({"_id": user_id})
        if not user:
            new_user = {"_id": user_id, "stage": 1, "xp": 0, "chat_history": []}
            users_collection.insert_one(new_user)
            user = new_user

        # Reset Command
        if user_input == "/reset":
            users_collection.update_one({"_id": user_id}, {"$set": {"chat_history": [], "stage": 1}})
            bot.send_message(user_id, "Reset Complete. Hi!", reply_markup=get_main_menu())
            return

        # AI Processing
        system_prompt = STAGES.get(user['stage'], STAGES[1])
        messages = [{"role": "system", "content": system_prompt}] + user.get("chat_history", []) + [{"role": "user", "content": user_input}]

        bot.send_chat_action(user_id, 'typing')
        
        # --- OPENROUTER CALL ---
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/LisaBot", "X-Title": "Lisa"},
            # මෙන්න අපි පාවිච්චි කරන මොඩල් එක
            model="google/gemini-2.0-flash-exp:free",
            messages=messages
        )
        
        ai_response = completion.choices[0].message.content
        
        if not ai_response:
            bot.send_message(user_id, "⚠️ Error: AI sent an empty response.")
            return

        # History Update
        msg_data = {"role": "user", "content": user_input}
        resp_data = {"role": "assistant", "content": ai_response}
        users_collection.update_one(
            {"_id": user_id},
            {"$push": {"chat_history": {"$each": [msg_data, resp_data], "$slice": -10}}}
        )

        # Sending Message
        bot.send_message(user_id, ai_response, reply_markup=get_main_menu())

    except Exception as e:
        # --- වැදගත්ම කොටස: ERROR එක ඔයාට එවනවා ---
        error_msg = f"⚠️ SYSTEM ERROR:\n{str(e)}"
        print(error_msg)
        bot.send_message(user_id, error_msg)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()