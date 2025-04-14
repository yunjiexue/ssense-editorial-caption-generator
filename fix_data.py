from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
import json

# Load environment variables
load_dotenv()

# Sample data to import
data = [
    {
        "product_id": "18516331",
        "product_code": "251892M131008",
        "brand": "Martine Rose",
        "subcategory_id": "131",
        "subcategory": "BELTS & SUSPENDERS"
    },
    {
        "product_id": "17468731",
        "product_code": "251586M214001",
        "brand": "Kijun",
        "subcategory_id": "214",
        "subcategory": "TANK TOPS"
    },
    {
        "product_id": "17490991",
        "product_code": "251209F124003",
        "brand": "Crocs",
        "subcategory_id": "124",
        "subcategory": "FLAT SANDALS"
    }
]

try:
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    
    # Use the products database
    db = client['products']
    collection = db['products']
    
    # Drop existing collection
    collection.drop()
    print("Dropped existing collection")
    
    # Convert string IDs to integers for better querying
    for product in data:
        product['product_id'] = int(product['product_id'])
        product['subcategory_id'] = int(product['subcategory_id'])
    
    # Insert the properly structured data
    result = collection.insert_many(data)
    print(f"Inserted {len(result.inserted_ids)} documents")
    
    # Verify the data
    print("\nVerifying data...")
    sample = collection.find_one({'product_id': 18516331})
    print("Sample document:", sample)
    
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    client.close() 