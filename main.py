from typing import Annotated
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from chat.chat_websocket import websocket_endpoint
from utils.auth import get_current_user, signup_user, login_user
from fastapi import FastAPI, Depends, UploadFile, File, WebSocket
from chat.chat import upload_pdf, get_chat_pdf, get_all_chat_pdf, delete_thread_chat

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount for serving uploaded files
app.mount("/static", StaticFiles(directory="static"), name="static")


# Authentication Routes
@app.post("/signup/")
async def signup(username: str, password: str):
    """API to create a new user account."""
    return signup_user(username, password)


@app.post("/login/")
async def login(username: str, password: str):
    """API to log in an existing user."""
    return login_user(username, password)


# PDF Chat Upload and Retrieval Routes
@app.post("/upload-pdf/", tags=["Chat"])
async def upload_pdf_endpoint(user: Annotated[str, Depends(get_current_user)], file: UploadFile = File(...)):
    """API endpoint to upload a PDF for chat processing."""
    return upload_pdf(user, file)


@app.get("/chat-pdf/", tags=["Chat"])
async def get_chat_pdfs(user: Annotated[str, Depends(get_current_user)]):
    """Retrieve all chat PDFs for a user."""
    return get_chat_pdf(user)


@app.get("/admin/chat-pdf/", tags=["Admin"])
async def get_all_chat_pdfs(user: Annotated[str, Depends(get_current_user)], page: int = 1, page_limit: int = 20, search: str = ""):
    """Retrieve all chat PDFs for admin view with pagination and search."""
    return get_all_chat_pdf(user, page, page_limit, search)


@app.delete("/chat-pdf/{thread_id}/", tags=["Chat"])
async def delete_chat_thread(user: Annotated[str, Depends(get_current_user)], thread_id: str):
    """Mark a chat PDF as deleted for a specific user."""
    return delete_thread_chat(user, thread_id)


# WebSocket Endpoint
@app.websocket("/ws/{thread_id}/")
async def chat_websocket_endpoint(websocket: WebSocket, thread_id: str):
    """WebSocket endpoint for real-time chat."""
    await websocket_endpoint(websocket, thread_id)
