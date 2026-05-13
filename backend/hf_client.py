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
        # Try primary model, then fallbacks. Many modern models use TGI endpoint.
        fallback_models = [
            model_id,
            "openai-community/gpt2",
            "google/flan-t5-large",
            "google/flan-t5-xl",
            "bigscience/bloom-560m",
        ]

        last_error = None
        for mid in fallback_models:
            # Try standard endpoint first
            api_url = f"https://api-inference.huggingface.co/models/{mid}"

            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": max_tokens,
                    "temperature": temperature,
                    "return_full_text": False,
                },
            }

            try:
                response = requests.post(api_url, headers=self.headers, json=payload, timeout=30)
                if response.status_code == 404:
                    # Some models use TGI endpoint — try chat completions format
                    tgi_url = f"https://api-inference.huggingface.co/models/{mid}/v1/chat/completions"
                    tgi_payload = {
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    }
                    response = requests.post(tgi_url, headers=self.headers, json=tgi_payload, timeout=30)
                if response.status_code == 404:
                    print(f"HF model '{mid}' not found (404), trying fallback...")
                    last_error = f"404: {mid} not found"
                    continue
                response.raise_for_status()

                result = response.json()
                # Handle TGI chat format
                if isinstance(result, dict) and "choices" in result:
                    return result["choices"][0]["message"]["content"].strip()
                # Handle standard format
                if isinstance(result, list) and len(result) > 0:
                    return result[0].get("generated_text", "").strip()
                elif isinstance(result, dict):
                    return result.get("generated_text", "").strip()
                return ""
            except requests.exceptions.Timeout:
                print(f"HF model '{mid}' timed out, trying fallback...")
                last_error = f"timeout: {mid}"
                continue
            except Exception as e:
                print(f"HF model '{mid}' failed ({e}), trying fallback...")
                last_error = str(e)
                continue

        raise RuntimeError(f"All HF models failed. Last error: {last_error}")
