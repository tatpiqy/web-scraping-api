from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import os

app = Flask(__name__)
CORS(app)

# Authentication token
AUTH_TOKEN = "B048C50E-9B124D9C-A6663DDF-B1CA5349"

def verify_auth(data):
    """Verify authentication token"""
    token = data.get('auth-token') or request.args.get('auth-token')
    if token != AUTH_TOKEN:
        return False
    return True

@app.route('/')
def home():
    return jsonify({
        "status": "ok",
        "message": "Web Scraping API is running",
        "endpoints": [
            "/webhook/get_text",
            "/webhook/list-links"
        ]
    })

@app.route('/webhook/get_text', methods=['GET', 'POST', 'OPTIONS'])
def get_text():
    """Extract plain text from a webpage"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Get data from JSON body, form data, or query parameters
    if request.is_json:
        data = request.get_json()
    elif request.form:
        data = request.form.to_dict()
    else:
        data = request.args.to_dict()
    
    # Verify authentication
    if not verify_auth(data):
        return jsonify({"error": "Non-subscribed user.", "code": 404}), 404
    
    # Get URL parameter
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL parameter is required", "code": 400}), 400
    
    try:
        # Fetch the webpage
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "header", "footer"]):
            script.decompose()
        
        # Get text
        text = soup.get_text()
        
        # Clean up text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return jsonify({
            "text": text,
            "url": url
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Failed to fetch URL: {str(e)}",
            "code": 500
        }), 500

@app.route('/webhook/list-links', methods=['GET', 'POST', 'OPTIONS'])
def list_links():
    """Extract internal links from a webpage"""
    if request.method == 'OPTIONS':
        return '', 200
    
    # Get data from JSON body, form data, or query parameters
    if request.is_json:
        data = request.get_json()
    elif request.form:
        data = request.form.to_dict()
    else:
        data = request.args.to_dict()
    
    # Verify authentication
    if not verify_auth(data):
        return jsonify({"error": "Non-subscribed user.", "code": 404}), 404
    
    # Get URL parameter
    url = data.get('url')
    if not url:
        return jsonify({"error": "URL parameter is required", "code": 400}), 400
    
    try:
        # Fetch the webpage
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Get base URL
        parsed_url = urlparse(url)
        base_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"
        
        # Extract all links
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(url, href)
            
            # Only include internal links (same domain)
            if urlparse(absolute_url).netloc == parsed_url.netloc:
                # Exclude root path and empty links
                if absolute_url != base_domain and absolute_url != base_domain + '/':
                    links.add(absolute_url)
        
        # Return up to 100 links
        return jsonify({
            "urls": sorted(list(links))[:100]
        })
    
    except Exception as e:
        return jsonify({
            "error": f"Failed to fetch URL: {str(e)}",
            "code": 500
        }), 500

if __name__ == '__main__':
    # IMPORTANT: Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

