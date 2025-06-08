import time
import logging
import streamlit as st
from pymongo import MongoClient
from utils.prompts import get_system_prompt, get_user_prompt
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from utils.sentiment_model import SentimentEvent
import json

# Configure logging
logger = logging.getLogger("analyzer")

MODEL = "gpt-4o"

class TranscriptAnalyzer:
    def __init__(self, openai_client, mongo_uri=None):
        """
        Initialize the TranscriptAnalyzer with OpenAI client and MongoDB connection.
        
        Args:
            openai_client: The OpenAI client instance
            mongo_uri (str, optional): MongoDB connection URI
        """
        self.openai_client = openai_client
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
        #print(f"Ticker to find: {ticker_to_find}")
        query = {ticker_to_find: {"$exists": True}}
        
        try:
            result = self.collection.find_one(query)
            #print(f"Result: {result}")
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
    
    def analyze_single_transcript(self, transcript_data, prompt_type):
        """
        Analyze a single transcript using OpenAI GPT, with MongoDB caching.
        
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
            #print(f"Checking MongoDB for {ticker} {year} Q{quarter} {mongo_tag}")
            cached_result = self.get_from_mongodb(ticker, year, quarter, mongo_tag)
            #print(f"Cached result: {cached_result}")
            if cached_result:
                return transcript_id, cached_result
        
        # If not in MongoDB, analyze with OpenAI
        system_content = get_system_prompt(prompt_type)
        user_content = get_user_prompt(prompt_type, transcript_data)
        
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
        
        # Add retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                if prompt_type == "sentiment":
                    sentiment_response = self.openai_client.beta.chat.completions.parse(
                                model="gpt-4o",
                                messages=messages,
                                #temperature=0.2,
                                response_format=SentimentEvent
                            )
                    event = sentiment_response.choices[0].message.parsed
                    result = json.loads(event.json())
                else:
                    gpt_response = self.openai_client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        #temperature=0.2,
                        stream=False,
                    )
                    
                    result = gpt_response.choices[0].message.content
                    
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