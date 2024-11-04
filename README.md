# PDF Chat Assistant

## Overview

The PDF Chat Assistant is a web application that enables users to sign up, log in, upload PDF documents, and engage in a chat interface to ask questions related to the content of those documents. Powered by OpenAI, this application provides intelligent responses based on the uploaded PDF content.

## Features

- **User Authentication**: Secure sign-up and login functionality.
- **PDF Upload**: Users can upload PDF documents for chat processing.
- **Interactive Chat**: Ask questions and receive answers related to the uploaded PDF content.
- **Data Storage**: Utilizes MongoDB to store user data and uploaded PDFs.
- **AI Integration**: Leverages OpenAI to provide intelligent responses based on the PDF content.

## Technology Stack

- **Backend**: FastAPI
- **Database**: MongoDB
- **AI**: OpenAI
- **Environment Variables**: Managed using `dotenv` for configuration

## Getting Started

To get started with the PDF Chat Assistant, follow these steps:

1. **Clone the Repository**:
https://github.com/Mprogrammer2020/fastapi-demo.git

2. **Install Dependencies**:
Make sure you have Python and pip installed, then run:
pip install -r requirements.txt

3. **Create a .env File**:
In the root directory, create a `.env` file and add the following environment variables:

DATABASE_URI=your_mongodb_uri 
DATABASE_NAME=your_database_name 
JWT_SECRET_KEY=your_jwt_secret_key 
OPENAI_MODEL=your_openai_model 
OPENAI_API_KEY=your_openai_api_key 
DEFAULT_CHAT_SYSTEM_PROMPT=your_default_chat_prompt 
OPENAI_INSTRUCTIONS=your_openai_instructions

4. **Run the Application**:
Start the FastAPI application with:
uvicorn main:app --reload