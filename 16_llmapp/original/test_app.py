import pytest
from flask import session
from original.app import app
from original.graph import memory, get_messages_list

USER_MESSAGE_1 = "1 plus 2 is?"
USER_MESSAGE_2 = "What is your website?"

@pytest.fixture
def client():
    """
    Creates a Flask test client.
    """
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'your_secret_key'  # Set the secret key for the session
    client = app.test_client()
    with client.session_transaction() as session:
        session.clear()  # Clear and initialize the session
    yield client #NOTE: Why this has to call yield? Still grasping this idiom


def test_index_get_request(client):
    """
    Tests if the initial page is displayed correctly on a GET request.
    """
    response = client.get('/')
    assert response.status_code == 200, "Should return status code 200 for a GET request."
    assert b"<form" in response.data, "HTML should contain a form element."
    assert memory.storage == {}, "Memory should be initialized on a GET request."


def test_index_post_request(client):
    """
    Tests if the bot's response is returned correctly on a POST request.
    """
    with client.session_transaction() as session:
        thread_id = session.get('thread_id')
        assert thread_id is None, "Session should not have a thread_id set initially."

    response = client.post('/', data={'user_message': USER_MESSAGE_1})
    assert response.status_code == 200, "Should return status code 200 for a POST request."
    decoded_data = response.data.decode('utf-8')  # Decode the byte string
    assert "1 plus 2" in decoded_data, "The user's input should be displayed in the HTML."
    assert "3" in decoded_data, "The bot's response should be correctly displayed in the HTML."

    with client.session_transaction() as session:
        thread_id = session.get('thread_id')
        assert thread_id is not None, "Session should have a thread_id set after a POST request."


def test_memory_persistence_with_session(client):
    """
    Tests if memory is persisted per session across multiple POST requests.
    """
    client.post('/', data={'user_message': USER_MESSAGE_1})
    client.post('/', data={'user_message': USER_MESSAGE_2})

    with client.session_transaction() as session:
        thread_id = session.get('thread_id')
        assert thread_id is not None, "Session must have a thread_id set."

    messages = get_messages_list(memory, thread_id)
    assert len(messages) >= 2, "More than two messages should be saved in memory."
    assert any("1 plus 2" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "The first user message should be saved in memory."
    assert any("website" in msg['text'].lower() for msg in messages if msg['class'] == 'user-message'), "The second user message should be saved in memory."


def test_clear_endpoint(client):
    """
    Tests if the /clear endpoint correctly resets the session and memory.
    """
    client.post('/', data={'user_message': USER_MESSAGE_1})

    with client.session_transaction() as session:
        thread_id = session.get('thread_id')
        assert thread_id is not None, "Session should have a thread_id set after a POST request."

    response = client.post('/clear')
    assert response.status_code == 200, "Should return status code 200 for a POST request."
    assert b"<form" in response.data, "HTML should contain a form element."

    with client.session_transaction() as session:
        thread_id = session.get('thread_id')
        assert thread_id is None, "Session should not have a thread_id set after the /clear endpoint."

    # Verify that memory has been cleared
    cleared_messages = memory.get({"configurable": {"thread_id": thread_id}})
    assert cleared_messages is None, "Memory should be cleared after the /clear endpoint."
