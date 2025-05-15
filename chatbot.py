# Creating AI Chatbot setp by step
# Import necessary libraries in chatbot.py:import nltk

from flask import Flask, request
import sqlite3
import string
import nltk
import requests
from nltk.tokenize import word_tokenize
from transformers import pipeline
from datetime import datetime
import logging
import traceback

import os
import openai # first run: install openai ; in not worked: run: python -m pip install openai.
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage



print("Traceback module loaded:", traceback)

# Ensure NLTK loads resources correctly
nltk.data.path.append(os.path.join(os.getenv("USERPROFILE"), "AppData\\Roaming\\nltk_data"))
try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")

# Initialize Flask app (web framwork) Here’s what it does:
# creates an instance of the Flask class, which is used to build a web application.
# The __name__ argument lets Flask know where the application's resources (like templates and static files) are located. It helps Flask determine the root of your application.
# Essentially, this line sets up the foundation of your chatbot's web service, allowing it to handle requests and responses.

app = Flask(__name__)

 #Enable logging for debugging
logging.basicConfig(level=logging.DEBUG)  # Prints errors in console


# Debugging Helper Function
def log_error(error):
    print(f"ERROR: {error}")  # Print errors to console for debugging

# Create SQLite Database & Table: if chats table does not exist, it creates one with two columns: user_input and bot_response.
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

# Ensure database exists by calling the setup_database function
setup_database()  

# Store conversation in SQLite
def save_to_db(user_input, bot_response):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_input, bot_response) VALUES (?, ?)", (user_input, bot_response))
    conn.commit()
    conn.close()

# Retrieve last message for context-aware responses from database
# This function fetches the last bot response from the database to provide context for the next response.
def get_last_message(user_input):
    # Normalize for consistency
    normalized_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT bot_response FROM chats WHERE user_input = ? ORDER BY ROWID DESC LIMIT 1",
        (normalized_input,)
    )
    last_message = cursor.fetchone()
    conn.close()
    return last_message[0] if last_message else ""

#

# to check a response from OpenAI API is valid or not
# This function checks if the response from the OpenAI API is valid by looking for common error messages or keywords.

# ✅ Function to validate chatbot responses
def is_valid_response(response: str) -> bool:
    if not response or not response.strip():
        return False

    invalid_keywords = [
        "something went wrong",
        "error:",
        "exception",
        "traceback",
        "insufficient_quota",
        "no longer supported",
        "invalid request",
        "you exceeded your quota"
    ]
    response_lower = response.lower()
    return not any(err in response_lower for err in invalid_keywords)

# ✅ OpenAI client initialization
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ✅ Main chatbot function
def chatbot_response(user_input: str) -> str:
    normalized_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))
    # check if response is already in DB
    # This function checks if the response for the given user input is already cached in the database.
    cached_response = get_last_message(normalized_input)
    if cached_response:
        return cached_response

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-4" if you have access
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_input}
            ],
            max_tokens=200,
            temperature=0.7
        )

        bot_response = response.choices[0].message.content.strip()

    except Exception as e:
        traceback.print_exc()
        bot_response = f"Oops! Something went wrong: {str(e)}"

    # ✅ Save to DB only if response is valid
    if is_valid_response(bot_response):
        save_to_db(normalized_input, bot_response)

    return bot_response


# Flask Chat Interface (html form  for user input )
# This function handles incoming requests to the /chat endpoint. It retrieves the user input from the form, generates a response using the chatbot_response function, and returns the response to the user.
@app.route('/')
def home():
    return '''<form action="/chat" method="post">
                <input type="text" name="message" placeholder="Type your message">
                <button type="submit">Send</button>
              </form>'''


# This defines a route for /chat, and it specifically allows POST requests.
# When a user submits the form, the data is sent to this endpoint, where the chatbot processes the input and generates a response.
@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.form.get("message", "")
        logging.debug(f"User Input: {user_input}")  # Debugging print

        if not user_input:
            return "Chatbot: Please type a message."

        response = chatbot_response(user_input)
        logging.debug(f"Bot Response: {response}")  # Debugging print

        return f"Chatbot: {response}"

    except Exception as e:
        logging.error(f"Internal Server Error: {e}", exc_info=True)  # Prints full error details
        return "Chatbot: Internal Server Error", 500


# Run Flask Server
# This line checks if the script is being run directly (not imported as a module). If it is, it starts the Flask web server.
# The debugpy module is used to enable debugging capabilities, allowing developers to connect a debugger to the running application.
# The app.run() method starts the Flask application, making it accessible via a web browser.
# The debug=True flag enables debug mode, which provides detailed error messages and auto-reloads the server on code changes.
# The use_reloader=False and use_debugger=False flags are set to prevent Flask from running the debugger and reloader twice when in debug mode.

if __name__ == "__main__":
    import debugpy  
    debugpy.listen(("0.0.0.0", 5678))  # Enables debugging:This sets up a debugging server that listens on port 5678. and The 0.0.0.0 means it’s accessible from any IP address, which can be useful in Docker containers or remote environments.
    #debugpy.wait_for_client()  # Wait for the debugger to attach before continuing
    print("Waiting for debugger connection...")
    app.run(debug=True, use_reloader=False, use_debugger=False)


    # todo:
    # 1. Add more features like voice recognition, text-to-speech, etc.
    # 2. Add more error handling and logging
    # 3. Add more tests and unit tests
    # 4. Add more documentation and comments
    # 5. Add more languages and localization
    # 6. Add more models and frameworks
    # 7. Add more databases and storage options
    

# Adding user/session tracking

# #Supporting contextual conversations (chat history)

Logging errors/usage stats for analysis

#Switching to gpt-4 for even better reasoning
