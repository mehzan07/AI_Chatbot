# Creating AI Chatbot setp by step
# Import necessary libraries in chatbot.py:import nltk

from flask import Flask, request, jsonify
import string

# Create the Flask app : Flask is a micro web framework written in Python
app = Flask(__name__)

# Default route to render the form
@app.route('/')
def home():
    return '''
        <form action="/chat" method="post">
            <input type="text" name="message" placeholder="Type your message">
            <button type="submit">Send</button>
        </form>
    '''

# Route for chatbot interaction
@app.route('/chat', methods=['POST'])
def chat():
    # Get the user input from the form
    user_input = request.form.get("message")
    # Generate a response from the chatbot
    response = chatbot_response(user_input)
    # Return the response in the form
    return f'''
        <p><strong>User:</strong> {user_input}</p>
        <p><strong>Chatbot:</strong> {response}</p>
        <a href="/">Go Back</a>
    '''

# Chatbot response logic
def chatbot_response(user_input):
    # Normalize the input by converting to lowercase and removing punctuation
    user_input = user_input.lower().translate(str.maketrans('', '', string.punctuation))
    
    # Define some basic responses
    responses = {
        "hello": "Hi there! How can I help you?",
        "bye": "Goodbye! Have a great day!",
        "what is your name": "my name is chatbot",
        "how are you": "I'm just a program, but I'm here to help you!",
    }
    # Return the matching response or a default message
    return responses.get(user_input, "I'm sorry, I didn't understand that.")

# new development 
# 1-  Expand Responses Using NLP
# Right now, your chatbot relies on exact matches. Improve it with Natural Language Processing (NLP) using the NLTK or spaCy libraries to analyze user input more intelligently.
#Tokenization, stemming, and lemmatization can improve understanding.
# Instead of predefined responses, use similarity matching.
# first you pip install nltk by command: pip install nltk



from nltk.tokenize import word_tokenize

def chatbot_response(user_input):
    tokens = word_tokenize(user_input.lower())  # Tokenizing words
    if "hello" in tokens:
        return "Hi! How can I assist you today?"
    elif "bye" in tokens:
        return "Goodbye! See you soon!"
    else:
        return "I’m sorry, I don’t understand."

# 2- Implement Machine Learning with Chatbot Models
#For more intelligent responses, integrate a machine learning-based chatbot using NLU (Natural Language Understanding) with models like Rasa, Hugging Face Transformers, or GPT.
#  Use a pretrained model from Hugging Face:

from transformers import pipeline

chatbot = pipeline("text-generation", model="microsoft/DialoGPT-medium")

'''while True:
    user_input = input("User: ")
    response = chatbot(user_input)
    print("Chatbot:", response[0]['generated_text']) 
      '''
def chatbot_response(user_input):
    response = chatbot(user_input, max_length=50)
    return response[0]["generated_text"]


# 3- Store Conversations Using a Database
# Enhance the chatbot by saving past conversations for context awareness using SQLite, PostgreSQL, or MongoDB.
# Save previous user chats in SQLite:
import sqlite3

def save_to_db(user_input, bot_response):
    conn = sqlite3.connect("chatbot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO chats (user_input, bot_response) VALUES (?, ?)", (user_input, bot_response))
    conn.commit()
    conn.close()

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
    
    # Ensure save_to_db is defined BEFORE calling it
    save_to_db("Hello!", "Hi there!")

setup_database()




# - 4 Add Intent Recognition Using AI
# Instead of hardcoding responses, classify user messages into intents using TensorFlow or scikit-learn.
# Example:
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB

# Sample intents
training_data = [("hello", "greeting"), ("bye", "farewell"), ("how are you", "small_talk")]
texts, labels = zip(*training_data)

vectorizer = CountVectorizer()
X_train = vectorizer.fit_transform(texts)
clf = MultinomialNB().fit(X_train, labels)

def classify_intent(user_input):
    X_test = vectorizer.transform([user_input])
    return clf.predict(X_test)[0]

# 5-Convert to an API for Scalability
# Instead of handling responses locally, create a REST API that connects to your chatbot from multiple applications.
# Example:
@app.route('/api/chat', methods=['POST'])
def chat_api():
    user_input = request.json.get("message")
    response = chatbot_response(user_input)
    return jsonify({"response": response})




# 6- Add Voice Input & Output
# Make your chatbot voice-enabled using Python’s speech_recognition and pyttsx3.
# Example:
import speech_recognition as sr
import pyttsx3

recognizer = sr.Recognizer()
engine = pyttsx3.init()

def listen_and_respond():
    with sr.Microphone() as source:
        print("Say something...")
        audio = recognizer.listen(source)
        user_input = recognizer.recognize_google(audio)
        response = chatbot_response(user_input)
        engine.say(response)
        engine.runAndWait()

# Now, your chatbot can talk to users!



# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)