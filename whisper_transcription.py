import whisper
import json
import os
import tempfile
from typing import Dict, List, Optional, Tuple
from datetime import timedelta

class WhisperTranscriber:
    def __init__(self, model_size: str = "base"):
        """
        Initialize the Whisper transcription model.
        
        Args:
            model_size: Size of the Whisper model to use ('tiny', 'base', 'small', 'medium', 'large')
        """
        self.model = whisper.load_model(model_size)
        self.model_size = model_size
        print(f"Whisper model '{model_size}' loaded successfully")
    
    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> Dict:
        """
        Transcribe audio file using Whisper.
        
        Args:
            audio_path: Path to the audio file
            language: Optional language code (e.g., 'en', 'fr', etc.)
            
        Returns:
            Dictionary containing the transcription results
        """
        # Set transcription options
        options = {}
        if language:
            options["language"] = language
        
        # Run transcription
        result = self.model.transcribe(audio_path, **options)
        return result
    
    def transcribe_with_timestamps(self, audio_path: str, language: Optional[str] = None) -> Tuple[str, List[Dict]]:
        """
        Transcribe audio with detailed timestamp information.
        
        Args:
            audio_path: Path to the audio file
            language: Optional language code
            
        Returns:
            Tuple of (full_text, segments) where segments contain timestamp information
        """
        result = self.transcribe_audio(audio_path, language)
        
        # Format timestamps for better readability
        segments = []
        for segment in result["segments"]:
            segments.append({
                "id": segment["id"],
                "start": str(timedelta(seconds=segment["start"])),
                "end": str(timedelta(seconds=segment["end"])),
                "text": segment["text"].strip(),
            })
        
        return result["text"], segments
    
    def save_transcript(self, audio_path: str, output_dir: str, include_timestamps: bool = True, 
                      language: Optional[str] = None) -> str:
        """
        Transcribe audio and save the transcript to files.
        
        Args:
            audio_path: Path to the audio file
            output_dir: Directory to save the transcript files
            include_timestamps: Whether to include timestamps in the output
            language: Optional language code
            
        Returns:
            Path to the saved transcript file
        """
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Get base filename without extension
        base_filename = os.path.splitext(os.path.basename(audio_path))[0]
        
        # Transcribe the audio
        text, segments = self.transcribe_with_timestamps(audio_path, language)
        
        # Save text transcript
        txt_path = os.path.join(output_dir, f"{base_filename}.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(text)
        
        # Save detailed transcript with timestamps
        if include_timestamps:
            json_path = os.path.join(output_dir, f"{base_filename}.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump({
                    "text": text,
                    "segments": segments,
                    "model_size": self.model_size
                }, f, indent=2, ensure_ascii=False)
        
        return txt_path

    def get_segment_by_question(self, transcript_data: Dict, question: str) -> Optional[Dict]:
        """
        Find the most relevant segment in a transcript based on a question.
        
        This is a simple keyword-based search. In a real application, you would
        use semantic search or other NLP techniques.
        
        Args:
            transcript_data: Transcript data with segments
            question: Question to search for in the transcript
            
        Returns:
            Most relevant segment or None if no match found
        """
        # Simple implementation: check for keyword matches
        # In a real application, use embeddings and semantic search
        
        # Remove common question words to focus on key terms
        question_words = ["what", "when", "where", "who", "how", "why", "is", "are", "did", "do", "does"]
        question_lower = question.lower()
        
        # Remove question words
        for word in question_words:
            question_lower = question_lower.replace(f" {word} ", " ")
        
        # Split into keywords
        keywords = [k.strip() for k in question_lower.split() if len(k.strip()) > 3]
        
        # Score each segment based on keyword matches
        best_segment = None
        best_score = 0
        
        for segment in transcript_data["segments"]:
            segment_text = segment["text"].lower()
            score = sum(1 for keyword in keywords if keyword in segment_text)
            
            if score > best_score:
                best_score = score
                best_segment = segment
        
        return best_segment if best_score > 0 else None

# Example usage:
if __name__ == "__main__":
    # Initialize transcriber
    transcriber = WhisperTranscriber(model_size="base")
    
    # Transcribe an audio file
    audio_path = "sample_audio.wav"
    transcript, segments = transcriber.transcribe_with_timestamps(audio_path)
    
    # Print the transcript
    print("Transcript:")
    print(transcript)
    
    # Print the first few segments with timestamps
    print("\nSegments with timestamps:")
    for segment in segments[:3]:
        print(f"{segment['start']} -> {segment['end']}: {segment['text']}")