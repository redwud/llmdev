import pytest
from langchain_openai import OpenAIEmbeddings
from original.graph import (
    get_bot_response,
    get_messages_list,
    memory,
    build_graph,
    define_tools,
    create_index,
)

# Mock test data
USER_MESSAGE_1 = "1 plus 2 is?"
USER_MESSAGE_2 = "What is your website?"
USER_MESSAGE_3 = "How many packages do you have?"
THREAD_ID = "test_thread"


@pytest.fixture
def setup_memory():
    """
    Initializes memory for testing.
    """
    memory.storage.clear()
    return memory


@pytest.fixture
def setup_graph():
    """
    Builds a new graph for testing.
    """
    return build_graph("gpt-4o-mini", memory)


def test_define_tools():
    """
    Tests if the define_tools function correctly defines tools.
    """
    tools = define_tools()
    assert len(tools) > 0, "Tools should be defined correctly."
    assert any(tool.name == "retrieve_wise_bacolod_info" for tool in tools), "The retrieve_wise_bacolod_info tool should be defined."


def test_create_index():
    """
    Tests if the create_index function correctly builds an index.
    """
    persist_directory = "./test_chroma_db"
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

    try:
        index = create_index(persist_directory, embedding_model)
        assert index is not None, "An index should be created."
    except Exception as e:
        pytest.fail(f"An error occurred while creating the index: {e}")


def test_get_bot_response_single_message(setup_memory):
    """
    Tests if the bot can respond to a simple message.
    """
    response = get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    assert isinstance(response, str), "The response should be a string."
    assert "3" in response, "The result of '1 plus 2' should be correctly returned."


def test_get_bot_response_with_rag(setup_memory):
    """
    Tests if the bot can correctly handle Retriever-based questions.
    """
    response = get_bot_response(USER_MESSAGE_3, setup_memory, THREAD_ID)
    assert isinstance(response, str), "The response should be a string."
    assert "package" in response.lower() , "The response should be related to the RAG-based question."


def test_get_bot_response_multiple_messages(setup_memory):
    """
    Tests if multiple messages are processed and saved in memory.
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    get_bot_response(USER_MESSAGE_2, setup_memory, THREAD_ID)
    messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(messages) >= 2, "More than two messages should be saved in memory."
    assert any("1 plus 2" in msg['text'] for msg in messages if msg['class'] == 'user-message'), "The first user message should be saved in memory."
    assert any("website" in msg['text'].lower() for msg in messages if msg['class'] == 'user-message'), "The second user message should be saved in memory."


def test_memory_clear_on_new_session(setup_memory):
    """
    Tests if memory is cleared with a new session.
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    initial_messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(initial_messages) > 0, "The first message may not have been saved in memory."

    setup_memory.storage.clear()
    cleared_messages = setup_memory.get({"configurable": {"thread_id": THREAD_ID}})
    assert cleared_messages is None or 'channel_values' not in cleared_messages, "Memory has not been cleared."

def test_build_graph(setup_memory):
    """
    Tests if the graph is built correctly and can generate a response.
    """
    graph = build_graph("gpt-4o-mini", setup_memory)
    response = graph.invoke(
        {"messages": [("user", USER_MESSAGE_1)]},
        {"configurable": {"thread_id": THREAD_ID}},
        stream_mode="values"
    )
    assert response["messages"][-1].content, "The graph should generate a valid response."

def test_get_messages_list(setup_memory):
    """
    Tests if the list of messages in memory is retrieved correctly.
    """
    get_bot_response(USER_MESSAGE_1, setup_memory, THREAD_ID)
    messages = get_messages_list(setup_memory, THREAD_ID)
    assert len(messages) > 0, "The message list should not be empty after a response."
    assert any(isinstance(msg, dict) for msg in messages), "The message list should be a list of dictionaries."
    assert any(msg['class'] == 'user-message' for msg in messages), "The message list should contain a user message."
    assert any(msg['class'] == 'bot-message' for msg in messages), "The message list should contain a bot response."

# For execution
if __name__ == "__main__":
    pytest.main()
