#!/usr/bin/env python3
"""
Web Scraping API - Replacement for lemolex.app.n8n.cloud/webhook/get_text
This API provides two endpoints:
1. /get_text - Fetches and returns plain text from a webpage
2. /list_links - Returns all internal links from a webpage
"""

from flask import Flask, request, jsonify
from bs4 import BeautifulSoup
import requests
from urllib.parse import urljoin, urlparse
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Authentication token (change this to your own secure token)
AUTH_TOKEN = "B048C50E-9B124D9C-A6663DDF-B1CA5349"

def verify_auth(request_data):
    """Verify authentication token"""
    token = request_data.get('auth-token', '')
    if token != AUTH_TOKEN:
        return False
    return True

def get_domain(url):
    """Extract domain from URL"""
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_request_data():
    """Extract data from request regardless of method or content type"""
    data = {}
    
    # Try JSON body first
    if request.is_json:
        data = request.get_json() or {}
    # Try form data
    elif request.form:
        data = request.form.to_dict()
    # Try query parameters
    elif request.args:
        data = request.args.to_dict()
    # Try raw data as JSON
    elif request.data:
        try:
            import json
            data = json.loads(request.data.decode('utf-8'))
        except:
            pass
    
    return data

@app.route('/webhook/get_text', methods=['POST', 'GET', 'OPTIONS'])
def get_text():
    """
    Fetches the fully-rendered plain text of a single webpage.
    
    Input (JSON body or query params):
      {
        "url": "<absolute https://...>",
        "auth-token": "<your-auth-token>"
      }
    
    Output (JSON):
      {
        "text": "<visible text of the body>",
        "url": "<same url>"
      }
    """
    try:
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200
        
        # Get request data
        data = get_request_data()
        
        # Verify authentication
        if not verify_auth(data):
            return jsonify({
                "error": "Non-subscribed user.",
                "code": 404
            }), 404
        
        url = data.get('url', '')
        if not url:
            return jsonify({
                "error": "URL parameter is required",
                "code": 400
            }), 400
        
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML and extract text
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()
        
        # Get text
        text = soup.get_text(separator=' ', strip=True)
        
        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return jsonify({
            "text": text,
            "url": url
        })
    
    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        return jsonify({
            "error": f"Failed to fetch URL: {str(e)}",
            "code": 500
        }), 500
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({
            "error": str(e),
            "code": 500
        }), 500


@app.route('/webhook/list-links', methods=['POST', 'GET', 'OPTIONS'])
def list_links():
    """
    Returns up to 100 unique, fully-qualified INTERNAL links for a given page.
    
    Input (JSON body or query params):
      {
        "url": "<absolute https://...>",
        "auth-token": "<your-auth-token>"
      }
    
    Output (JSON):
      {
        "urls": ["<link-1>", "<link-2>", ...]
      }
    """
    try:
        # Handle OPTIONS request for CORS
        if request.method == 'OPTIONS':
            return jsonify({"status": "ok"}), 200
        
        # Get request data
        data = get_request_data()
        
        # Verify authentication
        if not verify_auth(data):
            return jsonify({
                "error": "Non-subscribed user.",
                "code": 404
            }), 404
        
        url = data.get('url', '')
        if not url:
            return jsonify({
                "error": "URL parameter is required",
                "code": 400
            }), 400
        
        # Fetch the webpage
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Get base domain
        base_domain = get_domain(url)
        
        # Find all links
        links = set()
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href'].strip()
            
            # Skip empty, mailto, tel, javascript links
            if not href or href == '/' or href.startswith(('mailto:', 'tel:', 'javascript:')):
                continue
            
            # Convert to absolute URL
            absolute_url = urljoin(url, href)
            
            # Only include internal links (same domain)
            if absolute_url.startswith(base_domain):
                # Remove fragments
                absolute_url = absolute_url.split('#')[0]
                links.add(absolute_url)
            
            # Limit to 100 links
            if len(links) >= 100:
                break
        
        return jsonify({
            "urls": sorted(list(links))
        })
    
    except requests.RequestException as e:
        logging.error(f"Request error: {str(e)}")
        return jsonify({
            "error": f"Failed to fetch URL: {str(e)}",
            "code": 500
        }), 500
    
    except Exception as e:
        logging.error(f"Error: {str(e)}")
        return jsonify({
            "error": str(e),
            "code": 500
        }), 500


@app.route('/', methods=['GET'])
def home():
    """Home endpoint with API documentation"""
    return jsonify({
        "service": "Web Scraping API",
        "version": "1.0",
        "endpoints": {
            "/webhook/get_text": {
                "methods": ["POST", "GET"],
                "description": "Fetches plain text from a webpage",
                "input": {
                    "url": "string (required)",
                    "auth-token": "string (required)"
                },
                "output": {
                    "text": "string",
                    "url": "string"
                }
            },
            "/webhook/list-links": {
                "methods": ["POST", "GET"],
                "description": "Returns internal links from a webpage",
                "input": {
                    "url": "string (required)",
                    "auth-token": "string (required)"
                },
                "output": {
                    "urls": "array of strings"
                }
            }
        }
    })


# Add CORS headers to all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response


if __name__ == '__main__':
    # Get port from environment variable (Railway provides this)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
