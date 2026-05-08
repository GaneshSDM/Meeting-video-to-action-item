import whisper
import os

class Transcriber:
    def __init__(self, model_name="base"):
        print(f"Loading Whisper model: {model_name}...")
        self.model = whisper.load_model(model_name)

    def transcribe(self, audio_path):
        """
        Transcribes an audio file to text.
        """
        print(f"Transcribing {audio_path}...")
        try:
            result = self.model.transcribe(audio_path)
            return result['text']
        except Exception as e:
            print(f"Error during transcription: {e}")
            return None

    def save_transcript(self, text, output_path):
        """
        Saves the transcript text to a file.
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text)
            print(f"Transcript saved to {output_path}")
            return output_path
        except Exception as e:
            print(f"Error saving transcript: {e}")
            return None
