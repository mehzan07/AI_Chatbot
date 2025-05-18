# Creating AI Chatbot setp by step
# Import necessary libraries in chatbot.py:import nltk

from flask import Flask, request, make_response
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



# This function retrieves the last bot response from the database to provide context for the next response.
# It takes the user input as a parameter, normalizes it, and queries the database for the last bot response.from datetime import datetime
import sqlite3

def save_to_db(session_id, user_input, bot_response):
    conn = sqlite3.connect("your_database.db")  # Replace with actual path
    cursor = conn.cursor()

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO chats (session_id, user_input, bot_response, timestamp)
        VALUES (?, ?, ?, ?)
    """, (session_id, user_input, bot_response, current_time))

    conn.commit()
    conn.close()




# Retrieve last message for context-aware responses from database
# This function fetches the last bot response from the database to provide context for the next response.
def get_last_message(user_input):
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

    # ✅ Intercept datetime questions before any DB or API calls
    datetime_answer = detect_datetime_question(user_input)
    if datetime_answer:
     print(f"[INFO] Handled as datetime response: {datetime_answer}")
     return datetime_answer

    cached_response = get_last_message(normalized_input)
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

    if is_valid_response(bot_response) \
    and not detect_datetime_question(user_input) \
    and not looks_like_datetime_response(bot_response):
    
     save_to_db(session_id, normalized_input, bot_response)

# This function checks if the response from the OpenAI API is valid by looking for common error messages or keywords.
# This function checks if the response contains date/time-like content. It uses a list of keywords and regex patterns to identify such content.

import re
# This function checks if the response contains date/time-like content. It uses a list of keywords and regex patterns to identify such content.
def looks_like_datetime_response(response: str) -> bool:
    response = response.lower()

    # Regex: look for very specific datetime phrases or formats
    datetime_patterns = [
        r"\btoday is\b",
        r"\bcurrent date\b",
        r"\bthe date is\b",
        r"\bnow is\b",
        r"\btime is\b",
        r"\b\d{4}-\d{2}-\d{2}\b",  # e.g., 2025-05-17
        r"\b\d{1,2} (january|february|march|april|may|june|july|august|september|october|november|december) \d{4}\b",
        r"\bit's (monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b",
        r"\bthis month is\b",
        r"\bthe month is\b",
        r"\btoday\b",
        r"\bthis year\b",
        r"\bthis week\b"
    ]

    for pattern in datetime_patterns:
        if re.search(pattern, response):
            return True
    return False



# Flask Chat Interface (html form  for user input )
# This function handles incoming requests to the / endpoint. It retrieves the user input from the form, generates a response using the chatbot_response function, and returns the response to the user.
from flask import Flask, request, make_response, redirect

@app.route("/", methods=["GET"])
def home():
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; }}
                input[type="text"] {{ width: 80%; padding: 10px; }}
                button {{ padding: 10px 15px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h2>Chatbot</h2>
            <form action="/chat" method="post">
                <input type="text" name="message" placeholder="Type your message" required>
                <button type="submit">Send</button>
            </form>
            <form action="/history" method="get">
                <button type="submit">Show History</button>
            </form>
        </body>
        </html>
    """
    response = make_response(html)
    response.set_cookie("session_id", session_id, max_age=60*60*24*7)
    return response


# This function handles incoming requests to the /chat endpoint. It retrieves the user input from the form, 
# generates a response using the chatbot_response function, and returns the response to the user.

app.secret_key = "your_secret_key_here"  # Needed for session support

from flask import session
from flask import request, make_response, redirect
import uuid
from chatbot import chatbot_response  

@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    user_input = request.form.get("message", "")
    if not user_input:
        return redirect("/")  # No message submitted, go back to home

    bot_reply = chatbot_response(session_id, user_input)

    html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; }}
                .user {{ color: #0066cc; font-weight: bold; }}
                .bot {{ color: #009933; }}
                .chat-box {{ border-bottom: 1px solid #ccc; padding: 10px 0; }}
                button {{ padding: 10px 15px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h2>Chatbot</h2>
            <div class="chat-box">
                <div class="user">You: {user_input}</div>
                <div class="bot">Bot: {bot_reply}</div>
            </div>
            <form action="/" method="get">
                <button type="submit">New Question</button>
            </form>
            <form action="/history" method="get">
                <button type="submit">Show History</button>
            </form>
        </body>
        </html>
    """

    response = make_response(html)
    response.set_cookie("session_id", session_id, max_age=60 * 60 * 24 * 7)  # 1 week
    return response

#Show Past Messages per Session
# This function checks if the user input contains common datetime-related keywords and returns a predefined response.

def get_conversation_history(session_id):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_input, bot_response, timestamp FROM chats WHERE session_id = ? ORDER BY ROWID ASC",
        (session_id,)
    )
    messages = cursor.fetchall()
    conn.close()
    return messages


# This function is designed to detect and respond to common datetime-related questions without using the OpenAI API 
# and without saving the response to the database.
from datetime import datetime, timedelta

def detect_datetime_question(user_input: str) -> str | None:
    text = user_input.lower()

    if any(kw in text for kw in ["what time", "current time", "now", "time is it"]):
        return f"The current time is {datetime.now().strftime('%H:%M:%S')}."

    if any(kw in text for kw in ["what's the date", "what is the date", "current date", "today's date", "what date is it", "which date"]):
        return f"Today's date is {datetime.now().strftime('%Y-%m-%d')}."

    if any(kw in text for kw in ["which month", "what month", "current month", "month is this"]):
        return f"This month is {datetime.now().strftime('%B')}."

    if any(kw in text for kw in ["which day", "what day", "day is it", "current day", "today"]):
        return f"Today is {datetime.now().strftime('%A')}."

    if any(kw in text for kw in ["which year", "what year", "current year", "year is this"]):
        return f"This year is {datetime.now().strftime('%Y')}."

    return None

@app.route("/history", methods=["GET"])
def history():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return redirect("/")

    history = get_conversation_history(session_id)

    history_html = ""
    for user_input, bot_response, timestamp in history:
        history_html += f"""
            <div class="chat-box">
                <div><strong>[{timestamp}]</strong></div>
                <div class="user">You: {user_input}</div>
                <div class="bot">Bot: {bot_response}</div>
            </div>
        """

    html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: auto; padding: 20px; }}
                .user {{ color: #0066cc; font-weight: bold; }}
                .bot {{ color: #009933; }}
                .chat-box {{ border-bottom: 1px solid #ccc; padding: 10px 0; }}
                button {{ padding: 10px 15px; margin-top: 10px; }}
            </style>
        </head>
        <body>
            <h2>Chat History</h2>
            {history_html}
            <form action="/" method="get">
                <button type="submit">New Question</button>
            </form>
        </body>
        </html>
    """

    return html




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
# date time related input shall be not handled by opeai it should be fixed

#Chat history display : done

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
