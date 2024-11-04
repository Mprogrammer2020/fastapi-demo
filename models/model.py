from bson import ObjectId  # Library for working with BSON ObjectId type
from datetime import datetime  # Standard library for handling date and time
from pydantic import BaseModel, ConfigDict, Field  # Pydantic for data validation and settings management

class User(BaseModel):
    """
    User model to represent a user in the system.

    Attributes:
    - id (ObjectId): Unique identifier for the user (automatically generated).
    - username (str): Unique username of the user.
    - email (str): Email address of the user.
    - created_at (datetime): Timestamp when the user was created (default: current UTC time).
    - is_active (bool): Flag indicating if the user account is active (default: True).
    """
    id: ObjectId = Field(default_factory=ObjectId)  # Automatically generate ObjectId for new users
    username: str = Field(..., min_length=3, max_length=50)  # Ensure username is between 3 and 50 characters
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')  # Validate email format with regex
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Set created_at to current time
    is_active: bool = True  # Default active status

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Allow arbitrary types for flexibility

class ChatPDF(BaseModel):
    """
    ChatPDF model to represent a PDF document related to a chat session.

    Attributes:
    - user (ObjectId): Identifier for the user associated with the PDF.
    - file (str): URL or path to the PDF file.
    - status (str): Status of the PDF processing (default: "in_progress", can be "failed" or "completed").
    - is_deleted (bool): Flag indicating if the PDF is deleted (default: False).
    - assistant_id (str): Identifier for the OpenAI assistant associated with the PDF (default: empty).
    - vector_store_id (str): Identifier for the OpenAI vector store associated with the PDF (default: empty).
    - created_at (datetime): Timestamp when the PDF was created (default: current UTC time).
    """
    user: ObjectId  # User identifier
    file: str  # File path or URL of the PDF
    status: str = "in_progress"  # Initial status of the PDF processing
    is_deleted: bool = False  # Flag indicating deletion
    assistant_id: str = ""  # Identifier for the OpenAI assistant
    vector_store_id: str = ""  # Identifier for the OpenAI vector store
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Created timestamp

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Allow arbitrary types

class ChatMessage(BaseModel):
    """
    ChatMessage model to represent a message in a chat session.

    Attributes:
    - chat_pdf (ObjectId): Identifier for the associated ChatPDF.
    - user (ObjectId): Identifier for the user who sent the message.
    - question (str): The question asked by the user.
    - answer (str): The answer content provided by the openai (default: empty string).
    - token_usage (int): Token usage count for processing the answer (default: 0).
    - created_at (datetime): Timestamp when the answer was created (default: current UTC time).
    """
    chat_pdf: ObjectId  # Identifier for the associated ChatPDF
    user: ObjectId  # User identifier
    question: str  # The user's question
    answer: str = ""  # Content of the answer
    token_usage: int = 0  # Count of tokens used for processing
    created_at: datetime = Field(default_factory=datetime.utcnow)  # Created timestamp

    model_config = ConfigDict(arbitrary_types_allowed=True)  # Allow arbitrary types
