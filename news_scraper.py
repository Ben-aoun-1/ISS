import os
import time
from typing import List, Dict, Any
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain.chat_models import ChatOpenAI

# Try to load dotenv if it's installed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class NewsScraperAndGenerator:
    """A class to scrape news articles and generate custom content for Orange Tunisia."""
    
    def __init__(self, openai_api_key: str, model_name: str = "gpt-4"):
        """Initialize the scraper and generator with API key and model name."""
        self.openai_api_key = openai_api_key
        self.model_name = model_name
        self.llm = ChatOpenAI(temperature=0.7, model=model_name, api_key=openai_api_key)
        self.driver = None
        
        # Initialize driver when needed using setup_driver method
    
    def setup_driver(self):
        """Setup Selenium driver with appropriate options for the environment"""
        if self.driver is not None:
            return
            
        # Set up the Chrome driver with headless option
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        
        # Add language preferences for Arabic and French content
        chrome_options.add_argument("--lang=ar-TN,ar;fr-TN,fr;en-US,en;q=0.9")
        
        # Set UTF-8 encoding
        chrome_options.add_argument("--accept-charset=UTF-8")
        
        try:
            # First try using ChromeDriverManager
            self.driver = webdriver.Chrome(
                service=Service(ChromeDriverManager().install()),
                options=chrome_options
            )
        except Exception as e:
            print(f"Failed to initialize driver with ChromeDriverManager: {e}")
            try:
                # Fallback for Streamlit cloud or environments where ChromeDriverManager might not work
                self.driver = webdriver.Chrome(options=chrome_options)
            except Exception as e2:
                print(f"Failed to initialize Chrome driver: {e2}")
                raise RuntimeError("Could not initialize Chrome driver. Make sure Chrome is installed.")
    
    def scrape_with_bs4(self, url: str) -> Dict[str, Any]:
        """Scrape a news article using BeautifulSoup with UTF-8 encoding support."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'ar-TN,ar;fr-TN,fr;en-US,en;q=0.9',
                'Accept-Charset': 'UTF-8'
            }
            
            response = requests.get(url, headers=headers)
            response.encoding = 'utf-8'  # Ensure UTF-8 encoding
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Tunisia-specific news site selectors
            tunisia_selectors = {
                'title': [
                    '.article-title', '.entry-title', '.post-title', 
                    '.title', 'h1.title', '.entry-header h1', 
                    '.post-header h1', '.article__title', '.article-head h1'
                ],
                'content': [
                    '.article-content', '.entry-content', '.post-content', 
                    'article', '.story-body', '.article__content',
                    '.post-body', '.article-text', '.content-area'
                ],
                'date': [
                    'time', '.published', '.post-date', '.entry-date',
                    '.date', '.article-date', '.publish-date',
                    '.article__date', '.post__date', '.meta-date'
                ],
                'author': [
                    '.author', '.entry-author', '.byline', '.writer',
                    '.article-author', '.meta-author', '.post-author'
                ]
            }
            
            # Extract title
            title = None
            for selector in tunisia_selectors['title']:
                title_element = soup.select_one(selector)
                if title_element:
                    title = title_element.get_text().strip()
                    break
                    
            # If not found, try general h1
            if not title:
                h1_elements = soup.select('h1')
                if h1_elements:
                    title = h1_elements[0].get_text().strip()
            
            # Extract content
            content = ""
            for selector in tunisia_selectors['content']:
                content_elements = soup.select(f"{selector} p")
                if content_elements:
                    content = " ".join([p.get_text().strip() for p in content_elements])
                    break
                    
            # If no content found with selectors, get all paragraphs
            if not content:
                # Get all paragraphs with decent length
                paragraphs = soup.select('p')
                content = " ".join([p.get_text().strip() for p in paragraphs 
                                    if len(p.get_text().strip()) > 50])
            
            # Extract publish date
            publish_date = None
            for selector in tunisia_selectors['date']:
                date_element = soup.select_one(selector)
                if date_element:
                    if date_element.name == 'meta':
                        publish_date = date_element.get('content', '')
                    else:
                        publish_date = date_element.get_text().strip()
                    break
            
            # Extract author
            author = None
            for selector in tunisia_selectors['author']:
                author_element = soup.select_one(selector)
                if author_element:
                    if author_element.name == 'meta':
                        author = author_element.get('content', '')
                    else:
                        author = author_element.get_text().strip()
                    break
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'publish_date': publish_date,
                'author': author
            }
        
        except Exception as e:
            print(f"Error scraping {url} with BeautifulSoup: {e}")
            return {'url': url, 'error': str(e)}
    
    def scrape_with_selenium(self, url: str) -> Dict[str, Any]:
        """Scrape a news article using Selenium for JavaScript-heavy pages."""
        try:
            # Ensure driver is set up
            self.setup_driver()
            
            self.driver.get(url)
            
            # Wait for page to load
            WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Allow JS to render
            time.sleep(5)
            
            # Extract title
            title = self.driver.title
            
            # Tunisia-specific news site selectors
            tunisia_selectors = {
                'content': [
                    '.article-content', '.entry-content', '.post-content', 
                    'article', '.story-body', '.article__content',
                    '.post-body', '.article-text', '.content-area'
                ],
                'date': [
                    'time', '.published', '.post-date', '.entry-date',
                    '.date', '.article-date', '.publish-date'
                ],
                'author': [
                    '.author', '.entry-author', '.byline', '.writer',
                    '.article-author', '.meta-author'
                ]
            }
            
            # Try to find h1 title which might be more accurate than page title
            try:
                h1_elements = self.driver.find_elements(By.TAG_NAME, "h1")
                if h1_elements:
                    title = h1_elements[0].text.strip()
            except:
                pass
            
            # Try to find the main content
            content = ""
            for selector in tunisia_selectors['content']:
                try:
                    content_elements = self.driver.find_elements(By.CSS_SELECTOR, f"{selector} p")
                    if content_elements:
                        content = " ".join([p.text.strip() for p in content_elements])
                        break
                except:
                    continue
            
            # If no content found with selectors, get all paragraphs with decent length
            if not content:
                paragraphs = self.driver.find_elements(By.TAG_NAME, "p")
                content = " ".join([p.text.strip() for p in paragraphs if len(p.text.strip()) > 50])
            
            # Try to find publish date
            publish_date = None
            for selector in tunisia_selectors['date']:
                try:
                    date_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    publish_date = date_element.text.strip()
                    break
                except:
                    continue
            
            # Try to find author
            author = None
            for selector in tunisia_selectors['author']:
                try:
                    author_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                    author = author_element.text.strip()
                    break
                except:
                    continue
            
            return {
                'url': url,
                'title': title,
                'content': content,
                'publish_date': publish_date,
                'author': author
            }
        
        except Exception as e:
            print(f"Error scraping {url} with Selenium: {e}")
            return {'url': url, 'error': str(e)}
    
    def scrape_article(self, url: str) -> Dict[str, Any]:
        """Try scraping with BeautifulSoup first, fall back to Selenium if needed."""
        result = self.scrape_with_bs4(url)
        
        # If BeautifulSoup didn't get content, try Selenium
        if not result.get('content') or len(result.get('content', '')) < 100:
            print(f"BeautifulSoup didn't get enough content, trying Selenium for {url}")
            result = self.scrape_with_selenium(url)
        
        return result
    
    def scrape_multiple_sources(self, urls: List[str]) -> List[Dict[str, Any]]:
        """Scrape multiple news sources."""
        results = []
        for url in urls:
            print(f"Scraping {url}...")
            article_data = self.scrape_article(url)
            results.append(article_data)
        return results
    
    def generate_article_for_orange(self, scraped_data: List[Dict[str, Any]], 
                                  topic: str, 
                                  audience: str = "general",
                                  tone: str = "professional",
                                  max_length: int = 800) -> str:
        """Generate a custom article for Orange Tunisia based on scraped news data."""
        
        # Create a combined text from all valid scraped articles
        all_content = "\n\n".join(
            [f"Article: {data.get('title', 'Untitled')}\n{data.get('content', 'No content')}" 
             for data in scraped_data if 'error' not in data and data.get('content')]
        )
        
        # Create prompt template for Tunisian context
        prompt_template = PromptTemplate(
            input_variables=["topic", "audience", "tone", "max_length", "all_content"],
            template="""
            You are a professional content creator for Orange Tunisia, the major telecommunications company in Tunisia.
            Your task is to create a new article in both English and Arabic based on information from various Tunisian news sources.
            
            Here's the information from multiple news sources in Tunisia:
            {all_content}
            
            Topic to focus on: {topic}
            Target audience: {audience}
            Tone: {tone}
            Maximum word count: {max_length}
            
            Create an article that:
            1. Is relevant to Orange Tunisia's business (telecommunications, digital services, connectivity in Tunisia)
            2. Synthesizes information from the sources without directly copying
            3. Adds value with insights relevant to Tunisian telecom market and Orange Tunisia's audience
            4. Includes a compelling headline
            5. Has a professional structure with introduction, body, and conclusion
            6. Includes appropriate subheadings
            7. Maintains the specified tone
            8. Is within the specified word count
            9. Includes cultural context relevant to Tunisia when appropriate
            10. First provide the content in English, then provide a translation in Arabic
            
            Format the article in Markdown, starting with the headline as a level 1 heading.
            """
        )
        
        # Create LangChain chain
        chain = LLMChain(llm=self.llm, prompt=prompt_template)
        
        # Run the chain
        result = chain.run({
            "topic": topic,
            "audience": audience,
            "tone": tone,
            "max_length": max_length,
            "all_content": all_content
        })
        
        return result
    
    def close(self):
        """Close the Selenium driver."""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
            self.driver = None