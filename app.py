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

# Caption templates for each language - RE-ADDED
TEMPLATES = {
    "en": {
        "featured": "Featured In This Image:",
        "also_featured": "Also Featured In This Image:",
        "model_wears": "Model wears",
        "model_right": "Model (right) wears",
        "model_left": "Model (left) wears",
        "model_middle": "Model (middle) wears",
        "featured_top": "Featured In Top Image:",
        "top_model": "Top Image: Model wears",
        "talent": "[Talent name] wears",
        "talent_right": "[Talent name] (right) wears",
        "talent_left": "[Talent name] (left) wears",
        "top_talent": "Top Image: [Talent name] wears"
    },
    "fr": {
        "featured": "En vedette sur cette image:",
        "also_featured": "Aussi en vedette sur cette image:",
        "model_wears": "Le modèle porte:",
        "model_right": "Le modèle (à droite) porte:",
        "model_left": "Le modèle (à gauche) porte:",
        "model_middle": "Le modèle (au centre) porte:",
        "featured_top": "En vedette sur l'image du haut:",
        "top_model": "Sur l'image du haut, le modèle porte:",
        "talent": "[Talent name] porte:",
        "talent_right": "[Talent name] (à droite) porte:",
        "talent_left": "[Talent name] (à gauche) porte:",
        "top_talent": "Sur l'image précédente, [Talent name] porte:"
    },
    "jp": {
        "featured": "画像のアイテム：",
        "also_featured": "画像のアイテム：",
        "model_wears": "モデル着用アイテム：",
        "model_right": "モデル (右) ：",
        "model_left": "モデル (左) ：",
        "model_middle": "モデル (中央) ：",
        "featured_top": "冒頭の画像のアイテム：",
        "top_model": "冒頭の画像 モデル着用アイテム：",
        "talent": "[Talent name] 着用アイテム：",
        "talent_right": "[Talent name] (右) ：",
        "talent_left": "[Talent name] (左) ：",
        "top_talent": "冒頭の画像 [Talent name] 着用アイテム："
    },
    "zh": {
        "featured": "本图单品：",
        "also_featured": "本图单品：",
        "model_wears": "模特身着：",
        "model_right": "模特（右）身着：",
        "model_left": "模特（左）身着：",
        "model_middle": "模特（中）身着：",
        "featured_top": "顶图单品：",
        "top_model": "顶图模特身着：",
        "talent": "[Talent name]身着：",
        "talent_right": "[Talent name]（右）身着：",
        "talent_left": "[Talent name]（左）身着：",
        "top_talent": "顶图[Talent name]身着："
    }
}

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

        logging.info(f"Received request to generate caption for URLs: {urls} with template: {template_type}")

        if not urls:
            logging.warning("No URLs provided")
            return jsonify({'error': 'No URLs provided'}), 400

        products_data = [] # Store product info along with translated names
        errors = []

        # --- Step 1: Fetch product data and generate all language URLs --- 
        for url in urls:
            product = None
            try:
                product_id = extract_product_id(url)
                if product_id:
                    logging.info(f"Looking up product ID: {product_id}")
                    # Try integer first
                    product = db.products.find_one({"product_id": int(product_id)})
                    # If not found, try string (just in case)
                    if not product:
                        product = db.products.find_one({"product_id": product_id})

                    if product:
                        logging.info(f"Found product: {product.get('brand')} - {product.get('subcategory')}")
                        product['original_url'] = url
                        # Generate all language URLs
                        product['urls'] = {
                            'en': url, # Assume input is base 'en'
                            'fr': convert_url_to_language(url, 'fr'),
                            'jp': convert_url_to_language(url, 'ja'),
                            'zh': convert_url_to_language(url, 'zh')
                        }
                        products_data.append(product)
                    else:
                        error_msg = f"Product ID {product_id} not found in database"
                        logging.warning(error_msg)
                        errors.append(error_msg)
                else:
                     error_msg = f"Could not extract product ID from URL: {url}"
                     logging.warning(error_msg)
                     errors.append(error_msg)
            except Exception as e:
                error_msg = f"Error processing URL {url}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
        
        if not products_data:
             return jsonify({'error': 'No valid products found for the given URLs', 'errors': errors, 'success': False})

        # --- Step 2: Generate captions for each language using the fetched data --- 
        captions = {}
        # Map language to the category field name
        field_map = {
            "en": "CategoryEN",
            "fr": "CategoryFR",
            "jp": "CategoryJP",
            "zh": "CategoryZH"
        }

        for lang in ['en', 'fr', 'jp', 'zh']:
            try:
                template = TEMPLATES[lang][template_type]
                # Apply talent name replacement if needed
                if talent_name and ('talent' in template_type or 'talent' in template.lower()):
                    if lang == 'fr': template = template.replace('[Nom du talent]', talent_name)
                    elif lang == 'jp': template = template.replace('[タレント名]', talent_name)
                    elif lang == 'zh': template = template.replace('[艺人姓名]', talent_name)
                    else: template = template.replace('[Talent name]', talent_name)
                
                product_links = []
                for product in products_data:
                    # Get translated category name using subcategory_id
                    translated_name = product.get('subcategory', 'Unknown') # Default fallback
                    category_doc = None
                    target_field = field_map.get(lang, "CategoryEN")
                    try:
                        subcategory_id = int(product['subcategory_id'])
                        category_doc = db.categorys.find_one({"id": subcategory_id})
                        if category_doc:
                            if target_field in category_doc and category_doc[target_field]:
                                translated_name = category_doc[target_field]
                            elif "CategoryEN" in category_doc and category_doc["CategoryEN"]:
                                translated_name = category_doc["CategoryEN"]
                                logging.warning(f"[CaptionGen] Lang '{lang}', field '{target_field}' missing for id {subcategory_id}. Using EN: '{translated_name}'")
                            # else: keep original subcategory name as fallback
                        else:
                            logging.warning(f"[CaptionGen] Lang '{lang}', No category doc found for id {subcategory_id}. Using default: '{translated_name}'")
                    except Exception as e:
                         logging.error(f"[CaptionGen] Lang '{lang}', Error looking up category id {product.get('subcategory_id')}: {e}")

                    # Format the link string based on language order
                    link_url = product['urls'].get(lang, product['original_url']) # Use specific lang URL
                    if lang == "fr":
                        product_links.append(f"[{translated_name} {product['brand']}]({link_url})")
                    else: # EN, JP, ZH
                        product_links.append(f"[{product['brand']} {translated_name}]({link_url})")
                
                # Combine links into the final caption string
                if not product_links:
                    captions[lang] = ""
                    continue
                    
                if lang == "jp" or lang == "zh":
                    captions[lang] = f"{template}{'、'.join(product_links)}。"
                else: # EN, FR
                    conjunction = " et " if lang == "fr" else " and "
                    if len(product_links) == 1:
                        captions[lang] = f"{template} {product_links[0]}."
                    else:
                        captions[lang] = f"{template} {', '.join(product_links[:-1])},{conjunction}{product_links[-1]}."
                
                logging.info(f"Generated caption for {lang}: {captions[lang]}")
            except Exception as e:
                error_msg = f"Error generating caption for language {lang}: {str(e)}"
                logging.error(error_msg)
                errors.append(error_msg)
                captions[lang] = "Error generating caption."
        
        return jsonify({
            'captions': captions,
            'errors': errors,
            'success': len(products_data) > 0
        })
    except Exception as e:
        error_msg = f"Unexpected error in /generate route: {str(e)}"
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
