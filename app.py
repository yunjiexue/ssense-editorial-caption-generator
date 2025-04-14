from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os
import re
import certifi

# Load environment variables
load_dotenv()

app = Flask(__name__)

# MongoDB setup using environment variables
mongodb_uri = os.getenv('MONGODB_URI')
db_name = os.getenv('DB_NAME', 'products')  # Default to 'products' if not set

try:
    # Connect to MongoDB Atlas with SSL certificate verification
    client = MongoClient(mongodb_uri, tlsCAFile=certifi.where())
    db = client[db_name]
    # Test the connection
    client.admin.command('ping')
    print("Successfully connected to MongoDB!")
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")

def get_translated_subcategory(subcategory_en, target_lang):
    """Get translated subcategory from categorys collection."""
    try:
        # Map target language to field name
        field_map = {
            "en": "CategoryEN",
            "fr": "CategoryFR", 
            "jp": "CategoryJP",
            "zh": "CategoryZH"
        }
        
        field_name = field_map.get(target_lang)
        if not field_name:
            print(f"Unsupported language: {target_lang}")  # Debug log
            return subcategory_en

        # Try to find by subcategory_id first (for English)
        if target_lang == "en" and isinstance(subcategory_en, (int, str)):
            try:
                subcategory_id = int(subcategory_en) if isinstance(subcategory_en, str) else subcategory_en
                translation = db.categorys.find_one({"id": subcategory_id})
                if translation and field_name in translation:
                    print(f"Found translation by ID for {subcategory_en}: {translation[field_name]}")  # Debug log
                    return translation[field_name]
            except (ValueError, TypeError):
                pass
            
        # If not found by ID or for other languages, try exact match on category
        translation = db.categorys.find_one({"category": subcategory_en})
        if translation and field_name in translation:
            print(f"Found translation for {subcategory_en}: {translation[field_name]}")  # Debug log
            return translation[field_name]
            
        # If no exact match, try case-insensitive search
        translation = db.categorys.find_one({"category": {"$regex": f"^{subcategory_en}$", "$options": "i"}})
        if translation and field_name in translation:
            print(f"Found case-insensitive translation for {subcategory_en}: {translation[field_name]}")  # Debug log
            return translation[field_name]
            
        print(f"No translation found for {subcategory_en} in {target_lang}")  # Debug log
        return subcategory_en  # Fallback to English if no translation found
    except Exception as e:
        print(f"Error looking up translation: {e}")  # Debug log
        return subcategory_en

# Caption templates for each language
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
        "featured": "Présenté Dans Cette Image:",
        "also_featured": "Également Présenté Dans Cette Image:",
        "model_wears": "Le mannequin porte",
        "model_right": "Le mannequin (à droite) porte",
        "model_left": "Le mannequin (à gauche) porte",
        "model_middle": "Le mannequin (au milieu) porte",
        "featured_top": "Présenté Dans L'Image Du Haut:",
        "top_model": "Image Du Haut: Le mannequin porte",
        "talent": "[Nom du talent] porte",
        "talent_right": "[Nom du talent] (à droite) porte",
        "talent_left": "[Nom du talent] (à gauche) porte",
        "top_talent": "Image Du Haut: [Nom du talent] porte"
    },
    "jp": {
        "featured": "画像に登場するアイテム：",
        "also_featured": "画像に登場する他のアイテム：",
        "model_wears": "モデル着用：",
        "model_right": "モデル（右）着用：",
        "model_left": "モデル（左）着用：",
        "model_middle": "モデル（中央）着用：",
        "featured_top": "上の画像に登場するアイテム：",
        "top_model": "上の画像：モデル着用：",
        "talent": "[タレント名]着用：",
        "talent_right": "[タレント名]（右）着用：",
        "talent_left": "[タレント名]（左）着用：",
        "top_talent": "上の画像：[タレント名]着用："
    },
    "zh": {
        "featured": "图中精选单品：",
        "also_featured": "图中其他精选单品：",
        "model_wears": "模特穿着：",
        "model_right": "模特（右）穿着：",
        "model_left": "模特（左）穿着：",
        "model_middle": "模特（中）穿着：",
        "featured_top": "上图精选单品：",
        "top_model": "上图：模特穿着：",
        "talent": "[艺人姓名]穿着：",
        "talent_right": "[艺人姓名]（右）穿着：",
        "talent_left": "[艺人姓名]（左）穿着：",
        "top_talent": "上图：[艺人姓名]穿着："
    }
}

# Language-specific URL patterns
LANG_PATTERNS = {
    "fr": {
        "from": ["/en-", "/en/", "/product/", "/women/", "/men/"],
        "to": ["/fr/", "/fr/", "/produit/", "/femmes/", "/hommes/"]
    },
    "jp": {
        "from": ["/en-", "/en/"],
        "to": ["/ja/", "/ja/"]
    },
    "zh": {
        "from": ["/en-", "/en/"],
        "to": ["/zh/", "/zh/"]
    }
}

def convert_url_to_language(url, target_lang):
    """Convert English URL to target language URL."""
    if target_lang == "en":
        return url
        
    patterns = LANG_PATTERNS.get(target_lang)
    if not patterns:
        return url
        
    result = url
    for from_pattern, to_pattern in zip(patterns["from"], patterns["to"]):
        result = result.replace(from_pattern, to_pattern)
    
    return result

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
        # Japanese specific formatting - remove space after template
        product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
        return f"{template}{'、'.join(product_links)}。"
    elif lang == "zh":
        # Chinese specific formatting - remove space after template
        product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
        return f"{template}{'、'.join(product_links)}。"
    else:
        # English and French formatting
        product_links = [f"[{p['brand']} {p['translated_subcategory']}]({p['urls'][lang]})" for p in products]
        if len(product_links) == 1:
            return f"{template} {product_links[0]}."
        
        # Use appropriate conjunction for language
        conjunction = " and " if lang == "en" else " et "
        return f"{template} {', '.join(product_links[:-1])},{conjunction}{product_links[-1]}."

@app.route('/')
def index():
    return render_template('index.html', templates=TEMPLATES)

@app.route('/generate', methods=['POST'])
def generate():
    data = request.json
    urls = data.get('urls', [])
    template_type = data.get('template', "featured")  # Get template type
    talent_name = data.get('talent_name', '')  # Get talent name
    
    if not urls:
        return jsonify({'error': 'No URLs provided'}), 400
    
    products = []
    errors = []
    
    for url in urls:
        product_id = extract_product_id(url)
        if product_id:
            try:
                # Try to find product using string product_id
                product = db.products.find_one({"product_id": product_id})
                
                # If not found, try with integer product_id
                if not product:
                    product = db.products.find_one({"product_id": int(product_id)})
                
                if product:
                    # Generate URLs for all languages
                    product['urls'] = {
                        'en': url,
                        'fr': convert_url_to_language(url, 'fr'),
                        'jp': convert_url_to_language(url, 'jp'),
                        'zh': convert_url_to_language(url, 'zh')
                    }
                    products.append(product)
                else:
                    errors.append(f"Product ID {product_id} not found in database")
            except Exception as e:
                errors.append(f"Database error for product {product_id}: {str(e)}")
                print(f"Database error: {str(e)}")
        else:
            errors.append(f"Could not extract product ID from URL: {url}")
    
    # Generate captions in all languages
    captions = {}
    for lang in ['en', 'fr', 'jp', 'zh']:
        template = TEMPLATES[lang][template_type]
        # Replace talent name placeholders in all languages if provided
        if talent_name:
            if 'talent' in template_type or 'talent' in template.lower():
                if lang == 'fr':
                    template = template.replace('[Nom du talent]', talent_name)
                elif lang == 'jp':
                    template = template.replace('[タレント名]', talent_name)
                elif lang == 'zh':
                    template = template.replace('[艺人姓名]', talent_name)
                else:  # English
                    template = template.replace('[Talent name]', talent_name)
        captions[lang] = generate_caption(products, template, lang)
    
    # Add debug information
    print(f"URLs received: {urls}")
    print(f"Products found: {products}")
    print(f"Generated captions: {captions}")
    print(f"Errors: {errors}")
    
    return jsonify({
        'captions': captions,
        'errors': errors,
        'success': len(products) > 0
    })

if __name__ == '__main__':
    # Get port from environment variable (Render sets this automatically)
    port = int(os.getenv('PORT', 3000))
    
    # In production, debug should be False
    debug = os.getenv('FLASK_ENV') == 'development'
    
    # Host should be 0.0.0.0 for Render
    app.run(host='0.0.0.0', port=port, debug=debug)
