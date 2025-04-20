from flask import Flask, render_template, request, jsonify, send_file
import os
import json
import time
from datetime import datetime
import logging
import markdown
import tempfile
from pathlib import Path

from news_scraper import NewsScraperAndGenerator
import config

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('orange_news_scraper.log')
    ]
)
logger = logging.getLogger('orange_news_scraper')

# Initialize Flask application
app = Flask(__name__)

# Global scraper cache
scraper_cache = {}

def get_scraper(api_key):
    """Get or create a scraper instance using the provided API key"""
    if api_key in scraper_cache:
        # Return existing instance
        logger.info(f"Using cached scraper for API key ending in ...{api_key[-4:]}")
        return scraper_cache[api_key]
    else:
        # Create new instance
        logger.info(f"Creating new scraper for API key ending in ...{api_key[-4:]}")
        scraper = NewsScraperAndGenerator(api_key, config.OPENAI_MODEL)
        scraper_cache[api_key] = scraper
        return scraper

def get_sources_by_topic(topic):
    """Get list of sources by topic from config"""
    logger.info(f"Getting sources for topic: {topic}")
    
    if topic == 'all':
        # Combine all sources
        all_sources = []
        for sources in config.NEWS_SOURCES.values():
            all_sources.extend(sources)
        return all_sources
    else:
        return config.NEWS_SOURCES.get(topic, [])

@app.route('/')
def index():
    """Render the main application page"""
    # Get configuration items needed for the UI
    topics = list(config.NEWS_SOURCES.keys())
    templates = list(config.ARTICLE_TEMPLATES.keys())
    
    # Pass data to the template
    return render_template(
        'index.html',
        topics=topics,
        templates=templates,
        article_templates=config.ARTICLE_TEMPLATES
    )

@app.route('/api/get_sources', methods=['GET'])
def get_sources():
    """API endpoint to get sources by topic"""
    try:
        # Get request parameters
        topic = request.args.get('topic', 'all')
        
        # Get sources for the topic
        sources = get_sources_by_topic(topic)
        
        # Return the sources
        return jsonify({
            'success': True,
            'urls': sources
        })
        
    except Exception as e:
        logger.exception(f"Error getting sources: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/template_defaults', methods=['GET'])
def get_template_defaults():
    """API endpoint to get template defaults"""
    try:
        # Get request parameters
        template_name = request.args.get('template', 'telecom_news')
        
        # Get template defaults
        template = config.ARTICLE_TEMPLATES.get(template_name, {})
        
        # Return the template
        return jsonify({
            'success': True,
            'template': template
        })
        
    except Exception as e:
        logger.exception(f"Error getting template defaults: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/scrape', methods=['POST'])
def scrape_news():
    """API endpoint to scrape news sources"""
    try:
        # Get request data
        data = request.json
        
        # Log the received data for debugging
        logger.info(f"Received scrape request with data: {data}")
        
        api_key = data.get('api_key', '')
        topic = data.get('topic', 'all')
        custom_urls = data.get('custom_urls', [])
        search_keyword = data.get('search_keyword', '')
        max_workers = int(data.get('max_workers', 5))
        
        # Validate API key
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
            
        # Get scraper
        try:
            scraper = get_scraper(api_key)
        except Exception as e:
            logger.error(f"Error getting scraper: {e}")
            return jsonify({'error': f'Error initializing scraper: {str(e)}'}), 500
        
        # Determine sources
        urls = []
        if custom_urls and len(custom_urls) > 0:
            urls = custom_urls
        else:
            urls = get_sources_by_topic(topic)
            
        if not urls:
            return jsonify({'error': 'No sources specified'}), 400
            
        logger.info(f"Scraping URLs: {urls}")
        
        # Perform scraping
        try:
            results = scraper.scrape_multiple_sources(urls, max_workers=max_workers)
            
            # Apply keyword filtering if specified
            if search_keyword:
                filtered_results = []
                for article in results:
                    if 'error' in article:
                        continue
                    
                    title = article.get('title', '').lower()
                    content = article.get('content', '').lower()
                    
                    if search_keyword.lower() in title or search_keyword.lower() in content:
                        filtered_results.append(article)
                
                results = filtered_results
            
            # Count valid articles
            valid_articles = [a for a in results if 'error' not in a]
            
            # Return results
            return jsonify({
                'success': True,
                'total': len(valid_articles),
                'results': results
            })
        
        except Exception as e:
            logger.exception(f"Error during scraping execution: {e}")
            return jsonify({'error': f'Error during scraping: {str(e)}'}), 500
        
    except Exception as e:
        logger.exception(f"Error during scraping: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/generate', methods=['POST'])
def generate_article():
    """API endpoint to generate an article from scraped data"""
    try:
        # Get request data
        data = request.json
        api_key = data.get('api_key', '')
        scraped_data = data.get('scraped_data', [])
        template = data.get('template', 'telecom_news')
        custom_topic = data.get('topic', '')
        audience = data.get('audience', '')
        tone = data.get('tone', '')
        max_length = int(data.get('max_length', 800))
        include_images = data.get('include_images', True)
        
        # Validate API key
        if not api_key:
            return jsonify({'error': 'API key is required'}), 400
            
        # Validate scraped data
        if not scraped_data:
            return jsonify({'error': 'Scraped data is required'}), 400
            
        # Get scraper
        scraper = get_scraper(api_key)
        
        # Get template settings
        template_config = config.ARTICLE_TEMPLATES.get(template, {})
        
        # Use custom values or fall back to template defaults
        topic = custom_topic or template_config.get('topic', '')
        audience = audience or template_config.get('audience', 'general')
        tone = tone or template_config.get('tone', 'professional')
        max_length = max_length or template_config.get('max_length', 800)
        
        # Generate article
        result = scraper.generate_article_for_orange(
            scraped_data,
            topic=topic,
            audience=audience,
            tone=tone,
            max_length=max_length,
            include_images=include_images
        )
        
        # Prepare HTML content
        content = result.get('content', '')
        
        # Use Python-Markdown to convert to HTML
        try:
            html_content = markdown.markdown(content)
        except Exception as e:
            logger.error(f"Error converting markdown to HTML: {e}")
            html_content = f"<p>Error rendering HTML: {str(e)}</p><pre>{content}</pre>"
        
        # Return result
        return jsonify({
            'success': True,
            'article': result,
            'html_content': html_content
        })
        
    except Exception as e:
        logger.exception(f"Error during article generation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/download', methods=['POST'])
def download_article():
    """API endpoint to download an article in various formats"""
    try:
        # Get request data
        data = request.json
        content = data.get('content', '')
        format_type = data.get('format', 'md')
        template_name = data.get('template_name', 'article')
        
        if not content:
            return jsonify({'error': 'Content is required'}), 400
            
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Handle different formats
        if format_type == 'md':
            # Markdown format
            filename = f"orange_tunisia_article_{template_name}_{timestamp}.md"
            return jsonify({
                'success': True,
                'download_url': f"/download/md/{filename}",
                'content': content,
                'filename': filename
            })
            
        elif format_type == 'html':
            # HTML format
            html_content = markdown.markdown(content)
            styled_html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Orange Tunisia Article</title>
                <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/boosted@5.3.2/dist/css/boosted.min.css">
                <style>
                    body {{
                        font-family: Arial, sans-serif;
                        line-height: 1.6;
                        margin: 20px;
                        max-width: 800px;
                        color: #333;
                    }}
                    h1 {{
                        color: {config.ORANGE_THEME['primary']};
                    }}
                    h2, h3, h4 {{
                        color: {config.ORANGE_THEME['secondary']};
                    }}
                    a {{
                        color: {config.ORANGE_THEME['primary']};
                    }}
                    blockquote {{
                        border-left: 4px solid {config.ORANGE_THEME['primary']};
                        padding-left: 15px;
                        margin-left: 0;
                        color: {config.ORANGE_THEME['grey']};
                    }}
                    img {{
                        max-width: 100%;
                    }}
                    pre {{
                        background-color: {config.ORANGE_THEME['light_grey']};
                        padding: 10px;
                        border-radius: 5px;
                        overflow-x: auto;
                    }}
                    code {{
                        background-color: {config.ORANGE_THEME['light_grey']};
                        padding: 2px 4px;
                        border-radius: 3px;
                    }}
                </style>
            </head>
            <body>
                {html_content}
                <script src="https://cdn.jsdelivr.net/npm/boosted@5.3.2/dist/js/boosted.bundle.min.js"></script>
            </body>
            </html>
            """
            
            filename = f"orange_tunisia_article_{template_name}_{timestamp}.html"
            return jsonify({
                'success': True,
                'download_url': f"/download/html/{filename}",
                'content': styled_html,
                'filename': filename
            })
            
        elif format_type == 'json':
            # JSON format (analytics data)
            analytics_data = data.get('analytics_data', {})
            filename = f"orange_tunisia_analytics_{template_name}_{timestamp}.json"
            
            return jsonify({
                'success': True,
                'download_url': f"/download/json/{filename}",
                'content': json.dumps(analytics_data, indent=2),
                'filename': filename
            })
            
        else:
            return jsonify({'error': 'Unsupported format'}), 400
            
    except Exception as e:
        logger.exception(f"Error during download preparation: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/download/<format_type>/<filename>')
def download_file(format_type, filename):
    """Handle file download"""
    try:
        # Get content from the session or recreate it
        content = request.args.get('content', '')
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Write content to the temporary file
            tmp.write(content.encode('utf-8'))
            tmp_path = tmp.name
        
        # Set content type based on format
        if format_type == 'md':
            mimetype = 'text/markdown'
        elif format_type == 'html':
            mimetype = 'text/html'
        elif format_type == 'json':
            mimetype = 'application/json'
        else:
            mimetype = 'text/plain'
        
        # Return the file
        return send_file(
            tmp_path,
            mimetype=mimetype,
            as_attachment=True,
            download_name=filename
        )
        
    except Exception as e:
        logger.exception(f"Error during file download: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Create output directory if it doesn't exist
    Path('output').mkdir(exist_ok=True)
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)