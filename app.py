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

def get_translated_subcategory(subcategory_en, target_lang):
    """Get translated subcategory from categorys collection."""
    try:
        logging.info(f"[Translation] Attempting to translate '{subcategory_en}' to {target_lang}")
        # Map target language to field name
        field_map = {
            "en": "CategoryEN",
            "fr": "CategoryFR",
            "jp": "CategoryJP",
            "zh": "CategoryZH"
        }

        field_name = field_map.get(target_lang)
        if not field_name:
            logging.warning(f"[Translation] Unsupported language: {target_lang}")
            return subcategory_en

        # Try exact match on category first (more reliable than ID)
        exact_query = {"category": subcategory_en}
        logging.info(f"[Translation] Trying exact match query: {exact_query}")
        translation = db.categorys.find_one(exact_query)
        if translation and field_name in translation:
            translated_value = translation[field_name]
            logging.info(f"[Translation] Found exact match: '{translated_value}'")
            return translated_value
        else:
             logging.info(f"[Translation] No exact match found or field '{field_name}' missing in result: {translation}")

        # If no exact match, try case-insensitive search
        insensitive_query = {"category": {"$regex": f"^{re.escape(subcategory_en)}$", "$options": "i"}}
        logging.info(f"[Translation] Trying case-insensitive query: {insensitive_query}")
        translation = db.categorys.find_one(insensitive_query)
        if translation and field_name in translation:
            translated_value = translation[field_name]
            logging.info(f"[Translation] Found case-insensitive match: '{translated_value}'")
            return translated_value
        else:
            logging.info(f"[Translation] No case-insensitive match found or field '{field_name}' missing in result: {translation}")

        # Fallback if no translation found
        logging.warning(f"[Translation] No translation found for '{subcategory_en}' in {target_lang}. Falling back to English.")
        return subcategory_en
    except Exception as e:
        logging.error(f"[Translation] Error looking up translation for '{subcategory_en}' to {target_lang}: {e}")
        return subcategory_en # Fallback on error

# Caption templates for each language - UPDATED
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
    """Convert English (en-us or en-ca) URL to target language URL."""
    if target_lang == "en":
        return url

    target_locales = {
        "fr": "fr-ca",
        "jp": "ja-jp",
        "zh": "zh-cn"
    }

    target_locale = target_locales.get(target_lang)
    if not target_locale:
        logging.warning(f"Unsupported target language for URL conversion: {target_lang}")
        return url # Return original URL if language not supported

    # Use regex to replace /en-us/ or /en-ca/
    new_url, count = re.subn(r'/en-(us|ca)/', f'/{target_locale}/', url)

    if count == 0:
        logging.warning(f"Could not find /en-us/ or /en-ca/ pattern in URL: {url}")
        return url # Return original URL if pattern not found

    # Apply French-specific path changes *after* locale change
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
    
    # Get translated subcategories for each product
    for product in products:
        if lang == "en":
            # For English, look up CategoryEN and use it exactly as stored
            category_doc = db.categorys.find_one({"id": int(product['subcategory_id'])})
            if category_doc and 'CategoryEN' in category_doc:
                # Use CategoryEN exactly as it appears in the database (singular form)
                product['translated_subcategory'] = category_doc['CategoryEN']
                print(f"Found CategoryEN for ID {product['subcategory_id']}: {category_doc['CategoryEN']}")
            else:
                print(f"No CategoryEN found for ID {product['subcategory_id']}, using fallback")
                # Convert fallback to singular if possible by removing trailing 's'
                fallback = product.get('subcategory', 'Unknown Category').lower()
                if fallback.endswith('s'):
                    fallback = fallback[:-1]
                product['translated_subcategory'] = fallback
        else:
            product['translated_subcategory'] = get_translated_subcategory(product['subcategory'], lang)
        print(f"Final translation for {product.get('subcategory')} in {lang}: {product['translated_subcategory']}")
    
    if lang == "jp":
        # Japanese specific formatting
        product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
        return f"{template}{'、'.join(product_links)}。"
    elif lang == "zh":
        # Chinese specific formatting
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
