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
import logging

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


# Initialize Hugging Face model: creates a chatbot model that can generate responses based on user input, leveraging DialoGPT’s natural language generation capabilities.
chatbot_model = pipeline("text-generation", model="microsoft/DialoGPT-medium")
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
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    # Select the latest bot response where the user_input matches
    cursor.execute("SELECT bot_response FROM chats WHERE user_input = ? ORDER BY ROWID DESC LIMIT 1", (user_input,))
    last_message = cursor.fetchone()
    conn.close()
    return last_message[0] if last_message else ""

# Fetch factual answers from web search

''' def search_web(query):
    """Search for factual answers using Bing."""
    bing_api_key = "YOUR_REAL_BING_API_KEY"
    url = f"https://api.bing.microsoft.com/v7.0/search?q={query}"
    headers = {
        "Ocp-Apim-Subscription-Key": bing_api_key,
        "Content-Type": "application/json"
    }
    '''
#This is other allternative to search web


import requests
import re

def search_wikipedia(query):
    try:
        # Step 1: Search Wikipedia
        search_api_url = "https://en.wikipedia.org/w/api.php"
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json"
        }

        search_response = requests.get(search_api_url, params=search_params, timeout=10)
        search_response.raise_for_status()
        search_data = search_response.json()

        search_results = search_data.get("query", {}).get("search", [])
        if not search_results:
            return "I couldn't find a relevant Wikipedia article. Please try rephrasing your question."

        top_result_title = search_results[0]["title"]

        # Step 2: Get summary
        summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{top_result_title.replace(' ', '_')}"
        summary_response = requests.get(summary_url, timeout=10)
        summary_response.raise_for_status()
        summary_data = summary_response.json()

        title = summary_data.get("title", "")
        description = summary_data.get("description", "")
        full_extract = summary_data.get("extract", "")

        # Step 3: Get only the first short sentence
        first_sentence = re.split(r'(?<=[.!?])\s+', full_extract.strip())[0]

        # Step 4: Direct capital answer if query includes "capital" or "capital of"
        if "capital" in query.lower():
            capital_map = {
                "France": "Paris",
                "Germany": "Berlin",
                "Italy": "Rome",
                "Spain": "Madrid",
                "India": "New Delhi",
                "Japan": "Tokyo",
                "United States": "Washington, D.C."
            }
            capital = capital_map.get(title, None)
            if capital:
                return f"The capital of {title} is {capital}."
            else:
                return f"{first_sentence}"

        # Otherwise just return short version of the topic
        return f"{first_sentence}"

    except requests.exceptions.RequestException as e:
        return f"Error fetching data from Wikipedia: {e}"

# Improved response generation using AI and web search
def chatbot_response(user_input):
    user_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))  # Normalize text

    # Tokenization for better recognition
    try:
        tokens = word_tokenize(user_input)
    except LookupError:
        tokens = user_input.split()  # Fallback method

    # Retrieve previous chatbot messages for better response context
    last_message = get_last_message(user_input)

    # Handle date-related queries
    if "date" in tokens or "today" in tokens:
        bot_response = f"Today's date is {datetime.now().strftime('%A, %B %d, %Y')}."
    # Handle factual queries using web search
    elif any(word in tokens for word in ["capital", "president", "define", "weather"]):
      bot_response = search_wikipedia(user_input)
    else:
        # AI model generates response dynamically
        ai_response = chatbot_model(f"User: {user_input}\nChatbot (based on previous message '{last_message}'): ", max_length=100)
        bot_response = ai_response[0]["generated_text"].strip()

        # Prevent chatbot from echoing user input directly
        if bot_response.lower() == user_input.lower():
            bot_response = "I'm still learning! Can you ask me in a different way?"

    # Save conversation history
    # we don't save the bot response just now for test 
    # if bot_response != ''
    # save_to_db(user_input, bot_response)
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