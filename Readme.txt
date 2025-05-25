# 🧠 AI Chatbot with Language Detection and SQLite History

A simple yet powerful AI-powered chatbot built using **Flask**, **OpenAI's GPT API**, and **SQLite**. This chatbot supports multi-language responses, detects the language of the user input, handles date/time queries directly, and stores chat history per session.

---

## 🚀 Features

- 🌐 **Multi-language Support** using ISO 639-1 codes
- 🕰️ **Built-in Date & Time Handling** without calling OpenAI
- 💬 **Short-Term Memory** with caching for repeated questions
- 🧠 **OpenAI GPT-3.5-Turbo** for conversational intelligence
- 💾 **SQLite Database** for storing chat history
- 🖥️ **Session-based Chat History** and retrieval
- 📦 Lightweight Flask web interface

---

## 🧰 1. Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/chatbot-project.git
cd chatbot-project

2. Create a Virtual Environment (Optional but Recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install Requirements
pip install -r requirements.txt
requirements.txt
flask
openai
Setup OpenAI API Key
Set your OpenAI key as an environment variable before running:

How It Works
The chatbot uses a system prompt to instruct OpenAI to detect the user's language and return the response in the same language in a JSON format.

If a user asks about the date or time, the chatbot answers without calling OpenAI.

Each normalized user input is checked in the SQLite cache before sending to OpenAI.

The conversation is stored in an SQLite database (chatbot.db) with timestamp and language.

Database: SQLite Details
Database file: chatbot.db (auto-created on first run)

Table: chats

Columns: session_id, user_input, bot_response, timestamp, language

Basic SQLite Commands
-- Start SQLite
sqlite3 chatbot.db

-- View all chat history
SELECT * FROM chats;

-- Delete empty language rows
DELETE FROM chats WHERE language IS NULL OR language = '';

-- Exit
.quit


Running the Chatbot
python chatbot.py
Then open your browser and go to: http://127.0.0.1:5000

Example Interaction
You: Where is Tokyo?
Bot: Tokyo is the capital city of Japan.

You: What is the date today?
Bot: Today's date is 2025-05-25.

Development Notes
No duplicate calls to OpenAI for repeated inputs

Input normalization ensures case and punctuation insensitivity

Short-term memory caching and datetime detection are prioritized

Author
Built with ❤️ by Mehrdad Zandi

License
This project is open source and available under the MIT License.










