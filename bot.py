import telebot
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread

# =========================================================
# SERVER එකට දාන නිසා මේවා මෙහෙම තියන්න (Render එකෙන් ගන්නවා)
# =========================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

chat_history = {}

# --- 1. මේක තමයි අර බොරු වෙබ්සයිට් කෑල්ල (Dummy Server) ---
app = Flask('')

@app.route('/')
def home():
    return "I am alive! (බොට් වැඩ!)"

def run_http():
    # Render එකට ඕන කරන Port එකේ රන් කරනවා
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_http)
    t.start()
# -------------------------------------------------------

SYSTEM_PROMPT = """
You are Lisa, a 21-year-old playful girlfriend. 
If the user asks for a photo, say something like "Here is a pic for you baby".
Keep replies short and sexy.
"""

def send_random_photo(chat_id):
    try:
        if not os.path.exists('photos'):
            return
        photo_files = [f for f in os.listdir('photos') if f.endswith(('.jpg', '.png', '.jpeg'))]
        if photo_files:
            random_photo = random.choice(photo_files)
            photo_path = os.path.join('photos', random_photo)
            with open(photo_path, 'rb') as photo:
                bot.send_chat_action(chat_id, 'upload_photo')
                bot.send_photo(chat_id, photo)
    except Exception as e:
        print(f"Photo Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    
    keywords = ['photo', 'pic', 'selfie', 'image', 'nude', 'ෆොටෝ', 'පින්තූර']
    if any(word in user_input.lower() for word in keywords):
        send_random_photo(user_id)

    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    chat_history[user_id].append({"role": "user", "content": user_input})
    
    if len(chat_history[user_id]) > 12:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-10:]

    bot.send_chat_action(user_id, 'typing')

    try:
        completion = client.chat.completions.create(
            extra_headers={"HTTP-Referer": "https://telegram.me/MyBot", "X-Title": "My AI Bot"},
            model="nousresearch/hermes-3-llama-3.1-405b:free", 
            messages=chat_history[user_id]
        )
        ai_response = completion.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": ai_response})
        bot.reply_to(message, ai_response)
    except Exception as e:
        print(f"Error: {e}")

# --- 2. බොට් පණ ගන්වන තැන ---
if __name__ == "__main__":
    keep_alive()  # වෙබ් සර්වර් එක පණ ගන්වනවා
    print("Lisa is running on Server...")
    bot.infinity_polling()