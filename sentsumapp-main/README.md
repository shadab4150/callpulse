# CallPulse App : Earnings Call Analyzer
App to summarize, analyse sentiment, extract topics from earnings call.

A comprehensive financial analysis application that automatically fetches, processes, and analyzes earnings call transcripts for S&P 500 companies. This tool leverages advanced AI models (OpenAI GPT-4 and Google Gemini) to extract meaningful insights from quarterly earnings calls, providing summaries, topic extraction, and sentiment analysis.

## 🎯 Project Overview

The Earnings Call Analyzer transforms raw earnings call transcripts into actionable financial intelligence through three core analysis types:

- **Summarization**: Generates concise, structured summaries of earnings calls highlighting key financial metrics, strategic initiatives, and management guidance
- **Topic Extraction**: Identifies and extracts the most important discussion topics from analyst Q&A sessions
- **Sentiment Analysis**: Performs multi-dimensional sentiment scoring across financial performance, management confidence, analyst reactions, and strategic direction

## 🏗️ Architecture

The project consists of multiple interfaces and deployment options:

### Core Components

- **FastAPI Backend** (`api_server_v2.py`): RESTful API server with authentication for programmatic access
- **Streamlit Applications**: 
  - OpenAI-powered interface (`streamlit_app_openai.py`)
  - Gemini-powered interface (`streamlit_app_gemini.py`)
- **Analysis Engine**: Modular analyzers supporting both OpenAI and Google Gemini models
- **Data Fetching**: Automated transcript retrieval from earnings call data sources
- **Caching Layer**: MongoDB integration for performance optimization and cost reduction

### Key Features

- **Multi-Model Support**: Choose between OpenAI GPT-4 and Google Gemini 2.0 Flash
- **Parallel Processing**: Concurrent analysis of multiple quarters for improved performance
- **Smart Caching**: MongoDB-based caching prevents redundant API calls and reduces costs
- **Authentication**: Secure access controls for both web and API interfaces
- **Real-time Processing**: Live progress tracking and timing metrics
- **Company Database**: Comprehensive S&P 500 company ticker and name mapping

## 🚀 Getting Started

### Prerequisites

Before setting up the project, ensure you have:

- Python 3.8 or higher
- MongoDB instance (local or cloud)
- API keys for your chosen AI provider:
  - OpenAI API key (for GPT-4 support)
  - Google Gemini API key (for Gemini support)
- API Ninja key (for earnings transcript data)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/earnings-call-analyzer.git
   cd earnings-call-analyzer
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment Configuration**
   
   Create a `.env` file in the project root with your API credentials:
   ```env
   # AI Model APIs (choose one or both)
   OPENAI_API_KEY=your_openai_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   
   # Data Source
   NINJA_API_KEY=your_api_ninja_key_here
   
   # Database
   MONGODB_URI_CARL=your_mongodb_connection_string
   
   # Authentication (for API and Streamlit)
   USERNAME=your_username
   PASSWORD=your_password
   ```

4. **Streamlit Secrets** (for Streamlit apps)
   
   Create `.streamlit/secrets.toml`:
   ```toml
   [passwords]
   your_username = "your_password"
   ```

## 💻 Usage

### Option 1: Streamlit Web Interface

The Streamlit interface provides an intuitive web-based experience for analyzing earnings calls.

**For OpenAI GPT-4:**
```bash
streamlit run streamlit_app_openai.py
```

**For Google Gemini:**
```bash
streamlit run streamlit_app_gemini.py
```

**Using the Interface:**
1. Navigate to the provided local URL (typically `http://localhost:8501`)
2. Log in with your configured credentials
3. Enter an S&P 500 ticker symbol (e.g., "AAPL", "MSFT", "GOOGL")
4. Follow the step-by-step process:
   - **Step 1**: Fetch transcripts for the last 4 quarters
   - **Step 2**: Generate comprehensive summaries
   - **Step 3**: Extract key discussion topics
   - **Step 4**: Analyze sentiment across multiple dimensions

### Option 2: FastAPI REST Service

The FastAPI backend provides programmatic access for integration with other systems.

**Start the API server:**
```bash
uvicorn api_server_v2:app --host 0.0.0.0 --port 8505
```

**API Endpoints:**

- `POST /api/analyze/summary` - Generate earnings call summaries
- `POST /api/analyze/topics` - Extract discussion topics
- `POST /api/analyze/sentiment` - Perform sentiment analysis
- `GET /api/docs` - Interactive API documentation

**Example Usage:**
```python
import requests
import base64

# Prepare authentication
credentials = base64.b64encode("username:password".encode()).decode()
headers = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/x-www-form-urlencoded"
}

# Analyze sentiment for Apple's earnings
response = requests.post(
    "http://localhost:8505/api/analyze/sentiment",
    headers=headers,
    data={"ticker": "AAPL"}
)

sentiment_data = response.json()
```

### Option 3: Python Integration

For direct integration into Python applications:

```python
from utils.analyzer_v2 import TranscriptAnalyzer

# Initialize the analyzer
analyzer = TranscriptAnalyzer()

# Analyze a company's earnings
summaries = analyzer.analyze_transcripts("AAPL", "summary", n_jobs=2)
topics = analyzer.analyze_transcripts("AAPL", "topics", n_jobs=2)
sentiment = analyzer.analyze_transcripts("AAPL", "sentiment", n_jobs=2)
```

## 📊 Analysis Output

### Summary Analysis
Structured summaries include:
- Financial performance highlights with key metrics
- Business segment analysis and revenue trends
- Strategic initiatives and forward guidance
- Risk factors and challenges
- Management responses to analyst questions

### Topic Extraction
Identifies the 10 most important topics discussed during Q&A sessions, focusing on:
- Specific business metrics and KPIs
- Strategic initiatives and market expansion
- Operational challenges and solutions
- Competitive positioning and market trends

### Sentiment Analysis
Multi-dimensional sentiment scoring (scale: -1.0 to +1.0):
- **Overall Sentiment**: Holistic assessment of call tone
- **Financial Performance**: Management's characterization of results
- **Forward Guidance**: Confidence in future outlook statements
- **Management Confidence**: Executive tone and communication style
- **Analyst Reaction**: Question patterns and follow-up intensity
- **Strategic Direction**: Enthusiasm for long-term initiatives

## 🛠️ Technical Details

### Performance Optimizations
- **Parallel Processing**: Concurrent analysis using joblib for faster processing
- **Smart Caching**: MongoDB-based result caching to avoid redundant API calls
- **Exponential Backoff**: Robust retry logic for API failures
- **Memory Management**: Efficient data structures for large transcript processing

### AI Model Integration
- **OpenAI GPT-4**: Structured output using Pydantic models for sentiment analysis
- **Google Gemini 2.0**: JSON schema-based structured generation
- **Prompt Engineering**: Specialized prompts optimized for financial content analysis
- **Error Handling**: Comprehensive exception handling and graceful degradation

### Data Management
- **Transcript Storage**: Local caching with JSON format for quick access
- **Company Mapping**: Efficient ticker-to-company name resolution
- **Result Persistence**: MongoDB storage with organized document structure
- **Data Validation**: Input sanitization and output validation

## 📁 Project Structure

```
sentsumapp/
├── api_server_v2.py           # FastAPI backend service
├── streamlit_app_openai.py    # Streamlit interface for OpenAI
├── streamlit_app_gemini.py    # Streamlit interface for Gemini
├── utils/
│   ├── analyzer.py            # OpenAI-based analyzer
│   ├── analyzer_gemini.py     # Gemini-based analyzer
│   ├── analyzer_v2.py         # Enhanced analyzer with fetching
│   ├── fetcher.py             # Earnings transcript fetcher
│   ├── prompts.py             # AI model prompts
│   ├── sentiment_model.py     # Pydantic models for structured output
│   ├── company_utils.py       # Company name resolution utilities
│   └── stock-tickers.csv      # S&P 500 company database
├── style2.css                 # Custom Streamlit styling
├── test-api.py               # API testing utilities
└── README.md                 # Project documentation
```

## 🔧 Configuration

### Model Selection
Choose between AI providers based on your needs:
- **OpenAI GPT-4**: Superior reasoning and analysis quality
- **Google Gemini 2.0**: Faster processing and competitive quality

### Processing Parameters
- **Parallel Jobs**: Adjust `n_jobs` parameter for concurrent processing
- **Retry Logic**: Configurable retry attempts with exponential backoff
- **Cache Behavior**: Enable/disable MongoDB caching per analysis type

### Authentication
- **Streamlit**: Username/password authentication via secrets
- **FastAPI**: HTTP Basic Authentication with environment variables
- **API Keys**: Secure storage in environment variables only

## 🤝 Contributing

Contributions to improve the Earnings Call Analyzer! Here's how you can help:

1. **Fork the repository** and create a feature branch
2. **Add new analysis types** by extending the analyzer classes
3. **Improve prompt engineering** for better AI model responses
4. **Enhance the UI** with additional visualizations or features
5. **Add support for new data sources** beyond the current transcript API
6. **Submit pull requests** with clear descriptions of changes

## 🆘 Support

If you encounter issues or have questions:

1. **Check the documentation** in this README for common setup steps
2. **Review the API documentation** at `/api/docs` when running the FastAPI server
3. **Examine log outputs** from the Streamlit interface for debugging information
4. **Open an issue** on GitHub with detailed error descriptions and reproduction steps

## 🙏 Acknowledgments

This project leverages several powerful technologies and data sources:
- OpenAI GPT-4 for advanced language understanding
- Google Gemini for efficient AI processing
- API Ninja for earnings transcript data
- MongoDB for scalable data storage
- Streamlit for rapid web application development
- FastAPI for high-performance API services

---

*Built with ❤️ for the financial analysis community*
