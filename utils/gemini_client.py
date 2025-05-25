import google.generativeai as genai
import os

def get_gemini_client():
    """
    Initialize and return a Gemini client.
    """
    # Configure the Gemini API
    genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
    
    # Get the model
    model = genai.GenerativeModel('gemini-pro')
    
    return model 