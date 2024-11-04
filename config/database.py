import os  # Standard library for interacting with the operating system
from dotenv import load_dotenv  # Library for loading environment variables from a .env file
from pymongo import MongoClient  # Library for connecting to MongoDB

# Load environment variables from a .env file, overriding existing ones
# This allows sensitive data like database connection strings to be kept secure
load_dotenv(override=True)

# Establish a connection to the MongoDB server using the URI defined in the environment variable
client = MongoClient(os.getenv("DATABASE_URI"))  # Retrieve the MongoDB URI from environment variables

# Access the specified database within the MongoDB server
# The database name is also retrieved from the environment variables
db = client[os.getenv("DATABASE_NAME")]  # Connect to the database specified in the .env file
