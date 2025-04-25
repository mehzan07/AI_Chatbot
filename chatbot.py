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



# Run the Flask app
if __name__ == "__main__":
    app.run(debug=True)