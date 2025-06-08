from pydantic import BaseModel

class SentimentEvent(BaseModel):
    """Model for structured sentiment analysis output."""
    sentiment_score: float
    sentiment_explanation: str
    
    financial_performance_score: float
    financial_performance_explanation: str
    
    forward_guidance_score: float
    forward_guidance_explanation: str
    
    management_confidence_score: float
    management_confidence_explanation: str
    
    analyst_reaction_score: float
    analyst_reaction_explanation: str
    
    strategic_direction_score: float
    strategic_direction_explanation: str
    
    key_sentiment_indicators: list[str]
    sentiment_shifts: list[str]
    confidence_assessment: str