from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
import json

# Load environment variables
load_dotenv()

try:
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    
    # Use the products database
    db = client['products']
    collection = db['products']
    
    # Get total count of documents
    total_docs = collection.count_documents({})
    print(f"\nTotal documents in collection: {total_docs}")
    
    # Get a sample document
    print("\nFirst document in collection:")
    first_doc = collection.find_one()
    print(json.dumps(first_doc, indent=2, default=str))
    
    # List all keys in the document
    if first_doc:
        print("\nDocument keys:")
        print(list(first_doc.keys()))
    
    # Try to find a specific product
    test_id = "17026751"
    print(f"\nTrying to find product with ID {test_id}")
    product = collection.find_one({"product_id": test_id})
    print(f"Found by string ID: {product}")
    
    # Try alternative ways to find the product
    product = collection.find_one({"product_id": int(test_id)})
    print(f"Found by integer ID: {product}")
    
    # Show a few sample documents
    print("\nSample of documents in collection:")
    for doc in collection.find().limit(3):
        print("\nDocument:")
        print(json.dumps(doc, indent=2, default=str))

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    client.close() 