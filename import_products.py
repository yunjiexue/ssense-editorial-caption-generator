from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi
import json

# Load environment variables
load_dotenv()

def clean_json_string(json_str):
    # Remove any potential BOM or special characters
    json_str = json_str.strip()
    # Handle any potential trailing commas
    if json_str.endswith(','):
        json_str = json_str[:-1]
    return json_str

try:
    # Connect to MongoDB
    print("Connecting to MongoDB...")
    client = MongoClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
    
    # Use the products database
    db = client['products']
    collection = db['products']
    
    # Path to your data file
    file_path = 'products.txt'  # You'll need to create this file with your data
    
    # Read and import the data
    products = []
    with open(file_path, 'r', encoding='utf-8') as file:
        for line in file:
            try:
                # Clean and parse each line as JSON
                clean_line = clean_json_string(line)
                product = json.loads(clean_line)
                products.append(product)
            except json.JSONDecodeError as e:
                print(f"Error parsing line: {line}")
                print(f"Error details: {e}")
                continue
    
    if products:
        # Insert all products
        result = collection.insert_many(products)
        print(f"Successfully inserted {len(result.inserted_ids)} products")
        
        # Verify the count
        total_docs = collection.count_documents({})
        print(f"Total documents in collection: {total_docs}")
    else:
        print("No products were parsed successfully")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    client.close() 