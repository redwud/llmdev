# A fix to prevent errors from `from original.graph` when debugging in VS Code
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import uuid
from flask import Flask, render_template, request, make_response, session
from original.graph import get_bot_response, get_messages_list, memory
from dotenv import load_dotenv

load_dotenv(".env")

# Setting up the Flask application
app = Flask(__name__)
app.secret_key = os.environ.get('WISE_SECRET_KEY', 'this_is_a_dummy_secret')  # Secret key for the session


@app.route('/', methods=['GET', 'POST'])
def index():
    # Get the thread_id from the session; if it doesn't exist, generate a new one and save it to the session
    if 'thread_id' not in session:
        session['thread_id'] = str(uuid.uuid4())  # Generate a unique ID for each user

    # Display the initial message on a GET request
    if request.method == 'GET':
        # Clear the memory
        memory.storage.clear()

        # Create the greeting message
        salutation = {
            'class': 'bot-message',
            'text': 'Hi I am Win a chatbot from WISE Bacolod!<br>How may I be of service to you?'
        }
        # Initialize the conversation history
        response = make_response(render_template('index.html', messages=[salutation]))
        return response

    # Get the message from the user
    user_message = request.form['user_message']

    # Get the bot's response (stored in memory)
    get_bot_response(user_message, memory, session['thread_id'])

    # Get the messages from memory
    messages = get_messages_list(memory, session['thread_id'])

    # Return the response
    return make_response(render_template('index.html', messages=messages))


@app.route('/clear', methods=['POST'])
def clear():
    # Remove the thread_id from the session
    session.pop('thread_id', None)

    # Clear the memory
    memory.storage.clear()
    # Initialize the conversation history

    salutation = {
        'class': 'bot-message',
        'text': "Hello again! I've forgotten our last chat, but I'm ready to learn something new.<br>What would you like to discuss?"
    }

    response = make_response(render_template('index.html', messages=[salutation]))
    return response

if __name__ == '__main__':
    app.run(debug=True)
