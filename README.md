A stock scraper for stocks.

A simple and beginner friendly stock research web app that combines:

-recent up to date company news.
-sentiment analysis.
-market trend analysis using trading terms.
-A simple final recommendation.

this project is made to keep the output simple and understandable and not to complex by returning one of the four signals:

-buy
-dont buy
-sell
-hold

Features:

- Search by stock ticker or company name
- SEC-backed ticker/company lookup
- Recent news collection from supported providers
- News sentiment analysis
- Market data and technical signal analysis
- Simple recommendation output for beginners
- Web interface with clean signal badges
- JSON API for frontend and testing
- CLI version for terminal use

- ## Tech Stack

- Python
- FastAPI
- simple HTML / CSS / JavaScript
- "yfinance"
- "vaderSentiment"
- "requests"

Data Sources:
-This project uses live web data, mainly through APIs and structured public data sources:
-SEC company ticker list
-NewsAPI
-GDELT
-Yahoo Finance via yfinance

how to run this repositry with thorough stepes
1.clone the repositry using your terminal
-git clone https://github.com/zaidzamrik/news-scrapper-for-stocks-.git
-then enter the using the repositry name

2.create a virtual enviroment
-python3 -m venv .venv
-source .venv/bin/activate

3.install required dependencies(if you dont have them)
-python3 -m pip install -r requirements.txt

4.run the web app
-uvicorn web:app --reload --port 8000

5.open using the enviroment ip
-http://127.0.0.1:8000/

Notes:
-this is not financial advice.
-This app is for research and educational use.
-Missing news data can affect the final signal.
-News coverage depends on provider availability and API access.
-The recommendation system is simplified for beginner readability.
