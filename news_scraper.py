import os
import time
import concurrent.futures
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
import random
import json

# Try to load dotenv if it's installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class NewsScraperAndGenerator:
    """A class to scrape news articles and generate custom content for Orange Tunisia."""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-3.5-turbo"):
        """Initialize the scraper and generator with API key and model name."""
        self.openai_api_key = openai_api_key
        self.model_name = model_name
        self.article_cache = {}  # Simple in-memory cache for articles
    
    def get_cached_article(self, url: str) -> Dict[str, Any]:
        """Get article from cache if it exists and is not older than 1 hour"""
        if url in self.article_cache:
            cache_time, article_data = self.article_cache[url]
            # Check if cache is still fresh (less than 1 hour old)
            if time.time() - cache_time < 3600:  # 3600 seconds = 1 hour
                print(f"Using cached data for {url}")
                return article_data
        return None
    
    def cache_article(self, url: str, article_data: Dict[str, Any]):
        """Cache article data with current timestamp"""
        self.article_cache[url] = (time.time(), article_data)
    
    def scrape_article(self, url: str) -> Dict[str, Any]:
        """Scrape an article from a URL"""
        # Check cache first
        cached_article = self.get_cached_article(url)
        if cached_article:
            return cached_article
        
        try:
            # Set up headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,fr-FR;q=0.8,fr;q=0.7,ar;q=0.6',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            
            # Try to fetch the URL with a timeout
            response = requests.get(url, headers=headers, timeout=15)
            
            # Set proper encoding
            if response.encoding == 'ISO-8859-1':
                response.encoding = 'utf-8'
                
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract title - try different methods
            title = None
            if soup.title:
                title = soup.title.text.strip()
            
            # Try h1 tags if title is still None or too generic
            if not title or title.lower() in ['home', 'homepage', 'index']:
                h1_tags = soup.find_all('h1')
                if h1_tags:
                    title = h1_tags[0].text.strip()
            
            # Extract content - try multiple selectors that could contain the main article
            content_selectors = [
                'article', '.article', '.post', '.content', '.entry-content',
                '.post-content', '.article-content', 'main', '#content',
                '.story-body', '.story', '.news-article', '.news-content'
            ]
            
            content = ""
            for selector in content_selectors:
                elements = soup.select(selector)
                if elements:
                    # Get all paragraphs from the first matching element
                    paragraphs = elements[0].find_all('p')
                    if paragraphs:
                        content = " ".join([p.text.strip() for p in paragraphs])
                        break
            
            # If no content found with specific selectors, get all paragraphs
            if not content:
                paragraphs = soup.find_all('p')
                # Filter out very short paragraphs that could be UI elements
                valid_paragraphs = [p.text.strip() for p in paragraphs if len(p.text.strip()) > 40]
                content = " ".join(valid_paragraphs)
            
            # Try to extract publish date
            publish_date = None
            date_selectors = [
                'time', '.date', '.published', '.post-date', '.article-date',
                'meta[property="article:published_time"]', 'meta[name="date"]',
                '.byline time', '.meta-date', '.entry-date'
            ]
            
            for selector in date_selectors:
                elements = soup.select(selector)
                if elements:
                    date_element = elements[0]
                    if date_element.name == 'meta':
                        publish_date = date_element.get('content', '')
                    else:
                        publish_date = date_element.text.strip()
                    break
            
            # Try to extract author
            author = None
            author_selectors = [
                '.author', '.byline', '.article-author', '.entry-author',
                'meta[name="author"]', '.writer', '.post-author'
            ]
            
            for selector in author_selectors:
                elements = soup.select(selector)
                if elements:
                    author_element = elements[0]
                    if author_element.name == 'meta':
                        author = author_element.get('content', '')
                    else:
                        author = author_element.text.strip()
                    break
            
            # Try to extract main image
            image_url = None
            image_selectors = [
                'meta[property="og:image"]',
                'meta[name="twitter:image"]',
                '.featured-image img',
                '.article-featured-image img',
                '.post-thumbnail img',
                'article img:first-of-type',
                '.entry-content img:first-of-type'
            ]
            
            for selector in image_selectors:
                elements = soup.select(selector)
                if elements:
                    image_element = elements[0]
                    if image_element.name == 'meta':
                        image_url = image_element.get('content', '')
                    else:
                        image_url = image_element.get('src', '')
                    
                    # Handle relative URLs
                    if image_url and not image_url.startswith(('http://', 'https://')):
                        from urllib.parse import urljoin
                        image_url = urljoin(url, image_url)
                    
                    break
            
            # Create article data
            article_data = {
                'url': url,
                'title': title or 'Untitled Article',
                'content': content or 'No content could be extracted from this page.',
                'publish_date': publish_date or 'Unknown',
                'author': author or 'Unknown',
                'image_url': image_url
            }
            
            # Cache the result
            self.cache_article(url, article_data)
            
            return article_data
        
        except Exception as e:
            print(f"Error scraping {url}: {str(e)}")
            return {'url': url, 'error': str(e)}
    
    def _scrape_url_worker(self, url: str) -> Dict[str, Any]:
        """Worker function for parallel scraping"""
        print(f"Scraping {url}...")
        return self.scrape_article(url)
    
    def scrape_multiple_sources(self, urls: List[str], max_workers: int = 5) -> List[Dict[str, Any]]:
        """Scrape multiple news sources in parallel."""
        results = []
        
        # Use ThreadPoolExecutor for parallel scraping
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all scraping tasks
            future_to_url = {executor.submit(self._scrape_url_worker, url): url for url in urls}
            
            # Process results as they complete
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    article_data = future.result()
                    results.append(article_data)
                except Exception as e:
                    print(f"Error processing {url}: {str(e)}")
                    results.append({'url': url, 'error': str(e)})
        
        return results
    
    def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """Simulate sentiment analysis for the application"""
        # For simplicity, we'll use a random generator approach
        # In a production environment, you would use an actual NLP service
        
        # Generate scores between -1.0 and 1.0
        sentiment = {
            "overall": round(random.uniform(-0.3, 0.8), 2),
            "telecommunications": round(random.uniform(0.0, 0.9), 2),
            "technology": round(random.uniform(-0.1, 0.7), 2),
            "orange": round(random.uniform(0.2, 0.9), 2)
        }
        
        return sentiment
    
    def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract keywords from text or simulate for testing"""
        # For simplicity, we'll use predefined keywords relevant to the domain
        # In a production environment, you would use an NLP service
        
        all_keywords = [
            "5G", "Digital Inclusion", "Mobile Banking", "IoT", "Smart Cities",
            "Fiber Optics", "Rural Connectivity", "Data Privacy", "Cloud Services",
            "Digital Transformation", "e-Government", "Telecommunications", "Orange Tunisia",
            "Network Infrastructure", "Mobile Money", "Internet", "Broadband",
            "Cybersecurity", "Mobile Apps", "Tech Startups", "Innovation", "Connectivity"
        ]
        
        # Generate a random subset of keywords
        random.shuffle(all_keywords)
        return all_keywords[:max_keywords]
    
    def generate_article_for_orange(self, 
                                    scraped_data: List[Dict[str, Any]],
                                    topic: str, 
                                    audience: str = "general",
                                    tone: str = "professional",
                                    max_length: int = 800,
                                    include_images: bool = True) -> Dict[str, Any]:
        """Generate a custom article for Orange Tunisia based on scraped news data."""
        
        # Extract available images
        images = []
        if include_images:
            for data in scraped_data:
                if 'error' not in data and data.get('image_url'):
                    images.append({
                        'url': data.get('image_url'),
                        'source': data.get('url', ''),
                        'title': data.get('title', 'Image')
                    })
        
        # Generate a generic article template based on the topic
        article_content = f"""# {topic.title()} in Tunisia's Telecommunications Sector

## Introduction

Tunisia's telecommunications sector has been undergoing rapid transformation in recent years. This article explores the latest developments in {topic.lower()}, with a focus on implications for Orange Tunisia customers and stakeholders.

## Key Insights from Recent News

"""
        # Add content from scraped articles
        article_points = []
        for data in scraped_data:
            if 'error' not in data and data.get('content'):
                # Get the first 2-3 sentences as a summary
                content = data.get('content', '')
                sentences = content.split('. ')
                summary = '. '.join(sentences[:min(3, len(sentences))]) + '.'
                
                # Add a bullet point with source reference
                source_name = data.get('url', '').split('//')[-1].split('/')[0]
                article_points.append(f"- {summary} (Source: {source_name})")
        
        # Add unique points to the article
        unique_points = set(article_points)
        article_content += "\n".join(list(unique_points)[:5]) + "\n\n"
        
        # Add more sections
        article_content += f"""
## Current Landscape

The digital landscape in Tunisia presents both challenges and opportunities for telecommunications providers. With increasing internet penetration rates and smartphone adoption, demand for high-quality services continues to grow.

Orange Tunisia has positioned itself as a leader in innovation, offering solutions that address the unique needs of the Tunisian market.

## Key Trends

Several important trends are shaping the future of telecommunications in Tunisia:

1. Expansion of 5G networks in urban centers
2. Growing demand for digital financial services
3. Increasing focus on cybersecurity and data privacy
4. Development of smart city initiatives
5. Digital inclusion programs for rural communities

## Opportunities for Growth

For Orange Tunisia, these trends represent significant opportunities for growth and service expansion. By leveraging its expertise and infrastructure, Orange can continue to contribute to Tunisia's digital transformation.

## Conclusion

As Tunisia continues its digital journey, telecommunications providers like Orange will play a crucial role in building the infrastructure and services needed for a connected future.

---

# {topic.title()} في قطاع الاتصالات في تونس

## مقدمة

يشهد قطاع الاتصالات في تونس تحولًا سريعًا في السنوات الأخيرة. تستكشف هذه المقالة أحدث التطورات في {topic.lower()}، مع التركيز على الآثار المترتبة على عملاء وأصحاب المصلحة في Orange Tunisia.

## المشهد الحالي

يقدم المشهد الرقمي في تونس تحديات وفرصًا لمزودي خدمات الاتصالات. مع زيادة معدلات انتشار الإنترنت واعتماد الهواتف الذكية، يستمر الطلب على الخدمات عالية الجودة في النمو.

وضعت Orange Tunisia نفسها كرائدة في مجال الابتكار، حيث تقدم حلولًا تلبي الاحتياجات الفريدة للسوق التونسية.

## الاتجاهات الرئيسية

هناك العديد من الاتجاهات المهمة التي تشكل مستقبل الاتصالات في تونس:

1. توسيع شبكات الجيل الخامس في المراكز الحضرية
2. تزايد الطلب على الخدمات المالية الرقمية
3. زيادة التركيز على الأمن السيبراني وخصوصية البيانات
4. تطوير مبادرات المدن الذكية
5. برامج الشمول الرقمي للمجتمعات الريفية

## فرص النمو

بالنسبة لـ Orange Tunisia، تمثل هذه الاتجاهات فرصًا كبيرة للنمو وتوسيع الخدمات. من خلال الاستفادة من خبراتها وبنيتها التحتية، يمكن لـ Orange أن تواصل المساهمة في التحول الرقمي في تونس.

## الخلاصة

مع استمرار تونس في رحلتها الرقمية، ستلعب شركات الاتصالات مثل Orange دورًا حاسمًا في بناء البنية التحتية والخدمات اللازمة لمستقبل متصل.
"""
        
        # Get sentiment and keywords from the scraped content
        all_text = "\n\n".join([data.get('content', '') for data in scraped_data 
                              if 'error' not in data and data.get('content')])
        
        sentiment = self.analyze_sentiment(all_text)
        keywords = self.extract_keywords(all_text)
        
        # Return the generated article with metadata
        return {
            "content": article_content,
            "sentiment_analysis": sentiment,
            "keywords": keywords,
            "images": images
        }
    
    def close(self):
        """Clean up resources"""
        pass