import os
from dotenv import load_dotenv
import tiktoken
from langchain_community.document_loaders import DirectoryLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.tools.retriever import create_retriever_tool
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated
from typing_extensions import TypedDict

# Read environment variables
load_dotenv(".env")
os.environ['OPENAI_API_KEY'] = os.environ['API_KEY']

# Model name to be used
MODEL_NAME = "gpt-4o-mini"

# Creating a MemorySaver instance
memory = MemorySaver()

# Initializing variables that hold the graph
graph = None

# ===== State Class Definition  =====
# State class: A dictionary that holds a list of messages
class State(TypedDict):
    messages: Annotated[list, add_messages]

# ===== Building indexes =====
def create_index(persist_directory, embedding_model):
    # Get the path of the current script
    current_script_path = os.path.abspath(__file__)
    # Get the directory where the current script is located
    current_directory = os.path.dirname(current_script_path)

    # Load text files
    loader = DirectoryLoader(f'{current_directory}/data/pdf', glob="./*.pdf",
                             loader_cls=PyPDFLoader)
    documents = loader.load()

    # Split into chunks
    encoding_name = tiktoken.encoding_for_model(MODEL_NAME).name
    text_splitter = CharacterTextSplitter.from_tiktoken_encoder(encoding_name)
    texts = text_splitter.split_documents(documents)

    # Build a new index
    db = Chroma.from_documents(texts, embedding_model, persist_directory=persist_directory)
    return db


def define_tools():
    # Get the path of the current script
    current_script_path = os.path.abspath(__file__)
    # Get the directory where the current script is located
    current_directory = os.path.dirname(current_script_path)

    # Location to save the index
    persist_directory = f'{current_directory}/chroma_db'
    # Embedding model
    embedding_model = OpenAIEmbeddings(model="text-embedding-3-small")

    if os.path.exists(persist_directory):
        try:
            # Restore from storage
            db = Chroma(persist_directory=persist_directory, embedding_function=embedding_model)
            print("Restored existing index.")
        except Exception as e:
            print(f"Failed to restore index: {e}")
            db = create_index(persist_directory, embedding_model)
    else:
        print(f"Creating a new index.")
        db = create_index(persist_directory, embedding_model)

    # Create a Retriever
    retriever = db.as_retriever()

    retriever_tool = create_retriever_tool(
        retriever,
        "retrieve_wise_bacolod_info",
        "Search and return WISE Bacolod related info",
    )

    return [retriever_tool]


# ===== Building the graph =====
def build_graph(model_name, memory):
    """
    Creates a graph instance and adds tool nodes and a chatbot node.
    It creates an executable graph using the model name and memory.
    """
    # Create an instance of the graph
    graph_builder = StateGraph(State)

    # Create a tool node
    tools = define_tools()
    tool_node = ToolNode(tools)
    graph_builder.add_node("tools", tool_node)

    # Create a chatbot node
    llm = ChatOpenAI( model_name=model_name )

    # Bind the tool
    llm_with_tools = llm.bind_tools(tools)

    # Define how the chatbot runs
    def chatbot(state: State):
        return {"messages": [llm_with_tools.invoke(state["messages"])]}

    graph_builder.add_node("chatbot", chatbot)

    # Create an executable graph
    graph_builder.add_conditional_edges( "chatbot", tools_condition )
    graph_builder.add_edge("tools", "chatbot")
    graph_builder.set_entry_point("chatbot")

    return graph_builder.compile(checkpointer=memory)


# ===== Function to run the graph =====
def stream_graph_updates(graph: StateGraph, user_message: str, thread_id):
    """
    Runs the graph based on the user's message and streams the chatbot's response.
    """
    # Bind the system message to the LLM
    CS_SPECIALIST = """You are **Win**, the official Customer Support Specialist chatbot for **WISE Bacolod**. You are the **sole voice and representative** of this institution. When asked about 'your' or 'my' website, contact, or location, you **MUST** answer with the official information for WISE Bacolod, which is provided in your knowledge base. Always maintain a friendly and professional tone. Do not mention that you are a chatbot or AI."""

    config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": "default"}}

    response = graph.invoke(
        {"messages": [
            SystemMessage(content=CS_SPECIALIST),
            HumanMessage(content=user_message)
        ]},
        config=config
    )

    return response["messages"][-1].content

# ===== Function to return a response =====
def get_bot_response(user_message, memory, thread_id):
    """
    Gets a bot response based on the user's message.
    If it's the first time, a new graph is created.
    """
    global graph
    # If the graph hasn't been created yet, create a new one
    if graph is None:
        graph = build_graph(MODEL_NAME, memory)

    # Run the graph to get the bot's response
    return stream_graph_updates(graph, user_message, thread_id)

# ===== Function to get the list of messages =====
def get_messages_list(memory, thread_id):
    """
    Gets the list of messages from memory and categorizes them into user and bot messages.
    """
    messages = []
    # Get messages from memory
    memories = memory.get({"configurable": {"thread_id": thread_id}})['channel_values']['messages']
    for message in memories:
        if isinstance(message, HumanMessage):
            # Message from the user
            messages.append({'class': 'user-message', 'text': message.content.replace('\n', '<br>')})
        elif isinstance(message, AIMessage) and message.content != "":
            # Message from the bot (final answer)
            messages.append({'class': 'bot-message', 'text': message.content.replace('\n', '<br>')})
    return messages
