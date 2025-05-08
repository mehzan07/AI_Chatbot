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

# with Auto Capital Detection for all counytries. and adding more queston like  who is the president
def search_wikipedia(query):
    import re

    # Clean and prepare query
    user_query = query.lower().strip()
    filtered_query = user_query.replace("what is ", "").replace("who is ", "").replace("tell me about ", "").strip()
    formatted_query = filtered_query.replace(" ", "_")

    # If user asks for capital, population, president, currency, etc.
    fact_type = None
    if "capital of" in user_query:
        fact_type = "capital"
    elif "population of" in user_query:
        fact_type = "population"
    elif "president of" in user_query:
        fact_type = "leader"
    elif "currency of" in user_query:
        fact_type = "currency"

    # Try to extract country name
    country_match = re.search(r"of ([a-zA-Z ]+)", user_query)
    country_name = country_match.group(1).strip() if country_match else filtered_query

    if fact_type:
        try:
            # Query Wikidata API for structured fact
            wikidata_url = "https://www.wikidata.org/w/api.php"
            params = {
                "action": "wbsearchentities",
                "search": country_name,
                "language": "en",
                "format": "json",
                "type": "item"
            }
            resp = requests.get(wikidata_url, params=params, timeout=10)
            entity_results = resp.json().get("search", [])
            if not entity_results:
                return f"Could not find country data for '{country_name}'."

            qid = entity_results[0]["id"]

            # Property IDs for Wikidata
            property_ids = {
                "capital": "P36",
                "population": "P1082",
                "leader": "P35",
                "currency": "P38"
            }
            prop_id = property_ids.get(fact_type)
            claims_url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
            claims_resp = requests.get(claims_url, timeout=10)
            entity_data = claims_resp.json()
            claims = entity_data["entities"][qid]["claims"]

            if prop_id in claims:
                mainsnak = claims[prop_id][0]["mainsnak"]
                datavalue = mainsnak.get("datavalue", {})
                if fact_type == "population":
                    amount = datavalue.get("value", {}).get("amount", "")
                    return f"The population of {country_name.title()} is approximately {int(float(amount)):,}."
                elif fact_type == "currency":
                    currency_id = datavalue.get("value", {}).get("id", "")
                    label_resp = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{currency_id}.json", timeout=10)
                    label_data = label_resp.json()
                    label = label_data["entities"][currency_id]["labels"]["en"]["value"]
                    return f"The currency of {country_name.title()} is the {label}."
                else:
                    linked_id = datavalue.get("value", {}).get("id", "")
                    label_resp = requests.get(f"https://www.wikidata.org/wiki/Special:EntityData/{linked_id}.json", timeout=10)
                    label_data = label_resp.json()
                    label = label_data["entities"][linked_id]["labels"]["en"]["value"]
                    if fact_type == "capital":
                        return f"The capital of {country_name.title()} is {label}."
                    elif fact_type == "leader":
                        return f"The president of {country_name.title()} is {label}."
            else:
                return f"Could not find {fact_type} information for {country_name.title()}."

        except Exception as e:
            return f"Error retrieving factual information: {e}"

    # Fallback: summary from Wikipedia for general questions
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{formatted_query}"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        if response.status_code == 200:
            data = response.json()
            title = data.get("title", "Unknown title")
            description = data.get("description", "No description available")
            summary = data.get("extract", "No summary found.")

            # Optional: shorten summary to 1 sentence
            short_summary = summary.split(".")[0] + "."

            return f"**{title}** - {description}\n{short_summary}"

        elif response.status_code == 404:
            return "Wikipedia page not found. Try asking differently."

        else:
            return f"Error fetching Wikipedia data: {response.status_code}"

    except requests.exceptions.RequestException as e:
        return f"Error fetching data: {e}"




def chatbot_response(user_input):
    user_input_clean = user_input.lower().translate(str.maketrans('', '', string.punctuation))  # Normalize text

    # Tokenization
    try:
        tokens = word_tokenize(user_input_clean)
    except LookupError:
        tokens = user_input_clean.split()

    last_message = get_last_message(user_input_clean)

    # Handle date-related queries
    if "date" in tokens or "today" in tokens:
        bot_response = f"Today's date is {datetime.now().strftime('%A, %B %d, %Y')}."
    
    # Handle factual queries using search_wikipedia
    elif any(word in tokens for word in ["capital", "president", "population", "currency", "define", "what", "who"]):
        bot_response = search_wikipedia(user_input)
    
    else:
        # Generate AI-based response
        ai_response = chatbot_model(
            f"User: {user_input}\nChatbot (based on previous message '{last_message}'): ", 
            max_length=100
        )
        bot_response = ai_response[0]["generated_text"].strip()

        # Prevent simple echoes
        if bot_response.lower() == user_input_clean:
            bot_response = "I'm still learning! Can you ask that another way?"

    # ✅ Basic quality check before saving this is base on oly a few words
    # This checks if the bot response contains specific keywords that indicate it's a factual answer.
    # If it does, it saves the user input and bot response to the database.
    # This is a simple heuristic and can be improved with more sophisticated checks.
    keywords_to_save = ["the capital of", "is the president", "the population of", "the currency of"]
    if any(phrase in bot_response.lower() for phrase in keywords_to_save):
        save_to_db(user_input, bot_response)

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