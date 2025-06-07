"""
Groq API configuration for AI chat functionality.

This module handles Groq API connectivity and configuration for the
HR AI Assistant's conversational AI capabilities.
"""

import os
from typing import Dict, Any, Optional, List
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Groq configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "mixtral-8x7b-32768")
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2048"))
GROQ_TEMPERATURE = float(os.getenv("GROQ_TEMPERATURE", "0.7"))

class GroqConfig:
    """Groq API configuration class"""
    
    def __init__(self):
        self.api_key = GROQ_API_KEY
        self.model = GROQ_MODEL
        self.max_tokens = GROQ_MAX_TOKENS
        self.temperature = GROQ_TEMPERATURE
        self.client = None
        
        if not self.api_key:
            raise ValueError("GROQ_API_KEY environment variable is required")
    
    def get_client_config(self) -> Dict[str, Any]:
        """Get Groq client configuration"""
        return {
            "api_key": self.api_key
        }
    
    def get_completion_config(self) -> Dict[str, Any]:
        """Get default completion configuration"""
        return {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": 1,
            "frequency_penalty": 0,
            "presence_penalty": 0
        }

# Global configuration instance
groq_config = GroqConfig()

def get_groq_client() -> Groq:
    """
    Get Groq client instance.
    
    Returns:
        Groq: Configured Groq client
    """
    if groq_config.client is None:
        try:
            groq_config.client = Groq(api_key=groq_config.api_key)
            print("Groq client initialized successfully")
            
        except Exception as e:
            print(f"Failed to initialize Groq client: {e}")
            raise e
    
    return groq_config.client

def check_groq_connection() -> bool:
    """
    Check if Groq API connection is working.
    
    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_groq_client()
        
        # Test with a simple completion
        response = client.chat.completions.create(
            model=groq_config.model,
            messages=[{"role": "user", "content": "Test connection"}],
            max_tokens=10,
            temperature=0
        )
        
        return response and response.choices and len(response.choices) > 0
        
    except Exception as e:
        print(f"Groq connection failed: {e}")
        return False

async def groq_health_check() -> Dict[str, Any]:
    """
    Perform Groq API health check for monitoring.
    
    Returns:
        dict: Health check status and details
    """
    try:
        client = get_groq_client()
        
        # Test API call
        response = client.chat.completions.create(
            model=groq_config.model,
            messages=[{"role": "user", "content": "Health check"}],
            max_tokens=5,
            temperature=0
        )
        
        if response and response.choices:
            return {
                "status": "healthy",
                "message": "Groq API connection successful",
                "model": groq_config.model,
                "max_tokens": groq_config.max_tokens,
                "temperature": groq_config.temperature
            }
        else:
            return {
                "status": "unhealthy",
                "message": "Groq API response invalid",
                "model": groq_config.model
            }
            
    except Exception as e:
        return {
            "status": "unhealthy",
            "message": f"Groq API connection failed: {str(e)}",
            "model": groq_config.model
        }

# HR-specific system prompts and configurations
HR_SYSTEM_PROMPTS = {
    "general": """You are an AI assistant for an HR department. You help employees with HR-related queries, 
    provide information about company policies, assist with leave requests, and answer questions about 
    employee benefits and procedures. Always be professional, helpful, and empathetic in your responses.
    
    When you don't have specific information, clearly state that and suggest contacting HR directly.
    Always prioritize employee privacy and confidentiality.""",
    
    "leave_management": """You are an HR assistant specializing in leave management. Help employees 
    understand leave policies, calculate leave balances, and guide them through the leave request process.
    Be clear about different types of leave available and their requirements.""",
    
    "policy_questions": """You are an HR assistant specializing in company policies and procedures.
    Provide accurate information from the company handbook and policies. If you're unsure about 
    specific policy details, recommend checking with HR or the employee handbook.""",
    
    "onboarding": """You are an HR assistant helping with employee onboarding. Guide new employees 
    through the onboarding process, explain company procedures, and help them get started in their 
    new role. Be welcoming and comprehensive in your assistance.""",
    
    "benefits": """You are an HR assistant specializing in employee benefits. Help employees 
    understand their benefits package, enrollment procedures, and answer questions about 
    health insurance, retirement plans, and other benefits."""
}

def get_hr_system_prompt(category: str = "general") -> str:
    """
    Get HR-specific system prompt for different categories.
    
    Args:
        category: The category of HR assistance needed
        
    Returns:
        str: Appropriate system prompt for the category
    """
    return HR_SYSTEM_PROMPTS.get(category, HR_SYSTEM_PROMPTS["general"])

# Available Groq models and their capabilities
AVAILABLE_MODELS = {
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B",
        "max_tokens": 32768,
        "description": "Fast and efficient model for general tasks"
    },
    "llama2-70b-4096": {
        "name": "Llama 2 70B",
        "max_tokens": 4096,
        "description": "High-quality responses with good reasoning"
    },
    "gemma-7b-it": {
        "name": "Gemma 7B IT",
        "max_tokens": 8192,
        "description": "Instruction-tuned model for dialogue"
    }
}

def get_available_models() -> Dict[str, Dict[str, Any]]:
    """
    Get list of available Groq models.
    
    Returns:
        dict: Available models and their configurations
    """
    return AVAILABLE_MODELS

def validate_groq_config() -> bool:
    """
    Validate Groq configuration.
    
    Returns:
        bool: True if configuration is valid, False otherwise
    """
    if not groq_config.api_key:
        print("ERROR: GROQ_API_KEY is not set")
        return False
    
    if groq_config.model not in AVAILABLE_MODELS:
        print(f"WARNING: Model '{groq_config.model}' may not be available")
    
    if groq_config.max_tokens > AVAILABLE_MODELS.get(groq_config.model, {}).get("max_tokens", 32768):
        print(f"WARNING: max_tokens exceeds model limit")
    
    if not (0.0 <= groq_config.temperature <= 2.0):
        print(f"WARNING: temperature should be between 0.0 and 2.0")
    
    return True

# Initialize and validate configuration
def init_groq():
    """Initialize Groq configuration and validate settings"""
    try:
        if validate_groq_config():
            if check_groq_connection():
                print("Groq API initialized successfully")
            else:
                print("Groq API connection failed during initialization")
        else:
            print("Groq configuration validation failed")
    except Exception as e:
        print(f"Error initializing Groq: {e}")