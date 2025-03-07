import json
import requests
import time
import unicodedata
import re
import traceback
import datetime
from lxml import html
from transformers import pipeline
from selector_scraper import scrape_static_website, scrape_dynamic_website
from feed_data import analyze_keywords
from save2db import save_articles_to_db
import ftfy

# Load news site configurations
with open("news_sites.json", "r", encoding="utf-8") as file:
    WEBSITE_CONFIG = json.load(file)

# Load the T5 Summarization Model
summarizer = pipeline("summarization", model="t5-large")


# ✅ Fix Encoding Issues & Normalize Text
def clean_text(text):
    """Fix encoding issues, restore apostrophes, and normalize text properly."""
    try:
        text = unicodedata.normalize("NFKC", text)  # Normalize Unicode characters
        text = text.encode("utf-8", "ignore").decode("utf-8")  # Fix encoding artifacts

        # Restore contractions (e.g., "Trump s" → "Trump's")
        text = re.sub(r"\b([A-Za-z]+)\s([smtdl])\b", r"\1'\2", text)

        # Remove non-ASCII characters
        text = re.sub(r"[^\x00-\x7F]+", " ", text)
        text = re.sub(r"\s+", " ", text).strip()  # Remove extra spaces
        return text
    except Exception as e:
        print(f"❌ Error cleaning text: {e}")
        return text


# ✅ Convert The Guardian's relative URLs to absolute
def fix_guardian_link(link):
    if not link.startswith("http"):
        return "https://www.theguardian.com" + link.split("#")[0]  # Remove #comments
    return link


# ✅ Filter Out Non-Article Headlines
def filter_headlines(headlines):
    """Remove unwanted headlines such as videos, short titles, and advertisements."""
    filtered = []
    for headline in headlines:
        cleaned_headline = clean_text(headline)

        # ❌ Skip short headlines
        if len(cleaned_headline.split()) <= 2:
            continue

        # ❌ Skip "Video" & "Advertisement"
        if "video" in cleaned_headline.lower() or "advertisement" in cleaned_headline.lower():
            continue

        filtered.append(cleaned_headline)
    return filtered


# ✅ Extract Article Images
def extract_image(tree):
    """Extracts the first available image from the article page."""
    try:
        img_url = tree.xpath("//meta[@property='og:image']/@content")
        return img_url[0] if img_url else None
    except Exception as e:
        print(f"❌ Error extracting image: {e}")
        return None


# ✅ Fetch Full Article Content & Image
def fetch_full_article(url):
    """Fetches the full content and image of an article given its URL."""
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
    }
    try:
        session = requests.Session()
        response = session.get(url, headers=HEADERS)

        # Handle 403 Forbidden by retrying
        if response.status_code == 403:
            print(f"⚠️ Warning: Access denied for {url}. Trying alternative method...")
            time.sleep(2)  
            response = session.get(url, headers=HEADERS, cookies=session.cookies)

        response.raise_for_status()
        tree = html.fromstring(response.content)

        # Extract main article text
        paragraphs = tree.xpath("//p/text()")
        content = " ".join(paragraphs).strip()

        # Extract image if available
        image_url = extract_image(tree)

        return content if content else "Content not available", image_url
    except Exception as e:
        print(f"❌ Error fetching article from {url}: {e}")
        return "Content not available", None

def clean_summary(text):
    """Cleans up summary text, fixing encoding issues, capitalization, and punctuation."""
    try:
        # ✅ Fix character encoding issues (removes `â` and restores proper characters)
        text = ftfy.fix_text(text)

        # ✅ Normalize Unicode characters
        text = unicodedata.normalize("NFKC", text)

        # ✅ Remove excessive spaces and fix punctuation spacing
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\s([.,!?;:])', r'\1', text)  # Remove space before punctuation

        # ✅ Capitalize first letter of every sentence
        text = re.sub(r'(^|[.!?]\s+)([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)

        # ✅ Ensure proper apostrophe formatting ("Trump s" → "Trump’s")
        text = re.sub(r"\b([A-Za-z]+)\s([smtdl])\b", r"\1'\2", text)

        # ✅ Ensure the summary ends properly with a period
        if text and text[-1] not in ".!?":
            text += "."

        return text.strip()

    except Exception as e:
        print(f"❌ Error cleaning summary: {e}")
        return text

def generate_summary(text):
    """Generates a cleaned and formatted summary using Hugging Face's T5 model."""
    try:
        if not isinstance(text, str):
            text = str(text)  # Force conversion to string

        text = text.strip()
        if not text:
            return "No content available to summarize."

        input_length = len(text.split())
        if input_length < 10:
            return text.capitalize()  

        input_text = "summarize: " + text[:2048]  
        summary = summarizer(input_text, max_length=150, min_length=50, do_sample=False)
        
        cleaned_summary = clean_summary(summary[0]["summary_text"])  
        return cleaned_summary

    except Exception as e:
        print(f"❌ Error generating summary: {e}")
        print(traceback.format_exc())
        return clean_summary(text[:300] + "...")  


# ✅ Sentiment Analysis & Processing
def process_news():
    """Scrapes headlines, fetches full articles, analyzes sentiment, and organizes results."""
    results = {"positive": [], "neutral": [], "negative": []}

    for site, config in WEBSITE_CONFIG.items():
        print(f"📰 Scraping: {site}")
        base_url = config["base_url"]
        headline_xpath = config["headline_xpath"]
        link_xpath = config["link_xpath"]

        # Choose dynamic or static scraping
        if config["dynamic"]:
            articles = scrape_dynamic_website(base_url, headline_xpath, link_xpath)
        else:
            articles = scrape_static_website(base_url, headline_xpath, link_xpath)

        seen_articles = set()
        filtered_articles = []
        for a in articles:
            cleaned_headline = clean_text(a["headline"])
            cleaned_link = fix_guardian_link(a["link"]) if site == "guardian" else a["link"]

            if cleaned_link in seen_articles:
                continue  

            seen_articles.add(cleaned_link)
            filtered_articles.append({"headline": cleaned_headline, "link": cleaned_link})

        for article in filtered_articles:
            headline = clean_text(article["headline"])
            url = article["link"]

            print(f"🔍 Fetching article: {headline} ({url})")
            full_content, image_url = fetch_full_article(url)

            if full_content == "Content not available":
                continue

            sentiment_response = analyze_keywords(headline)
            sentiment = sentiment_response.get("final_sentiment", "neutral")

            summary = generate_summary(full_content)

            article_data = {
                "headline": headline,
                "url": url,
                "sentiment": sentiment,
                "summary": summary,
                "image": image_url,
                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()  # ✅ Timestamp for sorting
            }

            results[sentiment].append(article_data)
            print(f"{sentiment.capitalize()}: {headline}")

            time.sleep(2)  # Add a short delay to prevent rate limiting

    with open("sentiment_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=4, default=str)  # ✅ Convert datetime to string


    print("\n✅ Sentiment Analysis Complete! Results saved in `sentiment_results.json`")

    # save_articles_to_db(results)

if __name__ == "__main__":
    process_news()