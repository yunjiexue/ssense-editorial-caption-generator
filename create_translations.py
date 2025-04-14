from pymongo import MongoClient
from dotenv import load_dotenv
import os
import certifi

# Load environment variables
load_dotenv()

# Initial translations data for testing
TRANSLATIONS = [
    {
        "subcategory_en": "LOW TOP SNEAKERS",
        "translations": {
            "fr": "BASKETS BASSES",
            "jp": "ローカットスニーカー",
            "zh": "低帮运动鞋"
        }
    },
    {
        "subcategory_en": "HOODIES & ZIPUPS",
        "translations": {
            "fr": "SWEATS À CAPUCHE ET ZIPPÉS",
            "jp": "パーカー＆ジップアップ",
            "zh": "连帽衫和拉链衫"
        }
    },
    {
        "subcategory_en": "T-SHIRTS",
        "translations": {
            "fr": "T-SHIRTS",
            "jp": "Tシャツ",
            "zh": "T恤"
        }
    },
    {
        "subcategory_en": "SHORTS",
        "translations": {
            "fr": "SHORTS",
            "jp": "ショーツ",
            "zh": "短裤"
        }
    }
]

def setup_translations():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = MongoClient(os.getenv('MONGODB_URI'), tlsCAFile=certifi.where())
        db = client[os.getenv('DB_NAME', 'products')]
        
        # Check if translations collection exists
        if 'translations' in db.list_collection_names():
            print("Translations collection already exists. Dropping it...")
            db.translations.drop()
        
        # Create new translations collection
        print("Creating translations collection...")
        db.create_collection('translations')
        
        # Insert translations
        result = db.translations.insert_many(TRANSLATIONS)
        print(f"Successfully inserted {len(result.inserted_ids)} translations")
        
        # Create an index on subcategory_en for faster lookups
        db.translations.create_index("subcategory_en")
        print("Created index on subcategory_en")
        
        # Verify the insertions
        print("\nVerifying inserted translations:")
        for translation in db.translations.find():
            print(f"\nEnglish: {translation['subcategory_en']}")
            print("Translations:")
            for lang, trans in translation['translations'].items():
                print(f"  {lang}: {trans}")
        
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        client.close()

if __name__ == "__main__":
    setup_translations() 