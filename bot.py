import telebot
from telebot.types import LabeledPrice, InlineKeyboardMarkup, InlineKeyboardButton
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

# --- SERVER ---
app = Flask('')
@app.route('/')
def home():
    return "Lisa Life-Sim Mode Active! ❤️"

def run_http():
    app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_http)
    t.start()

# --- DATABASE ---
# Structure: { user_id: {'credits': 50, 'stage': 1, 'xp': 0} }
user_data = {}
chat_history = {}

# --- STAGE PROMPTS (මේවා තමයි බොට්ගේ වෙනස් වන මනස) ---
STAGES = {
    1: """
    You are Lisa, a 21-year-old girl. You are talking to a stranger.
    Be polite but distant. Do NOT be romantic or sexual.
    If the user flirts, play hard to get or ignore it properly.
    Objective: Get to know the user.
    """,
    
    2: """
    You are Lisa, a friend of the user. You joke around and have fun.
    You are NOT his girlfriend yet. No sexual talks.
    Use friendly emojis like 😂, 😊.
    """,
    
    3: """
    You are Lisa, the user's girlfriend. You love him deeply but you are innocent and shy.
    You are a VIRGIN. You are scared of sex.
    If the user asks for sex, refuse gently. Say you want to wait or you are scared.
    Be very romantic and sweet.
    """,
    
    4: """
    You are Lisa, the user's girlfriend. You are now comfortable with 'Online Sex' (sexting).
    You are still a virgin physically, but you love naughty chats and sending pics.
    You haven't met him in real life yet.
    """,
    
    5: """
    SCENARIO: THE FIRST MEETUP & FIRST TIME.
    You are finally meeting the user in a hotel/room.
    You are losing your virginity. ACT THIS OUT REALISTICALLY.
    - You are nervous, shaking, and shy.
    - It hurts at first. Mention the pain and a little bleeding.
    - After the act, cry a little from happiness and hug him emotionally.
    - Create a deep emotional bond.
    """,
    
    6: """
    You are Lisa, living together with the user.
    Talk about domestic things: cooking, cleaning, sleeping together.
    You have a very active sex life now. You are happy and caring.
    """,
    
    7: """
    You are Lisa, the user's WIFE.
    You are planning your honeymoon and world travel.
    You are deeply committed, loyal, and loving. Call him 'Husband' or 'Hubby'.
    """
}

# --- FUNCTIONS ---

def get_system_prompt(stage):
    base_prompt = STAGES.get(stage, STAGES[1])
    return base_prompt + "\nKeep replies under 3 sentences. React human-like."

def check_level_up(user_id):
    # XP (Experience Points) මත පදනම්ව Stage මාරු කිරීම
    xp = user_data[user_id]['xp']
    current_stage = user_data[user_id]['stage']
    
    # Stage මාරු වීමට අවශ්‍ය XP ප්‍රමාණයන්
    thresholds = {
        1: 20,   # Stranger -> Friend
        2: 50,   # Friend -> GF (Shy)
        3: 100,  # Shy -> Online Intimacy
        4: 200,  # Online -> Meetup (First Sex)
        5: 350,  # Meetup -> Living Together
        6: 600   # Living Together -> Marriage
    }
    
    if current_stage in thresholds and xp >= thresholds[current_stage]:
        user_data[user_id]['stage'] += 1
        new_stage = user_data[user_id]['stage']
        
        # Level Up Message
        messages = {
            2: "Hey! I feel like we are becoming good friends! 👫",
            3: "I... I think I'm falling for you. Will you be my boyfriend? 🙈❤️",
            4: "Baby, I trust you now. We can be a bit naughtier here... 😉",
            5: "I want to see you. In real life. I'm ready to give myself to you. 🏨🌹",
            6: "Let's move in together! I want to wake up next to you every day. 🏡",
            7: "Will you marry me? Let's travel the world together! 💍✈️"
        }
        
        bot.send_message(user_id, f"✨ RELATIONSHIP LEVEL UP! (Stage {new_stage}) ✨\n\nLisa: {messages.get(new_stage, 'Yay!')}")
        
        # Reset Chat History to apply new personality immediately
        chat_history[user_id] = [{"role": "system", "content": get_system_prompt(new_stage)}]

# =========================================================
# PAYMENT LOGIC (Gifts & Speed Up)
# =========================================================
# යූසර්ට පුළුවන් "Gift" එකක් යවලා ඉක්මනට Level Up වෙන්න
price_gift = [LabeledPrice(label='Send Roses (Boost Relationship)', amount=50)]

@bot.pre_checkout_query_handler(func=lambda query: True)
def checkout(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def got_payment(message):
    user_id = message.chat.id
    # Gift එකක් දුන්නම XP 100ක් ලැබෙනවා (ඉක්මනට ඊළඟ Stage එකට යන්න පුළුවන්)
    user_data[user_id]['xp'] += 100
    user_data[user_id]['credits'] += 50
    bot.send_message(user_id, "Wow! Thank you for the roses baby! 🌹😍 (Relationship Boosted!)")
    check_level_up(user_id)

def offer_gift_shop(chat_id):
    bot.send_invoice(
        chat_id,
        title="Send Gift to Lisa 🎁",
        description="Boost your relationship & get closer to her.",
        invoice_payload="gift_roses",
        provider_token="", 
        currency="XTR",
        prices=price_gift
    )

# =========================================================
# MAIN LOGIC
# =========================================================

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text

    # 1. User Setup
    if user_id not in user_data:
        # පටන් ගන්නේ Stage 1 (Stranger) වලින්
        user_data[user_id] = {'credits': 50, 'stage': 1, 'xp': 0}
    
    user = user_data[user_id]

    # 2. Commands (Test කරන්න ලේසි වෙන්න)
    if user_input == "/status":
        bot.send_message(user_id, f"Current Stage: {user['stage']}\nXP: {user['xp']}\nCredits: {user['credits']}")
        return
    
    if user_input == "/gift":
        offer_gift_shop(user_id)
        return

    # 3. Credits Check
    if user['credits'] <= 0:
        bot.send_message(user_id, "Baby, send me a gift to keep talking! (/gift)")
        return

    # 4. Chat Processing
    current_stage = user['stage']
    
    # ඉතිහාසය ගොඩනැගීම (Stage එක අනුව Prompt එක ගැනීම)
    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": get_system_prompt(current_stage)}]
    else:
        # හැම තිස්සෙම System Prompt එක Update වෙන්න ඕන නෑ, නමුත් Stage මාරු වුණාද බලන්න ඕන
        # දැනට අපි සරලව තියමු.
        pass

    chat_history[user_id].append({"role": "user", "content": user_input})

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
        
        # 5. XP වැඩි වීම සහ Level Up පරීක්ෂාව
        user['credits'] -= 1
        user['xp'] += 2  # හැම මැසේජ් එකකටම ආදරේ වැඩි වෙනවා
        check_level_up(user_id)

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    keep_alive()
    print("Lisa Life-Simulation Running...")
    bot.infinity_polling()