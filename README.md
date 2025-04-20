# Orange News Scraper and Article Generator

This tool scrapes information from journalism and news websites, then generates custom articles that Orange (telecommunications company) could use for various purposes, such as internal communications, customer newsletters, or marketing materials.

## Features

- Scrapes multiple news sources using BeautifulSoup and Selenium
- Falls back to Selenium for JavaScript-heavy pages
- Filters content by topic or keyword
- Generates custom articles using OpenAI's GPT models via LangChain
- Supports different article templates for various use cases
- Command-line interface for easy use and automation
- Configurable sources, topics, and article templates

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/orange-news-scraper.git
   cd orange-news-scraper
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Install Chrome WebDriver (required for Selenium):
   - The tool uses webdriver-manager to automatically download and install the appropriate Chrome WebDriver version.
   - Make sure you have Chrome browser installed on your system.

5. Create a `.env` file in the project root with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### Basic Usage

Run the tool with default settings:

```bash
python cli.py
```

This will:
1. Scrape all configured news sources
2. Generate a "news roundup" style article
3. Save the article in the `./output` directory

### Advanced Usage

Specify a topic category:

```bash
python cli.py --topic telecommunications
```

Use a specific article template:

```bash
python cli.py --template business_opportunity
```

Filter by keyword:

```bash
python cli.py --search "5G"
```

Specify custom sources:

```bash
python cli.py --sources https://www.fiercetelecom.com/ https://techcrunch.com/category/mobile/
```

Define a custom topic:

```bash
python cli.py --custom-topic "5G deployment challenges and solutions"
```

Combine multiple options:

```bash
python cli.py --topic technology --template technology_insight --search "artificial intelligence" --output ./custom_output
```

### Command-Line Options

- `--topic`, `-t`: Topic category to focus on (`telecommunications`, `technology`, `business`, `cybersecurity`, `cloud_computing`, or `all`)
- `--template`, `-m`: Article template to use (`news_roundup`, `technology_insight`, `business_opportunity`, `customer_focused`, `press_release`)
- `--sources`, `-s`: Specific URLs to scrape (overrides topic selection)
- `--output`, `-o`: Directory to save output files
- `--custom-topic`, `-c`: Custom topic to focus on (overrides template topic)
- `--search`, `-q`: Keyword to search for in article content
- `--verbose`, `-v`: Enable verbose output (includes saving raw scraped data)

## Configuration

You can customize the tool by modifying the `config.py` file:

- `OPENAI_MODEL`: The OpenAI model to use for article generation
- `NEWS_SOURCES`: Sources to scrape, categorized by topic
- `ARTICLE_TEMPLATES`: Templates for different article types
- `PRIORITY_TOPICS`: Specific topics of interest for Orange

## File Structure

- `news_scraper.py`: Main scraper and generator class
- `config.py`: Configuration settings
- `cli.py`: Command-line interface
- `requirements.txt`: Required Python packages
- `output/`: Directory for generated articles

## Requirements

Create a `requirements.txt` file with these dependencies:

```
openai
langchain
beautifulsoup4
selenium
webdriver-manager
requests
python-dotenv
```

## Limitations

- Some websites may block scraping attempts
- JavaScript-heavy sites may not render properly with Selenium in headless mode
- The quality of generated articles depends on the quality of the scraped content
- OpenAI API usage incurs costs based on token usage

## Future Enhancements

- Add support for authentication to access paywalled content
- Implement content summarization for long articles
- Add image scraping and embedding in generated articles
- Create a web interface for non-technical users
- Implement scheduled scraping and article generation
- Add more article templates and topic categories

## License

[MIT License](LICENSE)