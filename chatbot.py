# Creating AI Chatbot setp by step
# Import necessary libraries in chatbot.py:import nltk

from flask import Flask, request
import sqlite3
import string
import nltk
import os
import requests
from nltk.tokenize import word_tokenize
from transformers import pipeline
from datetime import datetime

# Ensure NLTK loads resources correctly
nltk.data.path.append(os.path.join(os.getenv("USERPROFILE"), "AppData\\Roaming\\nltk_data"))
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

# Initialize Flask app
app = Flask(__name__)

# Initialize Hugging Face model
chatbot_model = pipeline("text-generation", model="microsoft/DialoGPT-medium")

# Create SQLite Database & Table
def setup_database():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            user_input TEXT,
            bot_response TEXT
        )
    """)
    conn.commit()
    conn.close()

setup_database()  # Ensure database exists

# Store conversation in SQLite
def save_to_db(user_input, bot_response):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_input, bot_response) VALUES (?, ?)", (user_input, bot_response))
    conn.commit()
    conn.close()

# Retrieve last message for context-aware responses
def get_last_message():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT bot_response FROM chats ORDER BY ROWID DESC LIMIT 1")
    last_message = cursor.fetchone()
    conn.close()
    return last_message[0] if last_message else ""

# Fetch factual answers from web search
def search_web(query):
    """Search for factual answers using Bing."""
    url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
    headers = {"Ocp-Apim-Subscription-Key": "YOUR_BING_API_KEY"}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "webPages" in data and "value" in data["webPages"]:
            return data["webPages"]["value"][0]["snippet"]  # Extracting a reliable snippet
        return "I couldn't find an answer. Try asking differently!"
    return "I encountered an error fetching data. Please try again later!"

# Improved response generation using AI and web search
def chatbot_response(user_input):
    user_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))  # Normalize text

    # Tokenization for better recognition
    try:
        tokens = word_tokenize(user_input)
    except LookupError:
        tokens = user_input.split()  # Fallback method

    # Retrieve previous chatbot messages for better response context
    last_message = get_last_message()

    # Handle date-related queries
    if "date" in tokens or "today" in tokens:
        bot_response = f"Today's date is {datetime.now().strftime('%A, %B %d, %Y')}."
    # Handle factual queries using web search
    elif any(word in tokens for word in ["capital", "president", "define", "weather"]):
        bot_response = search_web(user_input)
    else:
        # AI model generates response dynamically
        ai_response = chatbot_model(f"User: {user_input}\nChatbot (based on previous message '{last_message}'): ", max_length=100)
        bot_response = ai_response[0]["generated_text"].strip()

        # Prevent chatbot from echoing user input directly
        if bot_response.lower() == user_input.lower():
            bot_response = "I'm still learning! Can you ask me in a different way?"

    # Save conversation history
    save_to_db(user_input, bot_response)
    return bot_response

# Flask Chat Interface
@app.route('/')
def home():
    return '''<form action="/chat" method="post">
                <input type="text" name="message" placeholder="Type your message">
                <button type="submit">Send</button>
              </form>'''

@app.route('/chat', methods=['POST'])
def chat():
    # Handle form-based requests
    user_input = request.form.get("message", "")

    response = chatbot_response(user_input)
    return f"Chatbot: {response}"

# Run Flask Server
if __name__ == "__main__":
    app.run(debug=True)