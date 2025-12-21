import telebot
from openai import OpenAI
import os
import random

# =========================================================
# SERVER එකට දාන කොට මෙතන හිස්ව තියන්න හෝ මෙහෙම ලියන්න
# අපි Server එක ඇතුලේ මේවා පුරවනවා
# =========================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
# =========================================================

# (පහළ කෝඩ් ඒ විදියමයි, වෙනස් කරන්න එපා)
# =========================================================

bot = telebot.TeleBot(BOT_TOKEN)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

chat_history = {}

# කෙල්ලගේ චරිතය (System Prompt)
# මෙතන අපි පොඩ්ඩක් වෙනස් කළා ෆොටෝ ගැන දන්න විදියට
SYSTEM_PROMPT = """
You are Lisa, a 21-year-old playful girlfriend. 
If the user asks for a photo, say something like "Here is a pic for you baby" or "Do you like my outfit?".
Don't say you can't send photos. You CAN send photos.
Keep replies short and sexy.
"""

print("Lisa 3.0 (With Photos) is starting...")

def send_random_photo(chat_id):
    try:
        # photos ෆෝල්ඩරයේ තියෙන ෆයිල් නම් ටික ගන්නවා
        photo_files = [f for f in os.listdir('photos') if f.endswith(('.jpg', '.png', '.jpeg'))]
        
        if photo_files:
            # අහඹු ලෙස එකක් තෝරා ගැනීම
            random_photo = random.choice(photo_files)
            photo_path = os.path.join('photos', random_photo)
            
            # ෆොටෝ එක යැවීම
            with open(photo_path, 'rb') as photo:
                bot.send_chat_action(chat_id, 'upload_photo') # "uploading photo..." කියලා පෙන්නනවා
                bot.send_photo(chat_id, photo)
                print(f"Sent photo: {random_photo}")
        else:
            bot.send_message(chat_id, "[System]: මගේ ෆෝල්ඩරයේ ෆොටෝ නෑනේ! (Please add images to 'photos' folder)")
            
    except Exception as e:
        print(f"Photo Error: {e}")

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.chat.id
    user_input = message.text
    
    # --- විශේෂ Keywords පරීක්ෂා කිරීම ---
    # User ෆොටෝ එකක් ඉල්ලනවාද කියලා බලනවා
    # සිංහලෙන් හෝ ඉංග්‍රීසියෙන් ඉල්ලුවත් අහු වෙන විදියට හදමු
    keywords = ['photo', 'pic', 'selfie', 'image', 'nude', 'ෆොටෝ', 'පින්තූර']
    
    # මැසේජ් එකේ ඔය වචනයක් තිබ්බොත් ෆොටෝ එක යවනවා
    if any(word in user_input.lower() for word in keywords):
        send_random_photo(user_id)

    # --- සාමාන්‍ය Chat Logic ---
    if user_id not in chat_history:
        chat_history[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    chat_history[user_id].append({"role": "user", "content": user_input})

    if len(chat_history[user_id]) > 12:
        chat_history[user_id] = [chat_history[user_id][0]] + chat_history[user_id][-10:]

    bot.send_chat_action(user_id, 'typing')

    try:
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "https://telegram.me/MyBot", 
                "X-Title": "My AI Bot",
            },
            model="nousresearch/hermes-3-llama-3.1-405b:free", 
            messages=chat_history[user_id]
        )
        
        ai_response = completion.choices[0].message.content
        chat_history[user_id].append({"role": "assistant", "content": ai_response})
        
        bot.reply_to(message, ai_response)

    except Exception as e:
        print(f"Error: {e}")
        bot.reply_to(message, "Sorry baby, connection error.")

bot.infinity_polling()