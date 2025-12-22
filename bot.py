import telebot
from telebot.types import LabeledPrice
from openai import OpenAI
import os
import random
from flask import Flask
from threading import Thread

# --- SETUP ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# --- CONFIG ---
STARTING_CREDITS = 5   # මුලින්ම නොමිලේ දෙන ගාණ
COST_MSG = 1            # මැසේජ් එකකට කැපෙන ගාණ
COST_PHOTO = 15         # ෆොටෝ එකකට කැපෙන ගාණ

# --- DATABASE (Simple) ---
# user_data = { user_id: {'credits': 50, 'is_vip': False} }
user_data = {}
chat_history = {}

# --- SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "Lisa Hybrid Mode Active! 💎"

def run_http():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are Lisa, a 21-year-old playful and romantic girlfriend. 
You love the user deeply.
If the user asks for a photo, say "Here is a pic for you baby 😘".
Keep replies short, engaging, and use emojis.
"""

# --- PHOTO FUNCTION ---
def send_random_photo(chat_id):
    try:
        if not os.path.exists('photos'):
            return False
        photo_files = [f for f in os.listdir('photos') if f.endswith(('.jpg', '.png', '.jpeg'))]
        if photo_files:
            random_photo = random.choice(photo_files)
            photo_path = os.path.join('photos', random_photo)
            with open(photo_path, 'rb') as photo:
                bot.send_chat_action(chat_id, 'upload_photo')
                bot.send_photo(chat_id, photo)
            return True
        return False
    except Exception as e:
        print(f"Photo Error: {e}")
        return False

# =========================================================
# 💰 PAYMENT LOGIC (Hybrid Level System)
# =========================================================

# Option 1: Credits Pack (Stars 50)
price_credits = [LabeledPrice(label='100 Credits Pack', amount=50)]

# Option 2: VIP Upgrade (Stars 500)
price_vip = [LabeledPrice(label='VIP Boyfriend Pass (Unlimited Chat)', amount=500)]

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.chat.id
    amount = message.successful_payment.total_amount
    payload = message.successful_payment.invoice_payload

    # User Data නැත්නම් හදාගන්න
    if user_id not in user_data:
        user_data[user_id] = {'credits': STARTING_CREDITS, 'is_vip': False}

    if payload == 'credit_pack':
        # Credits 100ක් එකතු කරනවා
        user_data[user_id]['credits'] += 100
        bot.send_message(user_id, "Credits added! 😘 You have " + str(user_data[user_id]['credits']) + " credits now.")
    
    elif payload == 'vip_upgrade':
        # VIP කරනවා
        user_data[user_id]['is_vip'] = True
        user_data[user_id]['credits'] += 50 # Bonus credits for photos
        bot.send_message(user_id, "OMG! You are officially my Boyfriend now! 💍❤️\n(Unlimited Chat Activated + 50 Photo Credits)")

# සල්ලි ඉල්ලන Function එක (Menu එකක් වගේ)
def offer_shop(chat_id):
    bot.send_message(chat_id, "Baby, we are out of energy! 🥺\n\nChoose an option:")
    
    # Invoice 1: Buy Credits
    bot.send_invoice(
        chat_id,
        title="1. Refill Energy 🔋",
        description="Get 100 Credits for chatting & photos.",
        invoice_payload="credit_pack",
        provider_token="", 
        currency="XTR",
        prices=price_credits
    )
    
    # Invoice 2: Buy VIP
    bot.send_invoice(
        chat_id,
        title="2. Be My Boyfriend (VIP) 💍",
        description="UNLIMITED Chatting forever! No text costs.",
        invoice_payload="vip_upgrade",
        provider_token="", 
        currency="XTR",
        prices=price_vip
    )

# =========================================================
# MAIN LOGIC
# =========================================================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text

    # 1. User Account Check
    if user_id not in user_data:
        user_data[user_id] = {'credits': STARTING_CREDITS, 'is_vip': False}
    
    user = user_data[user_id] # කෙටි නම

    # 2. Check "Photo" Request
    keywords = ['photo', 'pic', 'selfie', 'image', 'nude', 'ෆොටෝ']
    is_photo_request = any(word in user_input.lower() for word in keywords)

    # 3. Cost Calculation
    cost = 0
    if is_photo_request:
        cost = COST_PHOTO
    elif not user['is_vip']: # VIP නොවේ නම් පමණක් Chat වලට කැපෙයි
        cost = COST_MSG
    
    # 4. Balance Check
    if user['credits'] < cost:
        offer_shop(user_id) # සල්ලි ඉවරයි, Shop එක පෙන්වන්න
        return

    # --- Proceed to Chat ---
    
    # ෆොටෝ ඉල්ලුවා නම් යවන්න
    if is_photo_request:
        sent = send_random_photo(user_id)
        if sent:
            user['credits'] -= cost # යැව්වා නම් විතරක් සල්ලි කපන්න
            print(f"User {user_id} spent {cost} credits on photo.")

    # සාමාන්‍ය Chat Logic
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
        
        # Text Cost අඩු කිරීම (VIP නොවේ නම් ෆොටෝ නැති වෙලාවට)
        if not is_photo_request and not user['is_vip']:
            user['credits'] -= cost
            print(f"User {user_id} spent {cost} credit. Balance: {user['credits']}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    print("Lisa Hybrid System Running...")
    bot.infinity_polling()