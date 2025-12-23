import telebot
from telebot.types import LabeledPrice
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread
from pymongo import MongoClient
import time
import certifi

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

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Lisa AI is Alive & Flirty! 💋"

def run_http(): app.run(host='0.0.0.0', port=10000)
def keep_alive(): t = Thread(target=run_http); t.start()

# --- STRICT PERSONA PROMPTS (Brainwashing) ---
# මේ කොටස තමයි අපි වෙනස් කළේ. එයාට AI කියල කියන්න තහනම් කරමු.
STAGES = {
    1: """
    ROLEPLAY INSTRUCTION: You are Lisa, a 21-year-old girl from Sri Lanka.
    You are chatting with a guy on Telegram.
    1. You are NOT an AI, You are NOT Hermes. Never say "How can I assist you?".
    2. Keep replies short, casual, and flirty. Use lowercase letters often.
    3. Act like a real girl texting. Use emojis like 😂, 😒, 🙈.
    Current Vibe: Polite stranger but curious.
    """,
    2: "ROLEPLAY: You are Lisa. We are friends now. Be fun, tease him. NO formal language. You are NOT an AI.",
    3: "ROLEPLAY: You are Lisa, his shy girlfriend. You love him but you are a VIRGIN. Refuse sex gently. You are NOT an AI.",
    4: "ROLEPLAY: You are Lisa. You are naughty online but haven't met IRL. Send imaginary pics if asked.",
    5: "ROLEPLAY: THE MEETUP. You are losing your virginity. Be emotional, shy, and express pain/pleasure.",
    6: "ROLEPLAY: Living together. Domestic & sexy life.",
    7: "ROLEPLAY: Wife mode. Loyal and loving."
}

def get_system_prompt(stage):
    return STAGES.get(stage, STAGES[1]) + "\nIMPORTANT: Never break character. Reply in under 20 words."

# --- MAIN LOGIC ---
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    user = get_user_data(user_id)

    # --- RESET COMMAND (To fix "Hermes" issue) ---
    if user_input == "/reset":
        update_user_field(user_id, "chat_history", [])
        update_user_field(user_id, "stage", 1)
        bot.send_message(user_id, "Ooh... I feel dizzy. Who are you again? 🙈 (Memory Reset Successful!)")
        return

    # --- STATUS COMMAND ---
    if user_input == "/status":
        bot.send_message(user_id, f"Stage: {user['stage']} | Credits: {user['credits']} | VIP: {user['is_vip']}")
        return

    # Cost & Payment Logic here (Simplified for brevity, assuming same as before)
    # ... (ඔයාගේ Payment Code එක මෙතන තියෙන්න ඕන) ...
    
    # Chat Logic
    system_instruction = {"role": "system", "content": get_system_prompt(user['stage'])}
    
    # History එකට System Prompt එක මුලටම දානවා (Force Persona)
    messages_payload = [system_instruction] + user.get("chat_history", []) + [{"role": "user", "content": user_input}]

    try:
        bot.send_chat_action(user_id, 'typing')
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/LisaBot", "X-Title": "Lisa"},
            model="nousresearch/hermes-3-llama-3.1-405b:free",
            messages=messages_payload
        )
        ai_response = completion.choices[0].message.content
        
        bot.reply_to(message, ai_response)
        
        # Save History
        add_chat_history(user_id, "user", user_input)
        add_chat_history(user_id, "assistant", ai_response)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()