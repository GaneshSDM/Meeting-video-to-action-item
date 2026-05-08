import os
import requests
from dotenv import load_dotenv

load_dotenv()

class ActionItemProcessor:
    def __init__(self, model_id="mistralai/Mistral-7B-Instruct-v0.2"):
        self.model_id = model_id
        self.api_url = f"https://api-inference.huggingface.co/models/{model_id}"
        self.headers = {"Authorization": f"Bearer {os.getenv('HF_TOKEN')}"}

    def process_transcript(self, transcript):
        """
        Uses an LLM to extract action items per individual member from the transcript.
        """
        prompt = f"""
        The following is a transcript of a meeting. Please identify the action items and assign them to the respective individual members mentioned in the meeting.
        Format the output as a list of action items, each with the person's name and the task.

        Transcript:
        {transcript}

        Action Items:
        """
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 500,
                "temperature": 0.7,
                "return_full_text": False
            }
        }

        print(f"Processing transcript with LLM ({self.model_id})...")
        try:
            response = requests.post(self.api_url, headers=self.headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if isinstance(result, list) and len(result) > 0:
                return result[0].get('generated_text', '').strip()
            return "No action items found or error in processing."
        except Exception as e:
            print(f"Error during LLM processing: {e}")
            return f"Error: {str(e)}"
