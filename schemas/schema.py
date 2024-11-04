from bson import ObjectId  # Library for working with BSON data types, specifically ObjectId
from config.database import db  # Importing the database instance from the database configuration
from pymongo import ReturnDocument  # Importing ReturnDocument to control return behavior on updates

def insert_one_schema(data, model):
    """
    Insert a new document into a specified MongoDB collection.

    Parameters:
    - data (dict): The data to be inserted as a dictionary.
    - model (str): The name of the MongoDB collection where the document will be inserted.

    Returns:
    - dict: The inserted document data, or an error message if the operation fails.
    """
    try:
        # Insert the data into the specified collection and retrieve the inserted document's ID
        entry = db[model].insert_one(dict(data))
        # Fetch and return the newly inserted document using its ID
        output = find_one_schema({"_id": entry.inserted_id}, model)
        return output
    except Exception as e:
        # Return an error message if an exception occurs
        return {"detail": str(e), "status": False}

def find_one_schema(data, model):
    """
    Find a single document in a specified MongoDB collection.

    Parameters:
    - data (dict): A dictionary containing the search criteria.
    - model (str): The name of the MongoDB collection to search.

    Returns:
    - dict: The found document data, or an error message if no matching record is found or an error occurs.
    """
    try:
        # Search for a single document matching the criteria
        output = db[model].find_one(data)
        if output is None:
            # Return an error message if no document is found
            return {"detail": "No matching record found", "status": False}
        # Return the document data if found
        return {"data": individual_schema(output), "status": True}
    except Exception as e:
        # Return an error message if an exception occurs
        return {"detail": str(e), "status": False}

def find_many_schema(data, model, sort_by=None, page=None, page_limit=10):
    """
    Find multiple documents in a specified MongoDB collection with optional sorting and pagination.

    Parameters:
    - data (dict): A dictionary containing the search criteria.
    - model (str): The name of the MongoDB collection to search.
    - sort_by (list): Optional; fields by which to sort the results.
    - page (int): Optional; the page number for pagination.
    - page_limit (int): Optional; the number of documents to return per page (default is 10).

    Returns:
    - dict: The list of found documents and total items count, or an error message if an error occurs.
    """
    try:
        # Query the collection for documents matching the criteria
        output = db[model].find(data)
        
        # Apply sorting if specified
        if sort_by is not None:
            output = output.sort(sort_by)
        
        # Implement pagination if a page number is provided
        if page is not None:
            total_items = db[model].count_documents(data)  # Count total matching documents
            output = output.skip((page - 1) * page_limit).limit(page_limit)  # Paginate the results
            return {"data": list_schema(output), "total_items": total_items}  # Return data and count
        
        return {"data": list_schema(output), "status": True}  # Return data if no pagination is applied
    except Exception as e:
        # Return an error message if an exception occurs
        return {"detail": str(e), "status": False}

def find_one_and_update_schema(filter, data, model):
    """
    Find a document and update it in a specified MongoDB collection.

    Parameters:
    - filter (dict): A dictionary containing the search criteria for the document to update.
    - data (dict): The data to update in the document.
    - model (str): The name of the MongoDB collection where the document is located.

    Returns:
    - dict: The updated document data, or an error message if no matching record is found or an error occurs.
    """
    try:
        # Find a document matching the filter and update it
        output = db[model].find_one_and_update(filter, data, return_document=ReturnDocument.AFTER)
        if output is None:
            return {"detail": "No matching record found", "status": False}  # Return error if no document is found
        return {"data": individual_schema(output), "status": True}  # Return the updated document
    except Exception as e:
        # Return an error message if an exception occurs
        return {"detail": str(e), "status": False}

def individual_schema(data):
    """
    Convert individual document data into a standard format, handling BSON ObjectId types.

    Parameters:
    - data (dict): The document data retrieved from the database.

    Returns:
    - dict: The formatted document data with ObjectId converted to string.
    """
    for key, value in data.items():
        if isinstance(value, ObjectId):
            data[key] = str(value)  # Convert ObjectId to string
        if isinstance(value, dict):
            data[key] = individual_schema(value)  # Recursively process nested dictionaries
        if isinstance(value, list):
            data[key] = [individual_schema(item) for item in value]  # Process lists of dictionaries
    return data

def list_schema(data):
    """
    Convert a list of document data into a standard format.

    Parameters:
    - data: An iterable of document data retrieved from the database.

    Returns:
    - list: A list of formatted document data.
    """
    return [individual_schema(item) for item in data]  # Apply individual_schema to each document in the list
