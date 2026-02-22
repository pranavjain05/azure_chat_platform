from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from azure.cosmos import CosmosClient
from azure.messaging.webpubsubservice import WebPubSubServiceClient

from dotenv import load_dotenv
import os
import uuid
from datetime import datetime

# Load environment variables
load_dotenv()

# -------------------
# Cosmos DB setup
# -------------------
COSMOS_URL = os.getenv("COSMOS_URL")
COSMOS_KEY = os.getenv("COSMOS_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
CONTAINER_NAME = os.getenv("CONTAINER_NAME")

cosmos_client = CosmosClient(COSMOS_URL, COSMOS_KEY)
database = cosmos_client.get_database_client(DATABASE_NAME)
container = database.get_container_client(CONTAINER_NAME)

# -------------------
# Web PubSub setup
# -------------------
WEBPUBSUB_CONNECTION_STRING = os.getenv("WEBPUBSUB_CONNECTION_STRING")
HUB_NAME = os.getenv("HUB_NAME")

webpubsub_client = WebPubSubServiceClient.from_connection_string(
    WEBPUBSUB_CONNECTION_STRING,
    hub=HUB_NAME
)

# -------------------
# FastAPI app
# -------------------
app = FastAPI()

# Serve static folder at /static (NOT root)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Root endpoint serves UI
@app.get("/")
def serve_ui():
    return FileResponse("static/index.html")


# -------------------
# Send message endpoint (FIXED)
# Accept JSON body instead of query params
# -------------------
@app.post("/send_message")
def send_message(data: dict = Body(...)):

    senderId = data["senderId"]
    receiverId = data["receiverId"]
    message = data["message"]

    conversationId = f"{senderId}_{receiverId}"

    item = {
        "id": str(uuid.uuid4()),
        "conversationId": conversationId,
        "senderId": senderId,
        "receiverId": receiverId,
        "message": message,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Store in Cosmos DB
    container.create_item(body=item)

    # Send realtime message via Web PubSub
    webpubsub_client.send_to_all({
        "type": "new_message",
        "data": item
    })

    return {"status": "Message stored", "data": item}


# -------------------
# Get messages
# -------------------
@app.get("/get_messages")
def get_messages(user1: str, user2: str):

    conversationId1 = f"{user1}_{user2}"
    conversationId2 = f"{user2}_{user1}"

    query = f"""
        SELECT * FROM c
        WHERE c.conversationId = '{conversationId1}'
        OR c.conversationId = '{conversationId2}'
        ORDER BY c.timestamp
    """

    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    return {"messages": items}


# -------------------
# Get WebSocket URL (FIXED key name)
# -------------------
@app.get("/get_websocket_url")
def get_websocket_url(userId: str = Query(...)):

    token = webpubsub_client.get_client_access_token(
        user_id=userId
    )

    return {
        "url": token["url"]   # FIXED: frontend expects "url"
    }