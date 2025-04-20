# app.py
import streamlit as st
import os
import json
from datetime import datetime
import time
import threading
import markdown
import base64
from news_scraper import NewsScraperAndGenerator
import config

# Set page configuration
st.set_page_config(
    page_title="Orange Tunisia News Scraper",
    page_icon="📰",
    layout="wide"
)

# Define Orange theme colors
ORANGE_THEME = config.ORANGE_THEME

# Apply custom CSS
st.markdown(f"""
    <style>
        .stApp {{
            background-color: {ORANGE_THEME['light']};
            color: {ORANGE_THEME['dark']};
        }}
        h1, h2, h3, h4 {{
            color: {ORANGE_THEME['primary']};
        }}
        .stButton>button {{
            background-color: {ORANGE_THEME['primary']};
            color: {ORANGE_THEME['light']};
            border: none;
            border-radius: 5px;
            padding: 8px 15px;
            font-weight: bold;
        }}
        .stButton>button:hover {{
            background-color: {ORANGE_THEME['secondary']};
        }}
        .stTextInput>div>div>input {{
            border: 1px solid {ORANGE_THEME['grey']};
            border-radius: 4px;
            padding: 5px;
        }}
        .stSelectbox>div>div>div {{
            border: 1px solid {ORANGE_THEME['grey']};
            border-radius: 4px;
        }}
        .article-preview {{
            border: 1px solid {ORANGE_THEME['grey']};
            border-radius: 5px;
            padding: 10px;
            background-color: white;
        }}
        .html-preview {{
            border: 1px solid {ORANGE_THEME['grey']};
            border-radius: 5px;
            padding: 10px;
            background-color: white;
        }}
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = []
if 'current_article' not in st.session_state:
    st.session_state.current_article = ""
if 'scraping_status' not in st.session_state:
    st.session_state.scraping_status = "Ready to scrape..."
if 'generation_status' not in st.session_state:
    st.session_state.generation_status = "Ready to generate..."

# Header
st.markdown(f"<h1 style='color: {ORANGE_THEME['primary']}; text-align: center;'>ORANGE NEWS TUNISIA</h1>", unsafe_allow_html=True)

# Create tabs
tab1, tab2, tab3 = st.tabs(["Scrape News", "Generate Article", "Results"])

with tab1:
    st.header("News Sources")
    
    # Topic selection
    topic_options = ["all"] + list(config.NEWS_SOURCES.keys())
    topic_labels = ["All"] + [topic.replace("_", " ").title() for topic in config.NEWS_SOURCES.keys()]
    topic_dict = dict(zip(topic_labels, topic_options))
    
    selected_topic_label = st.selectbox("Topic:", topic_labels)
    selected_topic = topic_dict[selected_topic_label]
    
    # Custom URL
    custom_url = st.text_input("Custom URL:", placeholder="Enter custom URL")
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("Add URL"):
            if custom_url:
                if 'url_list' not in st.session_state:
                    st.session_state.url_list = []
                if custom_url not in st.session_state.url_list:
                    st.session_state.url_list.append(custom_url)
    with col2:
        if st.button("Clear URLs"):
            st.session_state.url_list = []
    
    # URL list
    st.subheader("Selected URLs:")
    
    # Get URLs from selected topic
    if selected_topic == "all":
        topic_urls = []
        for topic_urls_list in config.NEWS_SOURCES.values():
            topic_urls.extend(topic_urls_list)
    else:
        topic_urls = config.NEWS_SOURCES.get(selected_topic, [])
    
    # Combine with custom URLs if any
    if 'url_list' in st.session_state:
        all_urls = topic_urls + st.session_state.url_list
    else:
        all_urls = topic_urls
    
    # Display URL list
    st.text_area("", value="\n".join(all_urls), height=150, key="urls_display")
    
    # Filtering
    st.header("Filtering")
    keyword = st.text_input("Search Keyword:", placeholder="Enter keyword to filter articles")
    
    # Actions
    st.header("Actions")
    if st.button("Start Scraping", use_container_width=True):
        urls = all_urls
        
        if not urls:
            st.error("Please select a topic or add custom URLs")
        else:
            openai_api_key = st.session_state.get('openai_api_key', os.getenv("OPENAI_API_KEY", ""))
            if not openai_api_key:
                st.error("Please enter your OpenAI API Key in the sidebar")
            else:
                # Set status
                st.session_state.scraping_status = "Initializing scraper..."
                
                # Create a placeholder for progress
                progress_bar = st.progress(0)
                status_text = st.empty()
                status_text.text(st.session_state.scraping_status)
                
                try:
                    # Initialize scraper
                    scraper_generator = NewsScraperAndGenerator(openai_api_key, config.OPENAI_MODEL)
                    
                    results = []
                    total_urls = len(urls)
                    
                    # Scrape each URL
                    for i, url in enumerate(urls):
                        status = f"Scraping {url}..."
                        status_text.text(status)
                        st.session_state.scraping_status = status
                        
                        article_data = scraper_generator.scrape_article(url)
                        results.append(article_data)
                        
                        # Update progress
                        progress = int((i + 1) / total_urls * 100)
                        progress_bar.progress(progress / 100)
                    
                    # Handle filtering
                    if keyword:
                        filtered_data = []
                        for article in results:
                            if 'error' in article:
                                continue
                            
                            title = article.get('title', '').lower()
                            content = article.get('content', '').lower()
                            
                            if keyword.lower() in title or keyword.lower() in content:
                                filtered_data.append(article)
                        
                        results = filtered_data
                        status = f"Scraped and filtered {len(results)} articles containing '{keyword}'"
                    else:
                        valid_articles = [a for a in results if 'error' not in a]
                        status = f"Scraped {len(valid_articles)} articles successfully"
                    
                    # Update status
                    status_text.text(status)
                    st.session_state.scraping_status = status
                    
                    # Store results
                    st.session_state.scraped_data = results
                    
                    # Close scraper
                    scraper_generator.close()
                    
                    # Switch to generator tab if we have data
                    if len(results) > 0:
                        st.success(f"Successfully scraped {len(results)} articles. You can now generate an article.")
                    else:
                        st.warning("No articles found with the current settings.")
                
                except Exception as e:
                    error_message = f"Error: {str(e)}"
                    status_text.text(error_message)
                    st.session_state.scraping_status = error_message
                    st.error(error_message)
    
    # Progress section
    st.header("Progress")
    st.text(st.session_state.scraping_status)

with tab2:
    st.header("Article Settings")
    
    # Template selection
    template_options = list(config.ARTICLE_TEMPLATES.keys())
    template_labels = [template.replace("_", " ").title() for template in template_options]
    template_dict = dict(zip(template_labels, template_options))
    
    selected_template_label = st.selectbox("Template:", template_labels)
    selected_template = template_dict[selected_template_label]
    
    # Get template info
    template = config.ARTICLE_TEMPLATES.get(selected_template, {})
    
    # Form for article settings
    with st.form(key="article_settings"):
        custom_topic = st.text_input("Custom Topic:", value=template.get("topic", ""))
        audience = st.text_input("Audience:", value=template.get("audience", ""))
        tone = st.text_input("Tone:", value=template.get("tone", ""))
        max_length = st.number_input("Max Length (words):", value=template.get("max_length", 800), min_value=100, max_value=5000)
        
        # Generate button
        generate_submitted = st.form_submit_button(label="Generate Article", use_container_width=True)
        
        if generate_submitted:
            if not st.session_state.scraped_data:
                st.error("Please scrape some news sources first")
            else:
                openai_api_key = st.session_state.get('openai_api_key', os.getenv("OPENAI_API_KEY", ""))
                if not openai_api_key:
                    st.error("Please enter your OpenAI API Key in the sidebar")
                else:
                    # Set status
                    st.session_state.generation_status = "Initializing article generator..."
                    
                    # Create placeholders for progress
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    status_text.text(st.session_state.generation_status)
                    
                    try:
                        # Initialize generator
                        scraper_generator = NewsScraperAndGenerator(openai_api_key, config.OPENAI_MODEL)
                        
                        # Update status
                        status = "Generating article from scraped data..."
                        status_text.text(status)
                        st.session_state.generation_status = status
                        progress_bar.progress(30 / 100)
                        
                        # Generate article
                        article = scraper_generator.generate_article_for_orange(
                            st.session_state.scraped_data,
                            topic=custom_topic,
                            audience=audience,
                            tone=tone,
                            max_length=max_length
                        )
                        
                        # Update progress
                        progress_bar.progress(90 / 100)
                        
                        # Close generator
                        scraper_generator.close()
                        
                        # Update status
                        status = "Article generation completed!"
                        status_text.text(status)
                        st.session_state.generation_status = status
                        progress_bar.progress(100 / 100)
                        
                        # Store article
                        st.session_state.current_article = article
                        
                        # Success message
                        st.success("Article generated successfully! You can now view and save it in the Results tab.")
                        
                    except Exception as e:
                        error_message = f"Error: {str(e)}"
                        status_text.text(error_message)
                        st.session_state.generation_status = error_message
                        st.error(error_message)
    
    # Progress section
    st.header("Progress")
    st.text(st.session_state.generation_status)

with tab3:
    st.header("Article Preview")
    
    # Display article if available
    if st.session_state.current_article:
        # Text preview
        st.subheader("Markdown")
        st.markdown('<div class="article-preview">', unsafe_allow_html=True)
        st.text_area("", value=st.session_state.current_article, height=300, key="article_text")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # HTML preview
        st.subheader("HTML Preview")
        st.markdown('<div class="html-preview">', unsafe_allow_html=True)
        html_content = markdown.markdown(st.session_state.current_article)
        st.markdown(html_content, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Save button
        current_date = datetime.now().strftime("%Y%m%d-%H%M%S")
        template_name = selected_template
        file_name = f"orange_tunisia_article_{template_name}_{current_date}.md"
        
        # Create a download button
        st.download_button(
            label="Download Article as Markdown",
            data=st.session_state.current_article,
            file_name=file_name,
            mime="text/markdown",
            key="download_button"
        )
        
        # Create HTML download option
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
                    color: {ORANGE_THEME['primary']};
                }}
                h2, h3, h4 {{
                    color: {ORANGE_THEME['secondary']};
                }}
                a {{
                    color: {ORANGE_THEME['primary']};
                }}
                blockquote {{
                    border-left: 4px solid {ORANGE_THEME['primary']};
                    padding-left: 15px;
                    margin-left: 0;
                    color: {ORANGE_THEME['grey']};
                }}
                img {{
                    max-width: 100%;
                }}
                pre {{
                    background-color: {ORANGE_THEME['light_grey']};
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                code {{
                    background-color: {ORANGE_THEME['light_grey']};
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
        
        html_file_name = f"orange_tunisia_article_{template_name}_{current_date}.html"
        
        st.download_button(
            label="Download Article as HTML",
            data=styled_html,
            file_name=html_file_name,
            mime="text/html",
            key="download_html_button"
        )
    else:
        st.info("No article generated yet. Please go to the 'Generate Article' tab to create an article.")

# Sidebar
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/c/c8/Orange_logo.svg", width=100)
    st.title("Settings")
    
    # API Key input
    openai_api_key = st.text_input(
        "OpenAI API Key",
        value=os.getenv("OPENAI_API_KEY", ""),
        type="password",
        help="Enter your OpenAI API key here"
    )
    
    if openai_api_key:
        st.session_state.openai_api_key = openai_api_key
    
    st.divider()
    
    # App information
    st.subheader("About")
    st.write("Orange Tunisia News Scraper v1.0")
    st.write("This app scrapes news from various sources and generates articles using OpenAI's LLM.")
    
    st.divider()
    
    # Instructions
    st.subheader("How to use")
    st.write("1. Select news sources or add custom URLs")
    st.write("2. Click 'Start Scraping' to collect news data")
    st.write("3. Configure article settings and generate")
    st.write("4. View and download your article")