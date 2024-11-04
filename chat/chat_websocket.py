import os
import json
import asyncio
from bson import ObjectId
from models.model import ChatMessage
from typing_extensions import override
from fastapi import WebSocket, WebSocketDisconnect
from openai import AsyncOpenAI, AsyncAssistantEventHandler
from schemas.schema import find_one_schema, find_one_and_update_schema, find_many_schema, insert_one_schema

class PDFStreamHandler(AsyncAssistantEventHandler):
    """
    Custom event handler for handling PDF chat message streaming via WebSocket.
    
    Attributes:
    - websocket (WebSocket): WebSocket connection to communicate with the client.
    - client (AsyncOpenAI): Asynchronous OpenAI client for generating chat responses.
    - chat_thread: Current chat thread linked to the PDF.
    - chat_msg: Chat message identifier for tracking and updating messages in the database.
    """
    def __init__(self, websocket: WebSocket, client: AsyncOpenAI, chat_thread, chat_msg):
        self.websocket = websocket
        self.client = client
        self.chat_thread = chat_thread
        self.chat_msg = chat_msg
        super().__init__()

    async def save_chat_message(self, message):
        """
        Save or update the chat message content in the database.

        Parameters:
        - message (str): The message content to be saved.
        
        Returns:
        - dict: Updated chat message record from the database.
        """
        return find_one_and_update_schema(
            {"_id": ObjectId(self.chat_msg)},
            {"$set": {"message": message}},
            "chat_message"
        )

    @override
    async def on_message_delta(self, delta, snapshot) -> None:
        """
        Handle streaming of partial message content in real-time to WebSocket.
        
        Parameters:
        - delta: Partial message data from OpenAI response.
        - snapshot: Snapshot of the current message including annotations and text.
        """
        message_content = snapshot.content[0].text
        annotations = message_content.annotations
        for annotation in annotations:
            message_content.value = message_content.value.replace(annotation.text, "")
        await self.websocket.send_text(json.dumps({"message": message_content.value, "stream": True}))
        await asyncio.sleep(0.001)  # Slight delay for smooth streaming

    @override
    async def on_message_done(self, message) -> None:
        """
        Handle the completion of the response message, saving it in the database and sending to the client.
        
        Parameters:
        - message: Final message content received from OpenAI.
        """
        message_content = message.content[0].text
        annotations = message_content.annotations
        for annotation in annotations:
            message_content.value = message_content.value.replace(annotation.text, "")
        
        # Save completed message in chat thread
        await self.client.beta.threads.messages.create(
            thread_id=self.chat_thread.id,
            role="assistant",
            content=message_content.value
        )
        
        # Store the message in the database
        await self.save_chat_message(message_content.value)
        await asyncio.sleep(0.001)
        
        # Send the final message to the client
        await self.websocket.send_text(json.dumps({"message": message_content.value, "stream": False}))


async def websocket_endpoint(websocket: WebSocket, thread_id: str):
    """
    WebSocket endpoint for streaming chat responses with OpenAI assistant.

    Parameters:
    - websocket (WebSocket): WebSocket connection to interact with the client.
    - thread_id (str): ID of the chat PDF thread for the specific session.
    """
    await websocket.accept()
    try:
        # Fetch the chat PDF thread details
        chat_pdf = find_one_schema({"_id": ObjectId(thread_id)}, "chat_pdf")
        if not chat_pdf["status"]:
            return await websocket.close(reason="Thread not found")

        chat_pdf = chat_pdf["data"]

        # Initialize OpenAI client
        client = AsyncOpenAI()

        # Load chat system prompt
        CHAT_SYSTEM_PROMPT = find_many_schema({}, "ai_prompt")
        if CHAT_SYSTEM_PROMPT["data"]:
            CHAT_SYSTEM_PROMPT = CHAT_SYSTEM_PROMPT["data"][0]["chat_prompt"]
        else:
            CHAT_SYSTEM_PROMPT = os.getenv("DEFAULT_CHAT_SYSTEM_PROMPT")

        # Retrieve previous messages for context in the current chat thread
        pre_messages = [{'role': 'user', 'content': CHAT_SYSTEM_PROMPT}]
        chat_message = find_many_schema(
            {"chat_pdf": ObjectId(thread_id), "message": {"$ne": ""}}, 
            "chat_message", 
            {"created_at": -1}
        )["data"][:10][::-1]  # Limit to last 10 messages
        
        for message in chat_message:
            pre_messages.append({"role": "user", "content": message["question"]})
            pre_messages.append({"role": "assistant", "content": message["message"]})

        # Create a new chat thread for handling the session
        chat_thread = await client.beta.threads.create(
            messages=pre_messages,
            tool_resources={"file_search": {"vector_store_ids": [chat_pdf['vector_store_id']]}}
        )

        # WebSocket message loop
        while True:
            data = await websocket.receive_text()
            data = json.loads(data)

            # Fetch the user information
            user = find_one_schema({"_id": ObjectId(chat_pdf["user"])}, "users")
            user = user["data"]

            # Check user credits before proceeding
            if user.get("total_credits", 0) <= 500:
                await websocket.send_text(json.dumps({"detail": "Insufficient credits. Please top up and try again.", "stream": False}))
                continue

            # Send user message to OpenAI chat thread
            await client.beta.threads.messages.create(
                thread_id=chat_thread.id,
                role="user",
                content=data["message"]
            )

            # Insert new message in database
            new_chat_message = ChatMessage(
                chat_pdf=ObjectId(thread_id), 
                user=ObjectId(user['_id']), 
                question=data["message"]
            )
            new_chat_message = insert_one_schema(new_chat_message, "chat_message")["data"]

            # Stream assistant response
            async with client.beta.threads.runs.stream(
                instructions=CHAT_SYSTEM_PROMPT,
                thread_id=chat_thread.id,
                assistant_id=chat_pdf['assistant_id'],
                temperature=0,
                event_handler=PDFStreamHandler(websocket, client, chat_thread, new_chat_message["_id"])
            ) as stream:
                try:
                    await stream.until_done()

                    # Fetch final run result for token usage and status
                    run = await stream.get_final_run()

                    # Handle errors or rate limits in response
                    if run.status == "failed":
                        if run.last_error.code == "rate_limit_exceeded":
                            await websocket.send_text(json.dumps({"detail": "Contact admin as there are insufficient tokens in main account.", "stream": False}))
                        else:
                            await websocket.send_text(json.dumps({"detail": run.last_error.message, "stream": False}))
                        continue

                    # Update token usage based on assistant response
                    token_usage = run.usage.total_tokens

                    # Update chat message with token usage data
                    updated_data = find_one_and_update_schema(
                        {"_id": ObjectId(new_chat_message["_id"])},
                        {"$set": {"token_usage": token_usage}},
                        "chat_message"
                    )

                    if not updated_data["data"]["message"]:
                        await websocket.send_text(json.dumps({"message": "No relevant information found. Please try rephrasing your query.", "stream": False}))

                    # Deduct tokens from user's total credits
                    find_one_and_update_schema(
                        {"_id": ObjectId(user["_id"])},
                        {"$set": {"total_credits": user["total_credits"] - min(token_usage, user["total_credits"])}},
                        "users"
                    )

                    await websocket.send_text(json.dumps({"token_usage": token_usage, "stream": False}))

                except Exception:
                    await websocket.send_text(json.dumps({"stream": False}))

    except WebSocketDisconnect:
        pass

    except Exception as e:
        await websocket.send_text(json.dumps({"detail": str(e), "stream": False}))
