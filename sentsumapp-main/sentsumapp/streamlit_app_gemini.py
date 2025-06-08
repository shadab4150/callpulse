import streamlit as st
import os
import logging
from google import genai
from dotenv import load_dotenv
import secrets
import hmac
import os
import pandas as pd
import time
from datetime import datetime, timedelta

# Import utility modules
from utils.fetcher import EarningsCallFetcher
from utils.analyzer_gemini import TranscriptAnalyzer
#import yfinance as yf
# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("earnings_app")

st.set_page_config(
    page_title="Earnings Call Analyzer",
    page_icon="📊",
    layout="wide"
)
# Streamlit App
st.markdown("<center><h1>Earnings Call Analyzer</h1></center>", unsafe_allow_html=True)
st.markdown("<center>Analyze earnings call transcripts for S&P 500 companies</center>",unsafe_allow_html=True)


def check_password():
    """Returns `True` if the user had a correct password."""

    def login_form():
        """Form with widgets to collect user information"""
        with st.form("Credentials"):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            st.form_submit_button("Log in", on_click=password_entered)

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in st.secrets[
            "passwords"
        ] and hmac.compare_digest(
            st.session_state["password"],
            st.secrets.passwords[st.session_state["username"]],
        ):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the username or password.
            del st.session_state["username"]
        else:
            st.session_state["password_correct"] = False

    # Return True if the username +  password is validated.
    if st.session_state.get("password_correct", False):
        return True

    # Show inputs for username + password.
    login_form()
    if "password_correct" in st.session_state:
        st.error("😕 User not known or password incorrect")
    return False

if not check_password():
    st.stop()
    
@st.cache_data
def load_data(PATH):
    df = pd.read_csv(PATH)
    return df.set_index('Symbol')['Name'].to_dict()

PATH = "stock-tickers.csv"
symbol_to_name = load_data(PATH)

def get_company_name(ticker):
    return symbol_to_name.get(ticker, ticker)


#custome css style button
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("style2.css")

# Get API keys from environment variables
api_ninja_key = os.getenv("NINJA_API_KEY")
gemini_api_key = os.getenv("GEMINI_API_KEY")
mongodb_uri = os.getenv("MONGODB_URI_CARL")

# Initialize clients with environment variables if available
if api_ninja_key:
    fetcher = EarningsCallFetcher(api_key=api_ninja_key)
else:
    fetcher = None
    st.warning("NINJA_API_KEY not found in .env file. Please add it to use the transcript fetching functionality.")

if gemini_api_key:
    # Initialize the transcript analyzer with Gemini API key and MongoDB connection
    analyzer = TranscriptAnalyzer(gemini_api_key, mongodb_uri)
else:
    analyzer = None
    st.warning("GEMINI_API_KEY not found in .env file. Please add it to use the analysis functionality.")

# Session state initialization
if "fetched_data" not in st.session_state:
    st.session_state.fetched_data = None
if "summaries" not in st.session_state:
    st.session_state.summaries = {}
if "topics" not in st.session_state:
    st.session_state.topics = {}
if "sentiments" not in st.session_state:
    st.session_state.sentiments = {}
# Initialize timing data in session state
if "timing_data" not in st.session_state:
    st.session_state.timing_data = {}

# Helper function to format time duration
def format_duration(seconds):
    """Format duration in seconds to a readable string"""
    if seconds < 60:
        return f"{seconds:.1f} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        return f"{int(minutes)}m {int(remaining_seconds)}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        return f"{int(hours)}h {int(remaining_minutes)}m"

# Main content
col1, col2 = st.columns([1, 3])

with col1:
    # Search form
    st.header("Search")
    ticker = st.text_input("Enter S&P 500 Ticker Symbol", value="AAPL")
    
    # Number of parallel jobs slider
    n_jobs = 4
    
    # Display timing information if available
    if st.session_state.timing_data:
        st.divider()
        st.subheader("⏱️ Processing Times")
        for operation, duration in st.session_state.timing_data.items():
            st.metric(operation, format_duration(duration))
    
    # Step 1: Fetch Data
    if st.button("Step 1: Fetch Data"):
        if fetcher is None:
            st.error("API Ninja key not available. Please add it to the .env file.")
        else:
            # Clear previous timing data when fetching new data
            st.session_state.timing_data = {}
            
            start_time = time.time()
            with st.spinner("Fetching transcripts..."):
                try:
                    results = fetcher.get_last_n_quarters(ticker, 4)
                    if results:
                        keys_to_keep = ['date', 'transcript_split', 'ticker', 'year', 'quarter']
                        st.session_state.fetched_data = [{k: d[k] for k in keys_to_keep if k in d} for d in results]
                        
                        # Record fetch time
                        fetch_duration = time.time() - start_time
                        st.session_state.timing_data["Fetch Data"] = fetch_duration
                        
                        st.success(f"Successfully fetched data for {ticker} (last 4 quarters) in {format_duration(fetch_duration)}")
                    else:
                        st.error(f"No transcripts found for {ticker}")
                except Exception as e:
                    st.error(f"Error fetching data: {str(e)}")
    
    # Step 2: Summarize Data
    if st.button("Step 2: Summarize Data"):
        if analyzer is None:
            st.error("Gemini API key not available. Please add it to the .env file.")
        elif st.session_state.fetched_data is None:
            st.error("Please fetch data first")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Summarizing transcripts in parallel..."):
                try:
                    status_text.text("Starting summarization...")
                    
                    # Use the new parallel processing functionality
                    st.session_state.summaries = analyzer.analyze_transcripts(
                        st.session_state.fetched_data,
                        prompt_type="summary",
                        n_jobs=n_jobs
                    )
                    
                    # Record summarization time
                    summary_duration = time.time() - start_time
                    st.session_state.timing_data["Summarize"] = summary_duration
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    st.success(f"Successfully summarized all transcripts in {format_duration(summary_duration)}")
                except Exception as e:
                    st.error(f"Error summarizing data: {str(e)}")
                finally:
                    progress_bar.empty()
                    status_text.empty()
    
    # Step 3: Extract Topics
    if st.button("Step 3: Extract Topics"):
        if analyzer is None:
            st.error("Gemini API key not available. Please add it to the .env file.")
        elif st.session_state.fetched_data is None:
            st.error("Please fetch data first")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Extracting topics in parallel..."):
                try:
                    status_text.text("Starting topic extraction...")
                    
                    # Use the new parallel processing functionality
                    st.session_state.topics = analyzer.analyze_transcripts(
                        st.session_state.fetched_data,
                        prompt_type="topics",
                        n_jobs=n_jobs
                    )
                    
                    # Record topic extraction time
                    topics_duration = time.time() - start_time
                    st.session_state.timing_data["Extract Topics"] = topics_duration
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    st.success(f"Successfully extracted topics from all transcripts in {format_duration(topics_duration)}")
                except Exception as e:
                    st.error(f"Error extracting topics: {str(e)}")
                finally:
                    progress_bar.empty()
                    status_text.empty()
    
    # Step 4: Calculate Sentiment
    if st.button("Step 4: Calculate Sentiment"):
        if analyzer is None:
            st.error("Gemini API key not available. Please add it to the .env file.")
        elif st.session_state.fetched_data is None:
            st.error("Please fetch data first")
        else:
            start_time = time.time()
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            with st.spinner("Calculating sentiment in parallel..."):
                try:
                    status_text.text("Starting sentiment analysis...")
                    
                    # Use the new parallel processing functionality
                    st.session_state.sentiments = analyzer.analyze_transcripts(
                        st.session_state.fetched_data,
                        prompt_type="sentiment",
                        n_jobs=n_jobs
                    )
                    
                    # Record sentiment analysis time
                    sentiment_duration = time.time() - start_time
                    st.session_state.timing_data["Calculate Sentiment"] = sentiment_duration
                    
                    progress_bar.progress(100)
                    status_text.empty()
                    st.success(f"Successfully calculated sentiment for all transcripts in {format_duration(sentiment_duration)}")
                except Exception as e:
                    st.error(f"Error calculating sentiment: {str(e)}")
                finally:
                    progress_bar.empty()
                    status_text.empty()
    
    # Add total time display if all steps completed
    if len(st.session_state.timing_data) >= 4:
        st.divider()
        total_time = sum(st.session_state.timing_data.values())
        st.metric("Total Processing Time", format_duration(total_time), delta=None)

# Display results in the larger column
with col2:
    st.header("Results")
    
    # Add timing summary at the top if available
    if st.session_state.timing_data and len(st.session_state.timing_data) > 1:
        with st.expander("📊 Processing Time Summary", expanded=False):
            timing_df = pd.DataFrame(
                [(op, format_duration(duration)) for op, duration in st.session_state.timing_data.items()],
                columns=["Operation", "Duration"]
            )
            st.dataframe(timing_df, use_container_width=True, hide_index=True)
            
            # Create a bar chart for timing visualization
            timing_chart_data = pd.DataFrame(
                [(op, duration) for op, duration in st.session_state.timing_data.items()],
                columns=["Operation", "Seconds"]
            )
            st.bar_chart(timing_chart_data.set_index("Operation"))
    
    if st.session_state.fetched_data:
        # Create tabs for different analysis types
        result_tabs = st.tabs(["Summary", "Topics", "Sentiment"])
        
        with result_tabs[0]:  # Summary tab
            if st.session_state.summaries:
                # Sort data by year and quarter in descending order
                sorted_data = sorted(st.session_state.fetched_data, 
                                    key=lambda x: (x['year'], x['quarter']), 
                                    reverse=True)
                
                #Create an expander for each quarter
                for data in sorted_data:
                    transcript_id = f"{data['ticker']}_{data['year']}_Q{data['quarter']}"
                    expander_title = f"Summary {data['ticker']} {data['year']} Q{data['quarter']}"
                    
                    with st.expander(expander_title):
                        company_name = get_company_name(data["ticker"])
                        if company_name!=None:
                            start_text = f"### Company Name : {company_name} \n\n"
                        else:
                            start_text = f"### Company Name : {ticker} \n\n"
                        if transcript_id in st.session_state.summaries:
                            st.write(start_text+st.session_state.summaries[transcript_id].replace("```markdown","\n"))
                        else:
                            st.info("Summary not available for this quarter. Please Click on Summarize Data Button.")
            else:
                st.info("Summaries not available. Please run the summarization step.")
        
        with result_tabs[1]:  # Topics tab
            if st.session_state.topics:
                # Sort data by year and quarter in descending order
                sorted_data = sorted(st.session_state.fetched_data, 
                                    key=lambda x: (x['year'], x['quarter']), 
                                    reverse=True)
                
                # Create an expander for each quarter
                for data in sorted_data:
                    transcript_id = f"{data['ticker']}_{data['year']}_Q{data['quarter']}"
                    expander_title = f"Extracted Topics {data['ticker']} {data['year']} Q{data['quarter']}"
                    
                    with st.expander(expander_title):
                        if transcript_id in st.session_state.topics:
                            company_name = get_company_name(data["ticker"])
                            if company_name!=None:
                                start_text = f"### Company Name : {company_name} \n\n"
                            else:
                                start_text = f"### Company Name : {ticker} \n\n"
                            st.write(start_text+st.session_state.topics[transcript_id].replace("```markdown","\n"))
                        else:
                            st.info("Topics not available for this quarter. Please Click On Extract Topics Button.")
            else:
                st.info("Topics not available. Please run the topic extraction step.")
        
        with result_tabs[2]:  # Sentiment tab
            if st.session_state.sentiments:
                # Sort data by year and quarter in descending order
                sorted_data = sorted(st.session_state.fetched_data, 
                                    key=lambda x: (x['year'], x['quarter']), 
                                    reverse=True)
                
                # Create an expander for each quarter
                #print(st.session_state.sentiments)
                try:
                    col1 = []
                    col2 = []
                    col3 = []
                    for cdata in sorted_data:
                        transcript_id = f"{cdata['ticker']}_{cdata['year']}_Q{cdata['quarter']}"
                        col1.append(f"{cdata['year']}_Q{cdata['quarter']}")
                        col2.append(st.session_state.sentiments[transcript_id]["sentiment_score"])
                        col3.append(st.session_state.sentiments[transcript_id]["analyst_reaction_score"])
                        
                    
                    chart_data = pd.DataFrame(
                                    {
                                        "quarter": col1,
                                        "sentiment_score": col2,
                                        "analyst_reaction_score":col3,
                                    }
                                )
                    #bar chart
                    st.bar_chart(
                                chart_data,
                                x="quarter",
                                y=["sentiment_score","analyst_reaction_score"],
                                color=["#FF0000", "#0000FF"],  # Optional
                                stack=False,
                                
                            )
                except Exception as e:
                    print(e)
                    
                for data in sorted_data:
                    sentiment_text = ""
                    company_name = get_company_name(data["ticker"])
                    if company_name!=None:
                        start_text = f"### Company Name : {company_name} \n\n"
                    else:
                        start_text = f"### Company Name : {ticker} \n\n"
                    sentiment_text += start_text
                    transcript_id = f"{data['ticker']}_{data['year']}_Q{data['quarter']}"
                    expander_title = f"Sentiment Analysis : {data['ticker']} {data['year']} Q{data['quarter']}"
                    #sentiment_text += f"### {data['ticker']} {data['year']} Q{data['quarter']}\n\n"
                    try:
                        sentiment_text += f"**Sentiment Score:** {st.session_state.sentiments[transcript_id]['sentiment_score']}\n\n"
                        sentiment_text += f"**Sentiment Analysis:** {st.session_state.sentiments[transcript_id]['sentiment_explanation']}\n\n"
                        sentiment_text += f"**Analyst Reaction Score:** {st.session_state.sentiments[transcript_id]['analyst_reaction_score']}\n\n"
                        sentiment_text += f"**Analyst Reaction:** {st.session_state.sentiments[transcript_id]['analyst_reaction_explanation']}\n\n"
                        ksi = st.session_state.sentiments[transcript_id]['key_sentiment_indicators']
                        ksi = "\n\n- ".join(ksi)
                        sentiment_text += f"**Key Sentiment Indicators:**\n\n- {ksi}\n"
                    except Exception as e:
                        print(e)


                    with st.expander(expander_title):
                        if transcript_id in st.session_state.sentiments:
                            st.write(sentiment_text)
                        else:
                            st.info("Sentiment analysis not available for this quarter. Please Click on Calculate Sentiment Button.")
            else:
                st.info("Sentiment analysis not available. Please run the sentiment calculation step.")
    else:
        st.info("No data available. Please fetch data first.")