import os
from moviepy import VideoFileClip

def extract_audio(video_path, audio_output_path):
    """
    Extracts audio from a video file and saves it as an mp3.
    """
    print(f"Extracting audio from {video_path}...")
    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_output_path)
        print(f"Audio saved to {audio_output_path}")
        return audio_output_path
    except Exception as e:
        print(f"Error extracting audio: {e}")
        return None
