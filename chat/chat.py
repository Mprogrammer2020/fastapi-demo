import os
import uuid
import shutil
import traceback
from bson import ObjectId
from openai import OpenAI
from dotenv import load_dotenv
from models.model import ChatPDF
from fastapi import HTTPException, UploadFile
from schemas.schema import insert_one_schema, list_schema, find_one_and_update_schema

# Load environment variables from .env file
load_dotenv()

# PDF Chat Upload and Retrieval Functions

async def upload_pdf(user: dict, file: UploadFile):
    """
    Upload a PDF for chat processing and link it to the current user.

    Parameters:
    - user (dict): Current authenticated user data.
    - file (UploadFile): PDF file to upload and process.

    Raises:
    - HTTPException: If file type is not PDF or processing fails.

    Returns:
    - dict: Response with success status and details.
    """
    try:
        # Validate that the uploaded file is a PDF
        if file.content_type != "application/pdf":
            raise HTTPException(status_code=400, detail="Only PDF file is allowed")

        # Save the PDF file locally in the static directory
        file_path = os.path.join("static", f"{file.filename.split('.')[0]}-{uuid.uuid4()}.pdf")
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Initialize OpenAI client and create an assistant
        client = OpenAI()
        assistant = client.beta.assistants.create(
            name="Propti Assistant",
            instructions=os.getenv('OPENAI_INSTRUCTIONS'),
            model=os.getenv('OPENAI_MODEL'),
            tools=[{"type": "file_search"}]
        )

        # Create a vector store and upload the file to it
        vector_store = client.beta.vector_stores.create(name="rag-store")
        file_stream = open(file_path, "rb")
        file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
            vector_store_id=vector_store.id, files=[file_stream]
        )

        # Link the assistant to the created vector store
        assistant = client.beta.assistants.update(
            assistant_id=assistant.id,
            tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}
        )

        # Save PDF details to the database
        data = ChatPDF(
            user=ObjectId(user['_id']),
            file=file_path,
            assistant_id=assistant.id,
            vector_store_id=vector_store.id,
            status=file_batch.status,
        )
        output = insert_one_schema(data, "chat_pdf")

        # Check if file processing was successful
        if not output["status"] or output["data"]["status"] != "completed":
            raise HTTPException(status_code=400, detail="Unable to read files possibly due to issues like corruption or unsupported formats.")

        return output

    except Exception as e:
        print(traceback.format_exc())
        raise HTTPException(status_code=400, detail=str(e))


def get_chat_pdf(user: dict):
    """
    Retrieve all chat PDFs linked to the current user.

    Parameters:
    - user (dict): Current authenticated user data.

    Returns:
    - list: List of chat PDFs associated with the user.
    """
    pipeline = [
        {"$match": {"user": ObjectId(user['_id']), "is_deleted": False}},
        {"$lookup": {"from": "chat_message", "localField": "_id", "foreignField": "chat_pdf", "as": "chat_messages"}},
        {"$addFields": {"chat_message_count": {"$size": "$chat_messages"}}},
        {"$match": {"chat_message_count": {"$gt": 0}}},
        {"$sort": {"created_at": -1}},
        {"$project": {"chat_messages": 0, "chat_message_count": 0}}
    ]

    output = list_schema(db["chat_pdf"].aggregate(pipeline))
    return output


def get_all_chat_pdf(user: dict, page: int = 1, page_limit: int = 20, search: str = ""):
    """
    Retrieve all chat PDFs with pagination and optional search filter.

    Parameters:
    - user (dict): Current authenticated user data.
    - page (int): Page number for pagination.
    - page_limit (int): Number of items per page.
    - search (str): Search query to filter results.

    Returns:
    - dict: Paginated list of chat PDFs with total item count.
    """

    # Build query filter based on search criteria
    match_stage = {"$match": {"is_deleted": False}}
    if search:
        match_stage["$match"].update({
            "$or": [
                {"user.name": {"$regex": search, "$options": "i"}},
                {"user.last_name": {"$regex": search, "$options": "i"}},
                {"user.email": {"$regex": search, "$options": "i"}},
                {"name": {"$regex": search, "$options": "i"}}
            ]
        })

    # Run aggregation pipeline to retrieve and paginate results
    output = db["chat_pdf"].aggregate([
        {"$lookup": {"from": "users", "localField": "user", "foreignField": "_id", "as": "user"}},
        {"$unwind": "$user"},
        match_stage,
        {"$lookup": {"from": "chat_message", "localField": "_id", "foreignField": "chat_pdf", "as": "chat_messages"}},
        {"$addFields": {"chat_message_count": {"$size": "$chat_messages"}}},
        {"$facet": {
            "total": [{"$match": {"chat_message_count": {"$gt": 0}}}, {"$count": "count"}],
            "data": [
                {"$match": {"chat_message_count": {"$gt": 0}}},
                {"$sort": {"created_at": -1}},
                {"$skip": (page - 1) * page_limit},
                {"$limit": page_limit},
                {"$project": {"chat_messages": 0, "chat_message_count": 0}}
            ]
        }}
    ])

    output = list_schema(output)
    total_items = output[0]["total"][0]["count"] if output[0]["total"] else 0
    data = output[0]["data"]

    return {"data": data, "total_items": total_items}


def delete_thread_chat(user: dict, thread_id: str):
    """
    Mark a specific chat PDF thread as deleted for the user.

    Parameters:
    - user (dict): Current authenticated user data.
    - thread_id (str): ID of the chat PDF thread to delete.

    Returns:
    - dict: Result of the deletion operation.
    """
    output = find_one_and_update_schema({"_id": ObjectId(thread_id)}, {"$set": {"is_deleted": True}}, "chat_pdf")
    return output["data"]
