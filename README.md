# 📰 News Scraper with Sentiment Analysis & Summarization

## 📌 Overview
This project scrapes news articles from multiple sources, analyzes their sentiment, summarizes the content using an **LLM (T5 model)**, and stores the results in **MongoDB**.

### **🔹 Features**
✅ **Scrapes news from multiple websites**  
✅ **Filters & categorizes articles** based on sentiment (Positive, Neutral, Negative)  
✅ **Uses an AI model for summarization** (Hugging Face's `t5-large`)  
✅ **Stores articles in MongoDB for further analysis**  
✅ **Easily extendable for new news sources**  

---

## ⚡ Setup Guide

### **1️⃣ Install Dependencies**
Make sure you have Python installed (≥ 3.13), then install required packages:
```bash
# Install uv if you don't have it yet
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies using uv
uv sync
```

### **2️⃣ Setup MongoDB**
- Install [MongoDB](https://www.mongodb.com/try/download/community) and start it:
  ```bash
  mongod --dbpath /path/to/your/db
  ```
- If using **MongoDB Atlas (cloud)**, update the environment variables in `.env`:
  ```
  MONGO_URL=your-mongodb-connection-string
  DB_NAME=your-database-name
  COLLECTION_NAME=your-collection-name
  ```

### **3️⃣ Setup Redis for Celery**
- If using Upstash Redis, add these to your `.env` file:
  ```
  UPSTASH_REDIS_URL=your-redis-url
  UPSTASH_REDIS_PASSWORD=your-redis-password
  ```

### **4️⃣ Run the Scraper**
Scrape news headlines from all configured sources manually and then save them to the database:
```bash
python sentiment_analysis_pipeline.py  # Full pipeline with sentiment analysis
python save2db.py
```

### **5️⃣ Run the API**
Start the Flask API to serve the results we got from manually running the above scripts:
```bash
python sentiment_api.py
```

---

## 📁 Project Structure
```
📂 NewsScraper
├── 📄 news_sites.json          # List of websites & their scraping configurations
├── 📄 selector_scraper.py      # Scrapes headlines from news sources
├── 📄 sentiment_analysis_pipeline.py  # Fetches articles, analyzes sentiment, summarizes content
├── 📄 feed_data.py             # Handles sentiment analysis using RoBERTa model
├── 📄 save2db.py               # Saves articles to MongoDB
├── 📄 sentiment_api.py         # Flask API to serve sentiment analysis results
├── 📄 celery_worker.py         # Celery worker for scheduled scraping
├── 📄 pyproject.toml           # Project configuration and dependencies
├── 📄 .env                     # Environment variables (MongoDB, Redis)
├── 📄 README.md                # Setup guide & documentation
```

---

## 🛠️ **Adding New Websites**
To add a new news source:
1. Open `news_sites.json`.
2. Add an entry following this format:
   ```json
   {
      "newsite": {
         "base_url": "https://www.example.com/news",
         "headline_xpath": "//h2[contains(@class, 'headline')]",
         "link_xpath": ".//ancestor::a/@href",
         "dynamic": false
      }
   }
   ```
3. Run `selector_scraper.py` to test.

---

## 🚀 Future Enhancements
- ✅ **Deploy sentiment analysis as an API**
- ✅ **Introduce real-time updates**
- ✅ **Enhance summarization with more advanced LLMs**
- ✅ **Create a web-based dashboard for visualization**
