import os
import json
import requests
from typing import List, Optional, Dict, Any

class HFClient:
    """Client for Hugging Face Inference API."""
    
    def __init__(self):
        self.token = os.getenv("HF_TOKEN")
        if not self.token:
            raise ValueError("HF_TOKEN not set in environment variables")
        self.headers = {"Authorization": f"Bearer {self.token}"}

    def transcribe(self, audio_path: str, model_id: str = "openai/whisper-large-v3-turbo") -> str:
        """Transcribe audio using HF Inference API."""
        # Use the correct endpoint for the model
        api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        
        with open(audio_path, "rb") as f:
            data = f.read()
            
        response = requests.post(api_url, headers=self.headers, data=data)
        
        if response.status_code == 404:
            # Try without 'openai/' prefix if the model is hosted differently or use official whisper-large-v3-turbo
            print(f"404 for {model_id}, trying fallback...")
            fallback_id = "whisper-large-v3-turbo" 
            api_url = f"https://api-inference.huggingface.co/models/{fallback_id}"
            response = requests.post(api_url, headers=self.headers, data=data)

        response.raise_for_status()
        
        result = response.json()
        return result.get("text", "")

    def chat_completion(self, prompt: str, model_id: str = "unsloth/Llama-3.3-70B-Instruct-GGUF", max_tokens: int = 2000, temperature: float = 0.2) -> str:
        """Generic chat completion for HF Inference API."""
        api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
            },
        }
        
        response = requests.post(api_url, headers=self.headers, json=payload)
        response.raise_for_status()
        
        result = response.json()
        if isinstance(result, list) and len(result) > 0:
            return result[0].get("generated_text", "").strip()
        elif isinstance(result, dict):
            return result.get("generated_text", "").strip()
        
        return ""
