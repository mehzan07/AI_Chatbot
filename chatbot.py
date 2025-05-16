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

# This function sets up the SQLite database and creates a table for storing chat history. with three columns: session_id, user_input and bot_response.
def setup_database():
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            session_id TEXT,
            user_input TEXT,
            bot_response TEXT
        )
    """)
    conn.commit()
    conn.close()
# This function sets up the SQLite database and creates a table for storing chat history.


# Ensure database exists by calling the setup_database function
setup_database()  

# This function saves the user input and bot response to the SQLite database. It takes three parameters: session_id, user_input, and bot_response.
def save_to_db(session_id, user_input, bot_response):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (session_id, user_input, bot_response) VALUES (?, ?, ?)",
                   (session_id, user_input, bot_response))
    conn.commit()
    conn.close()



# Retrieve last message for context-aware responses from database
# This function fetches the last bot response from the database to provide context for the next response.
def get_last_message(session_id, user_input):
    normalized_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))

    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT bot_response FROM chats 
        WHERE session_id = ? AND user_input = ? 
        ORDER BY ROWID DESC LIMIT 1
    """, (session_id, normalized_input))
    last_message = cursor.fetchone()
    conn.close()
    return last_message[0] if last_message else ""


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
# This function handles incoming requests to the /chat endpoint. It retrieves the user input from the form, generates a response using the chatbot_response function, and returns the response to the user.

def chatbot_response(session_id: str, user_input: str) -> str:
    normalized_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))

    cached_response = get_last_message(session_id, normalized_input)
    if cached_response:
        return cached_response

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
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

    if is_valid_response(bot_response):
        save_to_db(session_id, normalized_input, bot_response)

    return bot_response


# Flask Chat Interface (html form  for user input )
# This function handles incoming requests to the /chat endpoint. It retrieves the user input from the form, generates a response using the chatbot_response function, and returns the response to the user.
@app.route('/')
def home():
    return '''<form action="/chat" method="post">
                <input type="text" name="message" placeholder="Type your message">
                <button type="submit">Send</button>
              </form>'''


# This function handles incoming requests to the /chat endpoint. It retrieves the user input from the form, 
# generates a response using the chatbot_response function, and returns the response to the user.
from flask import session
import uuid

app.secret_key = "your_secret_key_here"  # Needed for session support

@app.route('/chat', methods=['POST'])
def chat():
    try:
        user_input = request.form.get("message", "")
        logging.debug(f"User Input: {user_input}")

        if not user_input:
            return "Chatbot: Please type a message."

        # Assign or retrieve session ID
        if "session_id" not in session:
            session["session_id"] = str(uuid.uuid4())
        session_id = session["session_id"]

        response = chatbot_response(session_id, user_input)
        logging.debug(f"Bot Response: {response}")

        return f"Chatbot: {response}"

    except Exception as e:
        logging.error(f"Internal Server Error: {e}", exc_info=True)
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


# Todo:

#Chat history display

#Multi-language support

# Persistent user memory

#Voice input/output


# 1 Adding user/session tracking: done
# 2 Add more languages and localization
# 3 Supporting contextual conversations (chat history)
# 4 Logging errors/usage stats for analysis

# 5 Switching to gpt-4 for even better reasoning
# 6 Add more tests and unit tests
# 7  Add more features like voice recognition, text-to-speech, etc.
# 8 Add more documentation and comments
