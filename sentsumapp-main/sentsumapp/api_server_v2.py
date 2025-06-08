from fastapi import FastAPI, Depends, HTTPException, Form, status, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.responses import RedirectResponse
import os
import sys
import secrets
sys.path.append("./utils")
from typing import List, Dict, Any
from pydantic import BaseModel

# Import your existing modules
from utils.fetcher import EarningsCallFetcher
from utils.analyzer_v2 import TranscriptAnalyzer
from utils.company_utils import get_company_name
from dotenv import load_dotenv

load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
mongodb_uri = os.getenv("MONGODB_URI_CARL")
api_ninja_key = os.getenv("NINJA_API_KEY")

# Add these environment variables for authentication credentials
# or define them directly in the code (less secure)
USERNAME = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")

app = FastAPI(title="FinSumSent API", root_path="/api")

# Set up CORS for connecting with Svelte frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Svelte dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = TranscriptAnalyzer(openai_api_key, mongodb_uri, api_ninja_key)
security = HTTPBasic()

# Authentication function
def get_current_username(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, USERNAME)
    correct_password = secrets.compare_digest(credentials.password, PASSWORD)
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# Models
class TranscriptData(BaseModel):
    ticker: str

@app.post("/analyze/summary")
async def analyze_summary(
    ticker: str = Form(...),
    username: str = Depends(get_current_username)
):
    """Generate summaries for transcripts"""
    try:
        summaries = analyzer.analyze_transcripts(ticker, "summary", n_jobs=2)
        company_name = get_company_name(ticker)
        for key in summaries:
            summaries[key] = f"### Company Name : {company_name} \n\n" + summaries[key]
        return summaries
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/topics")
async def analyze_topics(
    ticker: str = Form(...),
    username: str = Depends(get_current_username)
):
    """Extract topics from transcripts"""
    try:
        topics = analyzer.analyze_transcripts(ticker, "topics", n_jobs=2)
        company_name = get_company_name(ticker)
        for key in topics:
            topics[key] = f"### Company Name : {company_name} \n\n" + topics[key]
        return topics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/sentiment")
async def analyze_sentiment(
    ticker: str = Form(...),
    username: str = Depends(get_current_username)
):
    """Calculate sentiment for transcripts"""
    try:
        sentiment = analyzer.analyze_transcripts(ticker, "sentiment", n_jobs=2)
        keys_to_keep = [
                'sentiment_score', 
                'sentiment_explanation', 
                'analyst_reaction_score', 
                'analyst_reaction_explanation', 
                'key_sentiment_indicators'
            ]
        filtered_data = {
            quarter: {k: v for k, v in data.items() if k in keys_to_keep}
            for quarter, data in sentiment.items()
        }
        return filtered_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

        
@app.get("/")
async def homepage():
    # return 'Welcome to Devnagri Transliteration API!'
    return RedirectResponse(url="/api/docs")

# If you want the ping endpoint to remain public (no auth)
@app.get("/ping")
async def _ping():
    # Health-checker as expected from https://docs.bugsnag.com/on-premise/clustered/service-ports/#bugsnag-event-server
    return "pong"

# If you want the options handler to remain public (no auth)
@app.options("/{path:path}")
async def options_handler(path: str):
    return {}