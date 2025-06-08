import time
import logging
import streamlit as st
from pymongo import MongoClient
from utils.prompts import get_system_prompt, get_user_prompt
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from utils.sentiment_model import SentimentEvent
import json
from google import genai
from google.genai.types import GenerateContentConfig

# Configure logging
logger = logging.getLogger("analyzer")

# Gemini model to use
GEMINI_MODEL = "gemini-2.0-flash"

class TranscriptAnalyzer:
    def __init__(self, gemini_api_key, mongo_uri=None):
        """
        Initialize the TranscriptAnalyzer with Gemini client and MongoDB connection.
        
        Args:
            gemini_api_key: The Gemini API key
            mongo_uri (str, optional): MongoDB connection URI
        """
        self.gemini_client = genai.Client(api_key=gemini_api_key)
        self.mongo_client = None
        self.db = None
        self.collection = None
        
        # Connect to MongoDB if URI is provided
        if mongo_uri:
            try:
                self.mongo_client = MongoClient(mongo_uri)
                self.db = self.mongo_client["callpulsedb"]
                self.collection = self.db["callpulsecollection"]
                logger.info("Connected to MongoDB")
            except Exception as e:
                logger.error(f"Failed to connect to MongoDB: {e}")
                st.warning(f"Failed to connect to MongoDB: {e}")
    
    def get_from_mongodb(self, ticker, year, quarter, analysis_type):
        """
        Try to retrieve analysis results from MongoDB.
        
        Args:
            ticker (str): The ticker symbol
            year (int): The year
            quarter (int): The quarter
            analysis_type (str): The type of analysis ("SUMMARY", "TOPIC", or "SENTIMENT")
            
        Returns:
            str or None: The analysis result if found, None otherwise
        """
        if self.collection is None:
            return None
        ticker = ticker.replace(".","-")
        ticker_to_find = f"{ticker}_{year}_Q{quarter}_{analysis_type}"
        query = {ticker_to_find: {"$exists": True}}
        
        try:
            result = self.collection.find_one(query)
            if result:
                logger.info(f"Found {analysis_type} for {ticker} {year} Q{quarter} in MongoDB")
                return result[ticker_to_find]
            else:
                logger.info(f"No {analysis_type} found for {ticker} {year} Q{quarter} in MongoDB")
                return None
        except Exception as e:
            logger.error(f"Error retrieving from MongoDB: {e}")
            return None
    
    def save_to_mongodb(self, ticker, year, quarter, analysis_type, data):
        """
        Save analysis results to MongoDB.
        
        Args:
            ticker (str): The ticker symbol
            year (int): The year
            quarter (int): The quarter
            analysis_type (str): The type of analysis ("SUMMARY", "TOPIC", or "SENTIMENT")
            data (str): The analysis result
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        if self.collection is None:
            return False
        ticker = ticker.replace(".","-")
        ticker_key = f"{ticker}_{year}_Q{quarter}_{analysis_type}"
        document = {ticker_key: data}
        
        try:
            result = self.collection.insert_one(document)
            logger.info(f"Saved {analysis_type} for {ticker} {year} Q{quarter} to MongoDB")
            return True
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            return False
    
    def _get_sentiment_response_schema(self):
        """
        Get the response schema for structured sentiment analysis output.
        
        Returns:
            dict: The response schema for Gemini structured output
        """
        return {
            "type": "OBJECT",
            "properties": {
                "sentiment_score": {"type": "NUMBER"},
                "sentiment_explanation": {"type": "STRING"},
                "financial_performance_score": {"type": "NUMBER"},
                "financial_performance_explanation": {"type": "STRING"},
                "forward_guidance_score": {"type": "NUMBER"},
                "forward_guidance_explanation": {"type": "STRING"},
                "management_confidence_score": {"type": "NUMBER"},
                "management_confidence_explanation": {"type": "STRING"},
                "analyst_reaction_score": {"type": "NUMBER"},
                "analyst_reaction_explanation": {"type": "STRING"},
                "strategic_direction_score": {"type": "NUMBER"},
                "strategic_direction_explanation": {"type": "STRING"},
                "key_sentiment_indicators": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "sentiment_shifts": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"}
                },
                "confidence_assessment": {"type": "STRING"}
            },
            "required": [
                "sentiment_score",
                "sentiment_explanation",
                "financial_performance_score",
                "financial_performance_explanation",
                "forward_guidance_score",
                "forward_guidance_explanation",
                "management_confidence_score",
                "management_confidence_explanation",
                "analyst_reaction_score",
                "analyst_reaction_explanation",
                "strategic_direction_score",
                "strategic_direction_explanation",
                "key_sentiment_indicators",
                "sentiment_shifts",
                "confidence_assessment"
            ]
        }
    
    def analyze_single_transcript(self, transcript_data, prompt_type):
        """
        Analyze a single transcript using Gemini, with MongoDB caching.
        
        Args:
            transcript_data (dict): The transcript data
            prompt_type (str): The type of analysis to perform ("summary", "topics", or "sentiment")
            
        Returns:
            tuple: (transcript_id, analysis_result)
        """
        ticker = transcript_data['ticker']
        year = transcript_data['year']
        quarter = transcript_data['quarter']
        transcript_id = f"{ticker}_{year}_Q{quarter}"
        
        # Determine the MongoDB tag based on prompt_type
        mongo_tag = {
            "summary": "SUMMARY",
            "topics": "TOPIC",
            "sentiment": "SENTIMENT"
        }.get(prompt_type, "UNKNOWN")
        
        # Try to get from MongoDB first
        if self.collection is not None:
            cached_result = self.get_from_mongodb(ticker, year, quarter, mongo_tag)
            if cached_result:
                return transcript_id, cached_result
        
        # If not in MongoDB, analyze with Gemini
        system_content = get_system_prompt(prompt_type)
        user_content = get_user_prompt(prompt_type, transcript_data)
        
        # Add retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if prompt_type == "sentiment":
                    # Use structured output for sentiment analysis
                    config = GenerateContentConfig(
                        system_instruction=system_content,
                        temperature=0.5,
                        response_mime_type="application/json",
                        response_schema=self._get_sentiment_response_schema()
                    )
                    
                    response = self.gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        config=config,
                        contents=user_content
                    )
                    
                    # Parse the JSON response
                    result = json.loads(response.text)
                else:
                    # For summary and topics, use regular text generation
                    config = GenerateContentConfig(
                        system_instruction=system_content,
                        temperature=0.5
                    )
                    
                    response = self.gemini_client.models.generate_content(
                        model=GEMINI_MODEL,
                        config=config,
                        contents=user_content
                    )
                    
                    result = response.text
                    
                # Save to MongoDB if connected
                if self.collection is not None:
                    self.save_to_mongodb(ticker, year, quarter, mongo_tag, result)
                
                return transcript_id, result
                
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    sleep_time = 2 ** attempt
                    logger.warning(f"Error processing {transcript_id}, retrying in {sleep_time}s... Error: {str(e)}")
                    time.sleep(sleep_time)
                else:
                    logger.error(f"Failed to process {transcript_id} after {max_retries} attempts: {str(e)}")
                    return transcript_id, f"ERROR: {str(e)}"

    def analyze_transcripts(self, transcript_data_list, prompt_type, n_jobs=4):
        """
        Analyze multiple transcripts in parallel using joblib.
        
        Args:
            transcript_data_list (list): List of transcript data dictionaries
            prompt_type (str): The type of analysis to perform ("summary", "topics", or "sentiment")
            n_jobs (int): Number of parallel jobs to run
            
        Returns:
            dict: Dictionary of transcript_id to analysis result
        """
        if not transcript_data_list:
            return {}
            
        # Using joblib to process transcripts in parallel
        results = Parallel(n_jobs=n_jobs, backend="threading")(
            delayed(self.analyze_single_transcript)(transcript_data, prompt_type)
            for transcript_data in tqdm(transcript_data_list, desc=f"Processing {prompt_type} analysis")
        )
        
        # Convert list of tuples to dictionary
        return dict(results)