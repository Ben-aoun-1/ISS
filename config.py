# config.py - Configuration for Orange Tunisia News Scraper

# OpenAI model to use
OPENAI_MODEL = "gpt-3.5-turbo"  # You can change this to "gpt-4" or any available model

# Orange Tunisia theme colors
ORANGE_THEME = {
    'primary': '#FF7900',    # Orange primary color
    'secondary': '#DD6B00',  # Darker orange
    'dark': '#333333',       # Dark text color
    'light': '#FFFFFF',      # Light background
    'grey': '#CCCCCC',       # Grey for borders
    'light_grey': '#F2F2F2', # Light grey for backgrounds
}

# News sources by topic
NEWS_SOURCES = {
    'technology': [
        'https://www.tunisianmonitor.com/en/category/tech',
        'https://www.webmanagercenter.com/category/high-tech/',
        'https://www.tekiano.com/category/telecom-it/'
    ],
    'business': [
        'https://www.tunisienumerique.com/category/business/',
        'https://www.webmanagercenter.com/category/economie/',
        'https://www.espacemanager.com/economie.html'
    ],
    'telecom': [
        'https://www.tekiano.com/category/telecom-it/',
        'https://www.webmanagercenter.com/tag/orange-tunisie/',
        'https://www.tunisietelecom.tn/Fr/Actualites_Tunisie_Telecom'
    ],
    'general': [
        'https://www.tap.info.tn/en',
        'https://www.tunisienumerique.com/en/',
        'https://www.tunisialive.net/'
    ]
}

# Article templates
ARTICLE_TEMPLATES = {
    'telecom_news': {
        'topic': 'Latest telecommunications news in Tunisia',
        'audience': 'Orange Tunisia customers and general public',
        'tone': 'informative and professional',
        'max_length': 800
    },
    'digital_inclusion': {
        'topic': 'Digital inclusion initiatives in Tunisia',
        'audience': 'Government officials, NGOs, and corporate partners',
        'tone': 'formal and persuasive',
        'max_length': 1000
    },
    'tech_trends': {
        'topic': 'Current technology trends affecting Tunisian telecom market',
        'audience': 'Tech-savvy consumers and business professionals',
        'tone': 'insightful and forward-looking',
        'max_length': 600
    },
    'customer_focus': {
        'topic': 'Orange Tunisia services and customer benefits',
        'audience': 'Current and potential Orange customers',
        'tone': 'friendly and helpful',
        'max_length': 700
    }
}

# Analytics configuration
ANALYTICS_CONFIG = {
    'sentiment_analysis': True,
    'keyword_extraction': True,
    'image_extraction': True,
    'max_keywords': 15,
    'min_keyword_relevance': 0.3
}

# Image processing configuration
IMAGE_CONFIG = {
    'min_width': 300,          # Minimum image width to include
    'min_height': 200,         # Minimum image height to include
    'preferred_formats': ['jpg', 'jpeg', 'png', 'webp'],
    'max_images_per_article': 5,
    'include_captions': True
}

# Caching configuration
CACHE_CONFIG = {
    'enabled': True,
    'ttl_seconds': 3600,  # Time-to-live: 1 hour
    'max_entries': 1000,  # Maximum cache entries
}