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

    if is_valid_response(bot_response):
        save_to_db(session_id, normalized_input, bot_response)    

    return bot_response


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
from flask import session
import uuid

app.secret_key = "your_secret_key_here"  # Needed for session support
@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.cookies.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())

    user_input = request.form.get("message", "")
    if not user_input:
        return redirect("/")

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
                <span class="user">You:</span> {user_input}<br>
                <span class="bot">Bot:</span> {bot_reply}
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
    response.set_cookie("session_id", session_id, max_age=60*60*24*7)
    return response


# This function retrieves the conversation history for a given session ID from the SQLite database.
@app.route("/history", methods=["GET"])
def show_history():
    session_id = request.cookies.get("session_id")
    history = get_conversation_history(session_id)

    chat_history_html = "".join([
        f'<div class="chat-box"><span class="user">You:</span> {u}<br><span class="bot">Bot:</span> {b}</div>'
        for u, b in history
    ])

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
            {chat_history_html}
            <form action="/" method="get">
                <button type="submit">New Question</button>
            </form>
        </body>
        </html>
    """
    return html

#Show Past Messages per Session
def get_conversation_history(session_id):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT user_input, bot_response FROM chats WHERE session_id = ? ORDER BY ROWID ASC",
        (session_id,)
    )
    messages = cursor.fetchall()
    conn.close()
    return messages


# This function is designed to detect and respond to common datetime-related questions without using the OpenAI API 
# and without saving the response to the database.
from datetime import datetime, timedelta
def detect_datetime_question(user_input: str) -> str | None:
    """Handle common datetime-related questions manually."""
    input_lower = user_input.lower()

    if "date" in input_lower and "today" in input_lower:
        return f"Today's date is {datetime.now().strftime('%d %B %Y')}."

    if "time" in input_lower or "clock" in input_lower:
        return f"The current time is {datetime.now().strftime('%H:%M')}."

    if "day" in input_lower and "today" in input_lower:
        return f"Today is {datetime.now().strftime('%A')}."

    if "yesterday" in input_lower:
        return f"Yesterday was { (datetime.now() - timedelta(days=1)).strftime('%A, %d %B %Y') }."

    if "tomorrow" in input_lower:
        return f"Tomorrow will be { (datetime.now() + timedelta(days=1)).strftime('%A, %d %B %Y') }."

    if "week" in input_lower:
        return f"This week is week {datetime.now().isocalendar()[1]} of the year."

    if "month" in input_lower and "current" in input_lower:
        return f"The current month is {datetime.now().strftime('%B')}."

    # Add more custom logic if needed (e.g., "noon", "evening", "this morning", etc.)
    
    return None



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
