from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re
import certifi
import logging
from datetime import datetime
import sys

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# MongoDB setup using environment variables
mongodb_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DB_NAME', 'products')

try:
    # Connect to MongoDB Atlas with SSL certificate verification
    logging.info(f"Attempting to connect to MongoDB at {mongodb_uri}")
    client = MongoClient(mongodb_uri, tlsCAFile=certifi.where())
    db = client[db_name]
    # Test the connection
    client.admin.command('ping')
    logging.info("Successfully connected to MongoDB!")
except Exception as e:
    logging.error(f"Error connecting to MongoDB: {str(e)}")
    raise

def convert_url_to_language(url, target_lang):
    """Convert English (en-us or en-ca) URL to target language URL (e.g., /fr/, /ja/, /zh/)."""
    if target_lang == "en":
        return url

    # Define supported target languages
    supported_langs = ["fr", "ja", "zh"]
    if target_lang not in supported_langs:
        logging.warning(f"Unsupported target language for URL conversion: {target_lang}")
        return url # Return original URL if language not supported

    # Use regex to replace /en-us/ or /en-ca/ with /<target_lang>/
    new_url, count = re.subn(r'/en-(us|ca)/', f'/{target_lang}/', url)

    if count == 0:
        logging.warning(f"Could not find /en-us/ or /en-ca/ pattern in URL: {url}")
        return url # Return original URL if pattern not found

    # Apply French-specific path changes *after* language code change
    if target_lang == "fr":
        new_url = new_url.replace("/product/", "/produit/")
        new_url = new_url.replace("/men/", "/hommes/")
        new_url = new_url.replace("/women/", "/femmes/")
        # Add other French specific replacements if needed

    logging.info(f"Converted URL for {target_lang}: {new_url}")
    return new_url

def extract_product_id(url):
    """Extract product ID from SSENSE URL."""
    pattern = r'/(\d+)$'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def generate_caption(products, template, lang="en"):
    """Generate caption for given products in specified language."""
    if not products:
        return ""

    # Map target language to the field name in the 'categorys' collection
    field_map = {
        "en": "CategoryEN",
        "fr": "CategoryFR",
        "jp": "CategoryJP",
        "zh": "CategoryZH"
    }
    target_field = field_map.get(lang, "CategoryEN") # Default to English field

    # Get translated subcategories for each product using subcategory_id
    for product in products:
        translated_name = product.get('subcategory', 'Unknown Category') # Default fallback
        category_doc = None
        try:
            subcategory_id = int(product['subcategory_id'])
            logging.info(f"[Translation] Looking up category for subcategory_id: {subcategory_id}")
            category_doc = db.categorys.find_one({"id": subcategory_id})

            if category_doc:
                logging.info(f"[Translation] Found category doc: {category_doc}")
                if target_field in category_doc and category_doc[target_field]:
                    translated_name = category_doc[target_field]
                    logging.info(f"[Translation] Using '{target_field}': '{translated_name}'")
                elif "CategoryEN" in category_doc and category_doc["CategoryEN"]:
                    # Fallback to English if target language field is missing
                    translated_name = category_doc["CategoryEN"]
                    logging.warning(f"[Translation] Target field '{target_field}' missing. Falling back to CategoryEN: '{translated_name}'")
                else:
                    # Fallback to original subcategory if English also missing
                    logging.warning(f"[Translation] Target field '{target_field}' and CategoryEN missing. Falling back to original subcategory: '{translated_name}'")
            else:
                logging.warning(f"[Translation] No category document found for subcategory_id: {subcategory_id}. Using original subcategory: '{translated_name}'")

        except (ValueError, TypeError) as e:
            logging.error(f"[Translation] Invalid subcategory_id format: {product.get('subcategory_id')}. Error: {e}. Using original subcategory: '{translated_name}'")
        except Exception as e:
            logging.error(f"[Translation] Error looking up category for subcategory_id {product.get('subcategory_id')}: {e}. Using original subcategory: '{translated_name}'")
        
        product['translated_subcategory'] = translated_name
        # print(f"Final translation for {product.get('subcategory')} in {lang}: {product['translated_subcategory']}") # Old debug print

    # Format the links using the fetched translations
    if lang == "jp" or lang == "zh":
        # Japanese & Chinese specific formatting
        product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
        return f"{template}{'、'.join(product_links)}。"
    else:
        # English and French formatting
        if lang == "fr":
            # French: Category first, then Brand
            product_links = [f"[{p['translated_subcategory']} {p['brand']}]({p['urls'][lang]})" for p in products]
            conjunction = " et "
        else:
            # English: Brand first, then Category
            product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
            conjunction = " and "

        if len(product_links) == 1:
            return f"{template} {product_links[0]}."

        # Use appropriate conjunction for language
        return f"{template} {', '.join(product_links[:-1])},{conjunction}{product_links[-1]}."

def get_product_by_url(url):
    """Get product from database by URL."""
    try:
        # Extract product ID from URL
        product_id = extract_product_id(url)
        if not product_id:
            logging.warning(f"Could not extract product ID from URL: {url}")
            return None
            
        # Try to find product
        product = db.products.find_one({"product_id": int(product_id)})
        if not product:
            logging.warning(f"Product not found in database: ID {product_id}")
            return None
            
        logging.info(f"Found product: {product['brand']} - {product['subcategory']} (ID: {product_id})")
        return product
    except Exception as e:
        logging.error(f"Error finding product for URL {url}: {str(e)}")
        return None

@app.route('/')
def index():
    return render_template('index.html', templates=TEMPLATES)

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.json
        urls = data.get('urls', [])
        template_type = data.get('template', "featured")
        talent_name = data.get('talent_name', '')

        logging.info(f"Received request to generate caption for URLs: {urls}")
        
        if not urls:
            logging.warning("No URLs provided")
            return jsonify({'error': 'No URLs provided'}), 400
        
        products = []
        errors = []
        
        for url in urls:
            try:
                product_id = extract_product_id(url)
                if product_id:
                    logging.info(f"Looking up product ID: {product_id}")
                    # Try to find product using string product_id
                    product = db.products.find_one({"product_id": product_id})
                    
                    # If not found, try with integer product_id
                    if not product:
                        product = db.products.find_one({"product_id": int(product_id)})
                    
                    if product:
                        logging.info(f"Found product: {product.get('brand')} - {product.get('subcategory')}")
                        # Generate URLs for all languages using the *corrected* function
                        product['urls'] = {
                            'en': url, # Assume input is always 'en'
                            'fr': convert_url_to_language(url, 'fr'),
                            'jp': convert_url_to_language(url, 'jp'),
                            'zh': convert_url_to_language(url, 'zh')
                        }
                        products.append(product)
                    else:
                        error_msg = f"Product ID {product_id} not found in database"
                        logging.warning(error_msg)
                        errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error processing URL {url}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)

        # Generate captions in all languages
        captions = {}
        for lang in ['en', 'fr', 'jp', 'zh']:
            try:
                template = TEMPLATES[lang][template_type]
                if talent_name and ('talent' in template_type or 'talent' in template.lower()):
                    if lang == 'fr':
                        template = template.replace('[Nom du talent]', talent_name)
                    elif lang == 'jp':
                        template = template.replace('[タレント名]', talent_name)
                    elif lang == 'zh':
                        template = template.replace('[艺人姓名]', talent_name)
                    else:
                        template = template.replace('[Talent name]', talent_name)
                captions[lang] = generate_caption(products, template, lang)
                logging.info(f"Generated caption for {lang}: {captions[lang]}")
            except Exception as e:
                error_msg = f"Error generating caption for language {lang}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
        
        return jsonify({
            'captions': captions,
            'errors': errors,
            'success': len(products) > 0
        })
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logging.error(error_msg)
        return jsonify({
            'error': error_msg,
            'success': False
        }), 500

if __name__ == '__main__':
    # Use different port for local development
    if os.getenv('FLASK_ENV') == 'development':
        port = 3000
        debug = True
    else:
        # Render configuration
        port = int(os.getenv('PORT', 10000))
        debug = False
    
    app.run(host='0.0.0.0', port=port, debug=debug)
