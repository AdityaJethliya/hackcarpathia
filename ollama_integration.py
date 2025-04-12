import requests
import json
import logging
from typing import Dict, List, Optional, Union, Any

logger = logging.getLogger("hearclear_api")

class OllamaClient:
    """
    Client for interacting with Ollama API to use DeepSeek-LLM for 
    semantic search and question answering.
    """
    
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "deepseek-llm"):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: Base URL for Ollama API
            model: Model name to use (default: deepseek-llm)
        """
        self.base_url = base_url
        self.model = model
        logger.info(f"Initialized OllamaClient with model: {model}")
        
        # Test connection to Ollama
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                available_models = [m["name"] for m in models]
                if self.model in available_models:
                    logger.info(f"Successfully connected to Ollama. Model '{self.model}' is available.")
                else:
                    logger.warning(f"Model '{self.model}' not found in available models: {available_models}")
            else:
                logger.warning(f"Could not connect to Ollama API: {response.status_code}")
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {str(e)}")
    
    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Generate a response using the DeepSeek-LLM model.
        
        Args:
            prompt: The prompt to send to the model
            system_prompt: Optional system prompt for instruction
            
        Returns:
            Generated text response
        """
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        
        if system_prompt:
            payload["system"] = system_prompt
        
        try:
            logger.debug(f"Sending prompt to Ollama: {prompt[:100]}...")
            response = requests.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "")
            else:
                logger.error(f"Error from Ollama API: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            logger.error(f"Error calling Ollama API: {str(e)}")
            return ""
    
    def find_answer_in_transcript(self, 
                                  transcript_data: Dict[str, Any], 
                                  question: str) -> Dict[str, Any]:
        """
        Find the most relevant answer segment in a transcript using DeepSeek-LLM.
        
        Args:
            transcript_data: The transcript data with segments
            question: The question to answer
            
        Returns:
            Dict with answer information including:
            - matched_segment: The best matching segment
            - confidence: Confidence score
            - metadata: Additional metadata about the match
        """
        segments = transcript_data.get("segments", [])
        if not segments:
            logger.warning("No segments found in transcript data")
            return {
                "matched_segment": None,
                "confidence": 0.0,
                "metadata": {
                    "reasoning": "No transcript segments were found to analyze.",
                    "question_analysis": "",
                    "match_method": "semantic"
                }
            }
        
        # Create a context with the transcript segments
        context = "Transcript segments:\n\n"
        for i, segment in enumerate(segments):
            context += f"Segment {i+1} [Time: {segment['start']} - {segment['end']}]: {segment['text']}\n\n"
        
        # Create a prompt for the LLM to analyze
        system_prompt = """
        You are an AI assistant helping to find the most relevant segment from a transcript that answers a user's question.
        Analyze each segment carefully and choose the ONE most relevant segment that best answers the question.
        Provide your reasoning and explain why this segment is the best match.
        """
        
        prompt = f"""
        Question: {question}
        
        {context}
        
        Based on the transcript segments above, identify the segment that best answers the question.
        Return your answer in the following structured JSON format without any additional commentary:
        
        {{
            "best_segment_id": <segment number>,
            "confidence": <float between 0 and 1>,
            "reasoning": "<explain why this segment answers the question>",
            "question_analysis": "<brief analysis of the key information being sought>"
        }}
        
        Only return the JSON object, nothing else.
        """
        
        # Get response from Ollama
        response = self.generate(prompt, system_prompt)
        logger.debug(f"Ollama response: {response[:200]}...")
        
        # Extract JSON from response
        try:
            # Find JSON block in the response (might be surrounded by markdown or other text)
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                result = json.loads(json_str)
                
                # Get the segment ID and convert to zero-based index
                segment_id = result.get("best_segment_id", 0)
                if isinstance(segment_id, str) and segment_id.isdigit():
                    segment_id = int(segment_id)
                if isinstance(segment_id, int) and segment_id > 0:
                    segment_id -= 1  # Convert to zero-based index
                
                # Check if segment_id is valid
                if segment_id is not None and 0 <= segment_id < len(segments):
                    matched_segment = segments[segment_id]
                    
                    return {
                        "matched_segment": matched_segment,
                        "confidence": result.get("confidence", 0.7),
                        "metadata": {
                            "reasoning": result.get("reasoning", ""),
                            "question_analysis": result.get("question_analysis", ""),
                            "match_method": "semantic",
                            "original_response": response
                        }
                    }
            
            # If JSON parsing fails, fall back to keyword-based matching
            logger.warning(f"Failed to parse Ollama response as JSON, falling back to keyword matching")
            return self._fallback_keyword_matching(segments, question)
            
        except Exception as e:
            logger.error(f"Error parsing Ollama response: {str(e)}")
            return self._fallback_keyword_matching(segments, question)
    
    def find_and_extract_audio_answer(self, 
                                 transcript_data: Dict[str, Any],
                                 original_audio_path: str,
                                 question: str,
                                 buffer_ms: int = 500) -> Dict[str, Any]:
        """
        Find the answer to a question in a transcript and extract the corresponding audio segment.
        
        Args:
            transcript_data: The transcript data with segments
            original_audio_path: Path to the original audio file
            question: The question to answer
            buffer_ms: Buffer in milliseconds to add before and after the segment (default: 500ms)
            
        Returns:
            Dict containing:
            - answer_info: Information about the matched segment and analysis
            - audio_segment: Extracted audio segment as bytes
            - audio_format: Format of the audio segment (e.g., 'wav')
            - start_time: Start time in seconds
            - end_time: End time in seconds
        """
        import os
        import tempfile
        import io
        from pydub import AudioSegment
        
        # First, find the answer segment using the existing method
        answer_info = self.find_answer_in_transcript(transcript_data, question)
        
        # If no matching segment found, return early
        if not answer_info["matched_segment"]:
            logger.info("No matching segment found for question")
            return {
                "answer_info": answer_info,
                "audio_segment": None,
                "audio_format": None,
                "start_time": None,
                "end_time": None
            }
        
        try:
            # Extract timestamp information
            segment = answer_info["matched_segment"]
            
            # Convert timestamps from HH:MM:SS format to seconds
            start_time = 0
            end_time = 0
            
            # Parse the start timestamp
            start_parts = segment["start"].split(":")
            if len(start_parts) == 3:  # Format is HH:MM:SS
                start_time = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
            elif len(start_parts) == 2:  # Format is MM:SS
                start_time = int(start_parts[0]) * 60 + float(start_parts[1])
            
            # Parse the end timestamp
            end_parts = segment["end"].split(":")
            if len(end_parts) == 3:  # Format is HH:MM:SS
                end_time = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
            elif len(end_parts) == 2:  # Format is MM:SS
                end_time = int(end_parts[0]) * 60 + float(end_parts[1])
            
            logger.info(f"Extracting audio segment from {start_time}s to {end_time}s")
            
            # Check if the audio file exists
            if not os.path.exists(original_audio_path):
                logger.error(f"Audio file not found: {original_audio_path}")
                raise FileNotFoundError(f"Audio file not found: {original_audio_path}")
            
            # Load the audio file using pydub
            audio = AudioSegment.from_file(original_audio_path)
            
            # Convert seconds to milliseconds for pydub
            start_ms = int(start_time * 1000)
            end_ms = int(end_time * 1000)
            
            # Ensure end time is not beyond audio length
            if end_ms > len(audio):
                logger.warning(f"End time ({end_ms}ms) exceeds audio length ({len(audio)}ms)")
                end_ms = len(audio)
            
            # Add buffer before and after if possible
            if start_ms >= buffer_ms:
                start_ms -= buffer_ms
            
            if end_ms + buffer_ms <= len(audio):
                end_ms += buffer_ms
            
            # Extract the segment
            segment_audio = audio[start_ms:end_ms]
            
            # Export to in-memory file
            buffer = io.BytesIO()
            segment_audio.export(buffer, format="wav")
            buffer.seek(0)
            audio_bytes = buffer.read()
            
            logger.info(f"Successfully extracted audio segment ({len(audio_bytes)} bytes)")
            
            # Update the answer info with timestamp information in seconds
            answer_info["metadata"]["timestamp"] = {
                "start_raw": segment["start"],
                "end_raw": segment["end"],
                "start_seconds": start_time,
                "end_seconds": end_time,
                "duration_seconds": end_time - start_time,
                "start_with_buffer_seconds": start_ms / 1000,
                "end_with_buffer_seconds": end_ms / 1000
            }
            
            return {
                "answer_info": answer_info,
                "audio_segment": audio_bytes,
                "audio_format": "wav",
                "start_time": start_time,
                "end_time": end_time
            }
            
        except Exception as e:
            logger.error(f"Error extracting audio segment: {str(e)}", exc_info=True)
            # Return answer info but with no audio
            return {
                "answer_info": answer_info,
                "audio_segment": None,
                "audio_format": None,
                "error": str(e),
                "start_time": None,
                "end_time": None
            }
    
    def _fallback_keyword_matching(self, segments, question):
        """Fallback to simple keyword matching if LLM response parsing fails"""
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
        
        for segment in segments:
            segment_text = segment["text"].lower()
            score = sum(1 for keyword in keywords if keyword in segment_text)
            
            if score > best_score:
                best_score = score
                best_segment = segment
        
        return {
            "matched_segment": best_segment,
            "confidence": best_score / len(keywords) if keywords else 0,
            "metadata": {
                "reasoning": f"Matched {best_score} keywords from the question",
                "question_analysis": f"Keywords extracted: {', '.join(keywords)}",
                "match_method": "keyword_fallback"
            }
        }