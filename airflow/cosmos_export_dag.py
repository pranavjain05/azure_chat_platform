from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime
from azure.cosmos import CosmosClient
from azure.storage.blob import BlobServiceClient

import json
import uuid
import os

# Config
COSMOS_ENDPOINT = 
COSMOS_KEY = 
DATABASE_NAME = 
CONTAINER_NAME = 

STORAGE_CONNECTION_STRING = 
BLOB_CONTAINER = 

STATE_FILE = "/tmp/last_export_time.txt"


# -------------------------
# State helpers
# -------------------------

def get_last_export_time():

    if not os.path.exists(STATE_FILE):
        return "1970-01-01T00:00:00"

    with open(STATE_FILE, "r") as f:
        return f.read().strip()


def save_last_export_time(timestamp):

    with open(STATE_FILE, "w") as f:
        f.write(timestamp)

    print(f"Updated state to {timestamp}")


# -------------------------
# Task 1: Fetch new messages
# -------------------------

def fetch_new_messages(**context):

    last_time = get_last_export_time()

    print(f"Last export time: {last_time}")

    client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(CONTAINER_NAME)

    query = f"""
        SELECT * FROM c
        WHERE c.timestamp > '{last_time}'
        ORDER BY c.timestamp
    """

    items = list(container.query_items(
        query=query,
        enable_cross_partition_query=True
    ))

    print(f"Fetched {len(items)} new messages")

    # Return items via XCom
    return items


# -------------------------
# Task 2: Upload and update state
# -------------------------

def upload_and_update_state(**context):

    items = context["ti"].xcom_pull(
        task_ids="fetch_new_messages"
    )

    if not items:
        print("No new messages")
        return

    blob_service = BlobServiceClient.from_connection_string(
        STORAGE_CONNECTION_STRING
    )

    container_client = blob_service.get_container_client(
        BLOB_CONTAINER
    )

    blob_name = f"chat_incremental_{uuid.uuid4()}.json"

    container_client.upload_blob(
        name=blob_name,
        data=json.dumps(items, indent=4),
        overwrite=True
    )

    print(f"Uploaded {blob_name}")

    # Update state
    latest_timestamp = max(item["timestamp"] for item in items)

    save_last_export_time(latest_timestamp)


# -------------------------
# DAG definition
# -------------------------

with DAG(
    dag_id="cosmos_incremental_export_dag",
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False
) as dag:

    fetch_task = PythonOperator(
        task_id="fetch_new_messages",
        python_callable=fetch_new_messages
    )

    upload_task = PythonOperator(
        task_id="upload_and_update_state",
        python_callable=upload_and_update_state
    )

    fetch_task >> upload_task