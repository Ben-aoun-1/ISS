#!/usr/bin/env python3
# app.py - Main application file for Orange Tunisia News Scraper

import os
import sys
import json
import argparse
from datetime import datetime
import time
from typing import List, Dict, Any
import concurrent.futures
import logging
from pathlib import Path
import markdown

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

class OrangeNewsScraper:
    """Main application class for Orange Tunisia News Scraper"""
    
    def __init__(self, api_key: str = None):
        """Initialize the application with API key from environment or argument"""
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            logger.error("No OpenAI API key provided. Please set OPENAI_API_KEY environment variable or pass as argument.")
            sys.exit(1)
        
        self.model_name = config.OPENAI_MODEL
        self.scraper = None
        
    def initialize_scraper(self):
        """Initialize the scraper only when needed"""
        if self.scraper is None:
            self.scraper = NewsScraperAndGenerator(self.api_key, self.model_name)
            # We're not using the persistent cache as it's causing issues
            # Just rely on the built-in in-memory cache
        return self.scraper
    
    def shutdown(self):
        """Properly close resources"""
        if self.scraper:
            self.scraper.close()
            self.scraper = None
    
    def get_sources_by_topic(self, topic: str) -> List[str]:
        """Get list of sources by topic"""
        if topic == 'all':
            # Combine all sources
            all_sources = []
            for sources in config.NEWS_SOURCES.values():
                all_sources.extend(sources)
            return all_sources
        else:
            return config.NEWS_SOURCES.get(topic, [])
    
    def scrape_news(self, 
                   topic: str = 'all', 
                   sources: List[str] = None, 
                   search_keyword: str = None,
                   max_workers: int = 5,
                   verbose: bool = False) -> List[Dict[str, Any]]:
        """Scrape news from specified sources"""
        # Initialize scraper
        scraper = self.initialize_scraper()
        
        # Determine sources
        if sources:
            urls_to_scrape = sources
        else:
            urls_to_scrape = self.get_sources_by_topic(topic)
        
        if not urls_to_scrape:
            logger.warning("No sources to scrape")
            return []
        
        logger.info(f"Starting to scrape {len(urls_to_scrape)} sources with {max_workers} workers")
        
        # Perform scraping
        results = scraper.scrape_multiple_sources(urls_to_scrape, max_workers=max_workers)
        
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
            
            logger.info(f"Filtered {len(results)} articles down to {len(filtered_results)} containing '{search_keyword}'")
            results = filtered_results
        
        # Save raw data if verbose
        if verbose:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            output_file = f"scraped_data_{timestamp}.json"
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"Raw scraped data saved to {output_file}")
        
        return results
    
    def generate_article(self,
                       scraped_data: List[Dict[str, Any]],
                       template: str = 'telecom_news',
                       custom_topic: str = None,
                       audience: str = None,
                       tone: str = None,
                       max_length: int = None,
                       include_images: bool = True,
                       output_dir: str = 'output') -> Dict[str, Any]:
        """Generate article from scraped data"""
        # Initialize scraper
        scraper = self.initialize_scraper()
        
        # Get template settings
        template_config = config.ARTICLE_TEMPLATES.get(template, {})
        
        # Use custom values or fall back to template defaults
        topic = custom_topic or template_config.get('topic', '')
        audience = audience or template_config.get('audience', 'general')
        tone = tone or template_config.get('tone', 'professional')
        max_length = max_length or template_config.get('max_length', 800)
        
        logger.info(f"Generating article with template: {template}, topic: {topic}")
        
        # Generate article
        result = scraper.generate_article_for_orange(
            scraped_data,
            topic=topic,
            audience=audience,
            tone=tone,
            max_length=max_length,
            include_images=include_images
        )
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        # Save article to markdown file
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        md_filename = f"{output_dir}/orange_tunisia_article_{template}_{timestamp}.md"
        
        with open(md_filename, 'w', encoding='utf-8') as f:
            f.write(result['content'])
        
        logger.info(f"Article saved to {md_filename}")
        
        # Save HTML version
        html_content = markdown.markdown(result['content'])
        html_filename = f"{output_dir}/orange_tunisia_article_{template}_{timestamp}.html"
        
        styled_html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
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
        </body>
        </html>
        """
        
        with open(html_filename, 'w', encoding='utf-8') as f:
            f.write(styled_html)
        
        logger.info(f"HTML version saved to {html_filename}")
        
        # Save analytics data
        analytics_data = {
            "article_info": {
                "title": template,
                "date": timestamp,
                "topic": topic,
                "audience": audience,
                "tone": tone,
                "word_count": len(result['content'].split())
            },
            "sentiment": result.get("sentiment_analysis", {}),
            "keywords": result.get("keywords", []),
            "images": [img.get("url") for img in result.get("images", [])]
        }
        
        analytics_filename = f"{output_dir}/orange_tunisia_analytics_{template}_{timestamp}.json"
        
        with open(analytics_filename, 'w', encoding='utf-8') as f:
            json.dump(analytics_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Analytics data saved to {analytics_filename}")
        
        return result

def main():
    """Main function for command-line execution"""
    parser = argparse.ArgumentParser(description="Orange Tunisia News Scraper and Article Generator")
    
    # Main options
    parser.add_argument('--topic', '-t', choices=['all', 'technology', 'business', 'telecom', 'general'], 
                        default='all', help='Topic category to focus on')
    parser.add_argument('--template', '-m', choices=list(config.ARTICLE_TEMPLATES.keys()),
                        default='telecom_news', help='Article template to use')
    parser.add_argument('--sources', '-s', nargs='+', help='Specific URLs to scrape (overrides topic selection)')
    parser.add_argument('--output', '-o', default='output', help='Directory to save output files')
    parser.add_argument('--custom-topic', '-c', help='Custom topic to focus on (overrides template topic)')
    parser.add_argument('--search', '-q', help='Keyword to search for in article content')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    
    # Advanced options
    parser.add_argument('--api-key', help='OpenAI API Key (overrides environment variable)')
    parser.add_argument('--workers', '-w', type=int, default=5, help='Number of parallel workers for scraping')
    parser.add_argument('--audience', help='Target audience (overrides template default)')
    parser.add_argument('--tone', help='Article tone (overrides template default)')
    parser.add_argument('--max-length', type=int, help='Maximum article length in words (overrides template default)')
    parser.add_argument('--no-images', action='store_true', help='Disable image inclusion in articles')
    
    args = parser.parse_args()
    
    # Initialize application
    app = OrangeNewsScraper(api_key=args.api_key)
    
    try:
        # Step 1: Scrape news sources
        scraped_data = app.scrape_news(
            topic=args.topic,
            sources=args.sources,
            search_keyword=args.search,
            max_workers=args.workers,
            verbose=args.verbose
        )
        
        if not scraped_data:
            logger.warning("No valid articles found to generate content")
            return
        
        # Step 2: Generate article
        app.generate_article(
            scraped_data,
            template=args.template,
            custom_topic=args.custom_topic,
            audience=args.audience,
            tone=args.tone,
            max_length=args.max_length,
            include_images=not args.no_images,
            output_dir=args.output
        )
        
    except KeyboardInterrupt:
        logger.info("Operation canceled by user")
    except Exception as e:
        logger.exception(f"Error during execution: {e}")
    finally:
        # Clean up resources
        app.shutdown()

if __name__ == "__main__":
    main()