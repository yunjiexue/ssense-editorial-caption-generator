from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi

# Load environment variables
load_dotenv()

try:
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    
    # Use the products database
    db = client['products']
    collection = db['products']
    
    # Get initial count
    initial_count = collection.count_documents({})
    print(f"Initial document count: {initial_count}")
    
    # Delete all documents
    result = collection.delete_many({})
    
    # Verify deletion
    final_count = collection.count_documents({})
    print(f"Deleted {result.deleted_count} documents")
    print(f"Final document count: {final_count}")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    client.close() 