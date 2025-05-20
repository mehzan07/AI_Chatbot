# chatbot.py — AI Chatbot with language detection, datetime handling, and SQLite chat history

from flask import Flask, request, make_response, redirect, session
import sqlite3
import uuid
import os
import json
import logging
import re
from datetime import datetime
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage

# === Initialize Flask App ===
app = Flask(__name__)
app.secret_key = "your_secret_key_here"

# === Enable Logging ===
logging.basicConfig(level=logging.DEBUG)

# === Initialize OpenAI Client ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# === Set up SQLite Database ===
def setup_database():
    with sqlite3.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                session_id TEXT,
                user_input TEXT,
                bot_response TEXT,
                timestamp TEXT,
                language TEXT
            )
        """)
        conn.commit()

setup_database()

# === Save Chat to Database ===
def save_to_db(session_id, user_input, bot_response, language):
    normalized_input = user_input.lower().translate(str.maketrans('', '', re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')))
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chats (session_id, user_input, bot_response, timestamp, language)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, normalized_input, bot_response, timestamp, language))
        conn.commit()

# === Fetch Last Bot Response for Reuse ===
def get_last_message(user_input):
    normalized_input = user_input.lower().translate(str.maketrans('', '', re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')))
    with sqlite3.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT bot_response FROM chats
            WHERE user_input = ?
            ORDER BY ROWID DESC LIMIT 1
        """, (normalized_input,))
        result = cursor.fetchone()
    return result[0] if result else None

# === Detect and Handle Simple Date/Time Questions ===
def detect_datetime_question(user_input):
    text = user_input.lower()
    now = datetime.now()

    checks = {
        ("what time", "current time", "now", "time is it"): f"The current time is {now.strftime('%H:%M:%S')}.",
        ("what's the date", "what is the date", "current date", "today's date", "what date is it", "which date"): f"Today's date is {now.strftime('%Y-%m-%d')}.",
        ("which month", "what month", "current month", "month is this"): f"This month is {now.strftime('%B')}.",
        ("which day", "what day", "day is it", "current day", "today"): f"Today is {now.strftime('%A')}.",
        ("which year", "what year", "current year", "year is this"): f"This year is {now.strftime('%Y')}."
    }

    for keywords, answer in checks.items():
        if any(kw in text for kw in keywords):
            return answer
    return None

# === Validate AI Response ===
def is_valid_response(response: str) -> bool:
    if not response or not response.strip():
        return False
    invalid_keywords = ["something went wrong", "error:", "exception", "traceback",
                        "insufficient_quota", "no longer supported", "invalid request",
                        "you exceeded your quota"]
    return not any(err in response.lower() for err in invalid_keywords)

# === Chatbot Main Logic ===
def chatbot_response(session_id, user_input):
    normalized_input = user_input.lower().translate(str.maketrans('', '', re.escape('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')))

    # Handle datetime Qs
    datetime_answer = detect_datetime_question(user_input)
    if datetime_answer:
        return datetime_answer

    # Return cached reply
    cached = get_last_message(normalized_input)
    if cached:
        save_to_db(session_id, normalized_input, cached, language=None)
        return cached

    # Query OpenAI
    messages = [
    {
        "role": "system",
        "content": (
            "You are a helpful assistant. First, detect the language of the user input. "
            "Then, respond to the input in the same language. "
            "Return the result in the following JSON format:\n\n"
            "{\n"
            '  "language": "<language_code>",\n'
            '  "response": "<your response in the same language>"\n'
            "}\n\n"
            "Use ISO 639-1 language codes (e.g., 'en', 'sv', 'tr', 'fa')."
        )
    },
    {
        "role": "user",
        "content": user_input
    }
]


    try:
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7
        )
        reply = completion.choices[0].message.content
        data = json.loads(reply)
        response = data.get("response", "").strip()
        language = data.get("language", "").lower().strip()
    except Exception as e:
        logging.error(f"Failed to parse OpenAI response: {e}")
        response = reply.strip() if 'reply' in locals() else "Sorry, I don't have an answer right now."
        language = None

    save_to_db(session_id, normalized_input, response, language)
    return response

# === Fetch Chat History for a Session ===
def get_conversation_history(session_id):
    with sqlite3.connect("chatbot.db") as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_input, bot_response, timestamp, language
            FROM chats
            WHERE session_id = ?
            ORDER BY timestamp ASC
        """, (session_id,))
        return cursor.fetchall()

# === Home Page ===
@app.route("/", methods=["GET"])
def home():
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())
    html = """
        <html><head><style>
        body { font-family: Arial; max-width: 600px; margin: auto; padding: 20px; }
        input[type="text"] { width: 80%; padding: 10px; }
        button { padding: 10px 15px; margin-top: 10px; }
        </style></head><body>
        <h2>Chatbot</h2>
        <form action="/chat" method="post">
            <input type="text" name="message" placeholder="Type your message" required>
            <button type="submit">Send</button>
        </form>
        <form action="/history" method="get">
            <button type="submit">Show History</button>
        </form>
        </body></html>
    """
    response = make_response(html)
    response.set_cookie("session_id", session_id, max_age=60 * 60 * 24 * 7)
    return response

# === Chat Handler ===
@app.route("/chat", methods=["POST"])
def chat():
    session_id = request.cookies.get("session_id") or str(uuid.uuid4())
    user_input = request.form.get("message", "")
    if not user_input:
        return redirect("/")

    bot_reply = chatbot_response(session_id, user_input)
    html = f"""
        <html><head><style>
        body {{ font-family: Arial; max-width: 600px; margin: auto; padding: 20px; }}
        .user {{ color: #0066cc; font-weight: bold; }}
        .bot {{ color: #009933; }}
        .chat-box {{ border-bottom: 1px solid #ccc; padding: 10px 0; }}
        button {{ padding: 10px 15px; margin-top: 10px; }}
        </style></head><body>
        <h2>Chatbot</h2>
        <div class="chat-box">
            <div class="user">You: {user_input}</div>
            <div class="bot">Bot: {bot_reply}</div>
        </div>
        <form action="/" method="get"><button type="submit">New Question</button></form>
        <form action="/history" method="get"><button type="submit">Show History</button></form>
        </body></html>
    """
    response = make_response(html)
    response.set_cookie("session_id", session_id, max_age=60 * 60 * 24 * 7)
    return response

# === History Page ===
@app.route("/history", methods=["GET"])
def history():
    session_id = request.cookies.get("session_id")
    if not session_id:
        return redirect("/")

    history = get_conversation_history(session_id)
    history_html = ""
    for user_input, bot_response, timestamp, language in history:
        lang_display = language.upper() if language else "??"
        history_html += f"""
            <div class="chat-box">
                <div><strong>[{timestamp}] [{lang_display}]</strong></div>
                <div class="user">You: {user_input}</div>
                <div class="bot">Bot: {bot_response}</div>
            </div>
        """

    html = f"""
        <html><head><style>
        body {{ font-family: Arial; max-width: 600px; margin: auto; padding: 20px; }}
        .user {{ color: #0066cc; font-weight: bold; }}
        .bot {{ color: #009933; }}
        .chat-box {{ border-bottom: 1px solid #ccc; padding: 10px 0; }}
        button {{ padding: 10px 15px; margin-top: 10px; }}
        </style></head><body>
        <h2>Chat History</h2>
        {history_html}
        <form action="/" method="get"><button type="submit">New Question</button></form>
        </body></html>
    """
    return html

# === Run Server with Debug Support ===
if __name__ == "__main__":
    import debugpy
    debugpy.listen(("0.0.0.0", 5678))
    print("Waiting for debugger connection...")
    app.run(debug=True, use_reloader=False, use_debugger=False)
