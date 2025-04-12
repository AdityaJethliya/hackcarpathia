from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
import librosa
import numpy as np
import io
import soundfile as sf
import tempfile
import os
import uuid
import json
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Union, Any
import uvicorn
import base64
from pydub import AudioSegment  # Added for audio segment extraction

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("hearclear_api.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("hearclear_api")

# Try to import Ollama integration
try:
    from ollama_integration import OllamaClient
    ollama_client = OllamaClient()
    OLLAMA_AVAILABLE = True
    logger.info("Successfully initialized Ollama client for DeepSeek-LLM")
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("Ollama integration not available, falling back to basic keyword matching")

# If you've created the advanced audio processing module
try:
    from audio_processing import enhance_audio, get_speech_stats
    logger.info("Successfully imported audio_processing module")
except ImportError:
    logger.warning("audio_processing module not found, using fallback implementation")
    # Fallback to basic implementation if module not available
    def enhance_audio(audio_data, sr, speed_factor=0.75, volume_factor=1.5, remove_noise=False, enhance_clarity=False):
        # Time stretching (slower speech)
        y_stretched = librosa.effects.time_stretch(audio_data, rate=speed_factor)
        
        # Simple noise reduction
        if remove_noise:
            noise_sample = y_stretched[:int(sr/2)]
            noise_profile = np.mean(np.abs(librosa.stft(noise_sample)), axis=1)
            D = librosa.stft(y_stretched)
            mag = np.abs(D)
            phase = np.angle(D)
            mag = np.maximum(mag - noise_profile[:, np.newaxis] * 1.5, 0)
            D_denoised = mag * np.exp(1j * phase)
            y_stretched = librosa.istft(D_denoised)
        
        # Volume adjustment
        y_enhanced = y_stretched * volume_factor
        
        # Prevent clipping
        if np.max(np.abs(y_enhanced)) > 1.0:
            y_enhanced = y_enhanced / np.max(np.abs(y_enhanced))
            
        return y_enhanced
    
    def get_speech_stats(audio_data, sr):
        rms = librosa.feature.rms(y=audio_data)[0]
        return {"average_volume": np.mean(rms)}

# Try to import Whisper transcription module
try:
    from whisper_transcription import WhisperTranscriber
    transcriber = WhisperTranscriber(model_size="base")
    WHISPER_AVAILABLE = True
    logger.info("Successfully imported WhisperTranscriber module")
except ImportError:
    WHISPER_AVAILABLE = False
    logger.warning("WhisperTranscriber module not found, transcription endpoints will be disabled")

# Initialize FastAPI app
app = FastAPI(title="HearClear API", description="Speech enhancement API for elderly users")

# Create middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())
    logger.info(f"Request {request_id} started: {request.method} {request.url.path}")
    
    start_time = time.time()
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"Request {request_id} completed: {response.status_code} in {process_time:.3f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request {request_id} failed in {process_time:.3f}s: {str(e)}")
        raise

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create a directory for storing processed files
UPLOADS_DIR = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)
logger.info(f"Uploads directory created at: {UPLOADS_DIR}")

# Create a directory for storing transcripts
TRANSCRIPTS_DIR = os.path.join(os.getcwd(), "transcripts")
os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)
logger.info(f"Transcripts directory created at: {TRANSCRIPTS_DIR}")

# Data models
class AudioProcessingResult(BaseModel):
    file_id: str
    original_filename: str
    enhanced_filename: str
    processing_stats: Dict
    duration_seconds: float

class TranscriptionResult(BaseModel):
    file_id: str
    text: str
    segments: List[Dict]

class QuestionResult(BaseModel):
    answer_segment: Optional[Dict]
    start_time: Optional[float]
    end_time: Optional[float]
    text: Optional[str]
    question_text: Optional[str] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

# Root endpoint
@app.get("/")
async def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "Welcome to HearClear API", "version": "1.0.0"}

# Audio enhancement endpoint
@app.post("/enhance-audio/", response_model=AudioProcessingResult)
async def enhance_audio_endpoint(
    audio_file: UploadFile = File(...),
    speed_factor: float = Form(0.75),  # Default to 75% speed
    volume_factor: float = Form(1.5),  # Default to 150% volume
    remove_noise: bool = Form(False),  # Noise removal toggle
    enhance_clarity: bool = Form(False),  # Speech clarity enhancement
):
    """
    Enhances audio by adjusting speed, volume, and optionally removing noise.
    
    - speed_factor: 0.5-1.0 (lower value = slower speech)
    - volume_factor: 1.0-2.0 (higher value = louder speech)
    - remove_noise: True/False (apply noise reduction)
    - enhance_clarity: True/False (enhance speech clarity)
    
    Returns metadata about the processed file
    """
    file_id = str(uuid.uuid4())
    logger.info(f"Audio enhancement requested [file_id: {file_id}] - Original filename: {audio_file.filename}")
    logger.debug(f"Parameters - speed: {speed_factor}, volume: {volume_factor}, remove_noise: {remove_noise}, enhance_clarity: {enhance_clarity}")
    
    try:
        # Create a temporary file to store the uploaded audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            logger.debug(f"Temporary file created: {temp_path} - Size: {len(content)} bytes")
            
        # Load the audio file
        logger.debug(f"Loading audio file with librosa")
        y, sr = librosa.load(temp_path, sr=None)
        logger.debug(f"Audio loaded - Duration: {len(y)/sr:.2f}s, Sample rate: {sr}Hz")
        
        # Get original duration
        duration_seconds = librosa.get_duration(y=y, sr=sr)
        
        # Get speech statistics before enhancement
        logger.debug("Getting original speech statistics")
        original_stats = get_speech_stats(y, sr)
        
        # Apply audio enhancements
        logger.info(f"Applying audio enhancements [file_id: {file_id}]")
        enhanced_audio = enhance_audio(
            y, sr, 
            speed_factor=speed_factor, 
            volume_factor=volume_factor, 
            remove_noise=remove_noise,
            enhance_clarity=enhance_clarity
        )
        
        # Get speech statistics after enhancement
        logger.debug("Getting enhanced speech statistics")
        enhanced_stats = get_speech_stats(enhanced_audio, sr)
        
        # Save the enhanced file
        original_filename = audio_file.filename or "audio.wav"
        base_name = os.path.splitext(original_filename)[0]
        enhanced_filename = f"{base_name}_enhanced_{file_id}.wav"
        enhanced_path = os.path.join(UPLOADS_DIR, enhanced_filename)
        
        logger.debug(f"Saving enhanced audio to {enhanced_path}")
        sf.write(enhanced_path, enhanced_audio, sr, format='wav')
        
        # Clean up temporary file
        os.unlink(temp_path)
        logger.debug(f"Temporary file removed: {temp_path}")
        
        # Create response
        result = AudioProcessingResult(
            file_id=file_id,
            original_filename=original_filename,
            enhanced_filename=enhanced_filename,
            processing_stats={
                "original": original_stats,
                "enhanced": enhanced_stats,
                "speed_factor": speed_factor,
                "volume_factor": volume_factor,
                "noise_removal_applied": remove_noise,
                "clarity_enhancement_applied": enhance_clarity
            },
            duration_seconds=duration_seconds
        )
        
        logger.info(f"Audio enhancement completed [file_id: {file_id}] - Output: {enhanced_filename}")
        return result
        
    except Exception as e:
        logger.error(f"Error in enhance_audio_endpoint [file_id: {file_id}]: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

# Get enhanced audio file
@app.get("/download-enhanced/{file_id}")
async def download_enhanced(file_id: str):
    """
    Download an enhanced audio file by its ID
    """
    logger.info(f"Download requested for file_id: {file_id}")
    try:
        # Find the file
        for filename in os.listdir(UPLOADS_DIR):
            if file_id in filename:
                file_path = os.path.join(UPLOADS_DIR, filename)
                logger.info(f"File found: {filename} - Serving for download")
                return FileResponse(
                    file_path, 
                    media_type="audio/wav",
                    filename=filename
                )
        
        logger.warning(f"File not found for file_id: {file_id}")
        raise HTTPException(status_code=404, detail="Enhanced audio file not found")
    except Exception as e:
        logger.error(f"Error in download_enhanced for file_id {file_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving file: {str(e)}")

# Transcription endpoint (if Whisper is available)
# Transcription endpoint (if Whisper is available)
if WHISPER_AVAILABLE:
    @app.post("/transcribe/{file_id}", response_model=TranscriptionResult)
    async def transcribe_audio(
        file_id: str,
        background_tasks: BackgroundTasks,
        language: Optional[str] = None
    ):
        """
        Transcribe an enhanced audio file using Whisper
        """
        logger.info(f"Transcription requested for file_id: {file_id}, language: {language or 'auto'}")
        try:
            # Find the enhanced file
            file_path = None
            for filename in os.listdir(UPLOADS_DIR):
                if file_id in filename:
                    file_path = os.path.join(UPLOADS_DIR, filename)
                    logger.debug(f"Found file for transcription: {filename}")
                    break
            
            if not file_path:
                logger.warning(f"No file found for transcription with file_id: {file_id}")
                raise HTTPException(status_code=404, detail="Enhanced audio file not found")
            
            # Transcribe the audio
            logger.info(f"Starting transcription with Whisper [file_id: {file_id}]")
            text, segments = transcriber.transcribe_with_timestamps(file_path, language)
            logger.debug(f"Transcription completed - {len(segments)} segments, {len(text)} characters")
            
            # Save transcript
            transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{file_id}.json")
            transcript_data = {
                "file_id": file_id,
                "text": text,
                "segments": segments,
                "created_at": datetime.now().isoformat()
            }
            
            with open(transcript_path, "w", encoding="utf-8") as f:
                json.dump(transcript_data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Transcript saved to {transcript_path}")
            
            logger.info(f"Transcription completed for file_id: {file_id}")
            return TranscriptionResult(
                file_id=file_id,
                text=text,
                segments=segments
            )
            
        except Exception as e:
            logger.error(f"Error in transcribe_audio for file_id {file_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error transcribing audio: {str(e)}")
    
    @app.post("/query-transcript/{file_id}", response_model=QuestionResult)
    async def query_transcript(
        file_id: str,
        question: str = Query(..., description="Question to ask about the transcript"),
        use_llm: bool = Query(True, description="Whether to use DeepSeek-LLM for semantic search")
    ):
        """
        Query a transcript using natural language
        
        The endpoint can use DeepSeek-LLM for semantic search (if available) or fall back
        to keyword matching. The response includes metadata about the matching process.
        """
        logger.info(f"Transcript query requested for file_id: {file_id}, question: '{question}'")
        try:
            # Find the transcript file
            transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{file_id}.json")
            if not os.path.exists(transcript_path):
                logger.warning(f"Transcript not found for file_id: {file_id}")
                raise HTTPException(status_code=404, detail="Transcript not found")
            
            # Load the transcript
            with open(transcript_path, "r", encoding="utf-8") as f:
                transcript_data = json.load(f)
            logger.debug(f"Transcript loaded from {transcript_path}")
            
            # Find relevant segment - use Ollama if available and requested
            if OLLAMA_AVAILABLE and use_llm:
                logger.info(f"Using DeepSeek-LLM to find answer to question: '{question}'")
                result = ollama_client.find_answer_in_transcript(transcript_data, question)
                segment = result.get("matched_segment")
                confidence = result.get("confidence", 0.0)
                metadata = result.get("metadata", {})
            else:
                logger.info(f"Using keyword matching to find answer to question: '{question}'")
                segment = transcriber.get_segment_by_question(transcript_data, question)
                confidence = 0.5  # Default confidence for keyword matching
                metadata = {"match_method": "keyword"}
            
            if segment:
                logger.info(f"Answer found in segment at {segment['start']} - {segment['end']} (confidence: {confidence:.2f})")
                
                # Convert timestamp to seconds
                start_time = 0
                end_time = 0
                
                # Parse timestamps
                start_parts = segment["start"].split(":")
                if len(start_parts) == 3:  # Format is HH:MM:SS
                    start_time = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
                elif len(start_parts) == 2:  # Format is MM:SS
                    start_time = int(start_parts[0]) * 60 + float(start_parts[1])
                
                end_parts = segment["end"].split(":")
                if len(end_parts) == 3:  # Format is HH:MM:SS
                    end_time = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
                elif len(end_parts) == 2:  # Format is MM:SS
                    end_time = int(end_parts[0]) * 60 + float(end_parts[1])
                
                # Add timestamps to metadata
                metadata["timestamp"] = {
                    "start_raw": segment["start"],
                    "end_raw": segment["end"],
                    "start_seconds": start_time,
                    "end_seconds": end_time,
                    "duration_seconds": end_time - start_time
                }
                
                # Add request info to metadata
                metadata["request"] = {
                    "file_id": file_id,
                    "question": question,
                    "use_llm": use_llm and OLLAMA_AVAILABLE,
                    "timestamp": datetime.now().isoformat()
                }
                
                return QuestionResult(
                    answer_segment=segment,
                    start_time=start_time,
                    end_time=end_time,
                    text=segment["text"],
                    question_text=question,
                    confidence=confidence,
                    metadata=metadata
                )
            else:
                logger.info(f"No relevant answer found for question: '{question}'")
                return QuestionResult(
                    answer_segment=None,
                    start_time=None,
                    end_time=None,
                    text="No relevant answer found",
                    question_text=question,
                    confidence=0.0,
                    metadata={
                        "match_method": "semantic" if OLLAMA_AVAILABLE and use_llm else "keyword",
                        "request": {
                            "file_id": file_id,
                            "question": question,
                            "use_llm": use_llm and OLLAMA_AVAILABLE,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                )
                
        except Exception as e:
            logger.error(f"Error in query_transcript for file_id {file_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error querying transcript: {str(e)}")
    
    @app.post("/query-transcript-audio/{file_id}", response_model=QuestionResult)
    async def query_transcript_audio(
        file_id: str,
        question_audio: UploadFile = File(...),
        language: Optional[str] = None,
        use_llm: bool = Query(True, description="Whether to use DeepSeek-LLM for semantic search")
    ):
        """
        Accept an audio recording of a question, transcribe it, and find the answer in the transcript.
        
        This endpoint uses Whisper to transcribe the question and then uses DeepSeek-LLM (if available)
        or keyword matching to find the most relevant answer segment.
        """
        logger.info(f"Audio question received for file_id: {file_id}, language: {language or 'auto'}")
        
        try:
            # Validation - check file_id format
            if not file_id or not isinstance(file_id, str):
                raise ValueError(f"Invalid file_id: {file_id}")
            
            # Find the transcript file - with better error message
            transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{file_id}.json")
            if not os.path.exists(transcript_path):
                logger.warning(f"Transcript not found for file_id: {file_id} at path: {transcript_path}")
                raise HTTPException(status_code=404, detail=f"Transcript not found for file_id: {file_id}")
            
            # Verify the audio file is provided and not empty
            if not question_audio or not question_audio.filename:
                raise ValueError("No audio file provided or filename is empty")
            
            content = await question_audio.read()
            if not content or len(content) < 100:  # Basic check for valid audio content
                raise ValueError(f"Audio file content is too small or empty: {len(content)} bytes")
            
            # Save the question audio to a temporary file with explicit error handling
            temp_file = None
            question_audio_path = None
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                temp_file.write(content)
                temp_file.flush()
                question_audio_path = temp_file.name
                temp_file.close()
                logger.debug(f"Question audio saved to temporary file: {question_audio_path} ({len(content)} bytes)")
            except Exception as file_error:
                logger.error(f"Error saving audio file: {str(file_error)}")
                raise ValueError(f"Failed to save audio file: {str(file_error)}")
            
            # Verify the temporary file exists and is not empty
            if not os.path.exists(question_audio_path) or os.path.getsize(question_audio_path) < 100:
                raise ValueError(f"Temporary audio file is missing or too small: {question_audio_path}")
            
            # Transcribe the question audio with better error handling
            if not WHISPER_AVAILABLE:
                os.unlink(question_audio_path)
                logger.error("Whisper transcription is not available")
                raise HTTPException(status_code=501, detail="Whisper transcription is not available")
            
            try:
                logger.info(f"Transcribing question audio with Whisper")
                question_text, _ = transcriber.transcribe_with_timestamps(question_audio_path, language)
                logger.info(f"Question transcribed: '{question_text}'")
            except Exception as whisper_error:
                logger.error(f"Error transcribing audio with Whisper: {str(whisper_error)}", exc_info=True)
                # Clean up the temporary file
                if question_audio_path and os.path.exists(question_audio_path):
                    os.unlink(question_audio_path)
                raise ValueError(f"Failed to transcribe audio question: {str(whisper_error)}")
            
            # Clean up the temporary file
            if question_audio_path and os.path.exists(question_audio_path):
                os.unlink(question_audio_path)
                logger.debug(f"Temporary file removed: {question_audio_path}")
            
            # If question text is empty, return an error
            if not question_text or len(question_text.strip()) == 0:
                raise ValueError("Question transcription was empty. Please speak clearly and try again.")
            
            # Load the transcript with explicit error handling
            try:
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                logger.debug(f"Transcript loaded from {transcript_path}")
            except json.JSONDecodeError as json_error:
                logger.error(f"Invalid JSON in transcript file: {str(json_error)}")
                raise ValueError(f"Transcript file contains invalid JSON: {str(json_error)}")
            except Exception as file_error:
                logger.error(f"Error loading transcript file: {str(file_error)}")
                raise ValueError(f"Failed to load transcript file: {str(file_error)}")
            
            # Check transcript has segments
            if "segments" not in transcript_data or not transcript_data["segments"]:
                logger.error(f"No segments found in transcript data for file_id: {file_id}")
                raise ValueError(f"No segments found in transcript data for file_id: {file_id}")
            
            # Find relevant segment - use Ollama if available and requested
            segment = None
            confidence = 0.0
            metadata = {}
            
            try:
                if OLLAMA_AVAILABLE and use_llm:
                    logger.info(f"Using DeepSeek-LLM to find answer to question: '{question_text}'")
                    result = ollama_client.find_answer_in_transcript(transcript_data, question_text)
                    segment = result.get("matched_segment")
                    confidence = result.get("confidence", 0.0)
                    metadata = result.get("metadata", {})
                else:
                    logger.info(f"Using keyword matching to find answer to question: '{question_text}'")
                    segment = transcriber.get_segment_by_question(transcript_data, question_text)
                    confidence = 0.5  # Default confidence for keyword matching
                    metadata = {"match_method": "keyword"}
            except Exception as search_error:
                logger.error(f"Error searching for answer: {str(search_error)}", exc_info=True)
                raise ValueError(f"Error finding answer in transcript: {str(search_error)}")
            
            if segment:
                logger.info(f"Answer found in segment at {segment['start']} - {segment['end']} (confidence: {confidence:.2f})")
                
                # Convert timestamps from HH:MM:SS format to seconds
                try:
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
                except Exception as time_error:
                    logger.error(f"Error parsing timestamps: {str(time_error)}")
                    raise ValueError(f"Error parsing timestamps: {str(time_error)}")
                
                # Add timestamps to metadata
                metadata["timestamp"] = {
                    "start_raw": segment["start"],
                    "end_raw": segment["end"],
                    "start_seconds": start_time,
                    "end_seconds": end_time,
                    "duration_seconds": end_time - start_time
                }
                
                # Add request info to metadata
                metadata["request"] = {
                    "file_id": file_id,
                    "question": question_text,
                    "language": language,
                    "use_llm": use_llm and OLLAMA_AVAILABLE,
                    "timestamp": datetime.now().isoformat()
                }
                
                return QuestionResult(
                    answer_segment=segment,
                    start_time=start_time,
                    end_time=end_time,
                    text=segment["text"],
                    question_text=question_text,
                    confidence=confidence,
                    metadata=metadata
                )
            else:
                logger.info(f"No relevant answer found for question: '{question_text}'")
                return QuestionResult(
                    answer_segment=None,
                    start_time=None,
                    end_time=None,
                    text="No relevant answer found",
                    question_text=question_text,
                    confidence=0.0,
                    metadata={
                        "match_method": "semantic" if OLLAMA_AVAILABLE and use_llm else "keyword",
                        "request": {
                            "file_id": file_id,
                            "question": question_text,
                            "language": language,
                            "use_llm": use_llm and OLLAMA_AVAILABLE,
                            "timestamp": datetime.now().isoformat()
                        }
                    }
                )
                
        except ValueError as ve:
            # Handle expected validation errors with details
            logger.error(f"Validation error in query_transcript_audio: {str(ve)}")
            raise HTTPException(status_code=400, detail=f"Input validation error: {str(ve)}")
        except HTTPException:
            # Re-raise HTTP exceptions as they already contain the right status code and message
            raise
        except Exception as e:
            # Add full error details including traceback to the logs
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in query_transcript_audio for file_id {file_id}: {str(e)}\n{error_traceback}")
            raise HTTPException(status_code=500, detail=f"Error processing question audio: {str(e) or 'Unknown error'}")

    @app.get("/get-audio-segment/{file_id}")
    async def get_audio_segment(
        file_id: str,
        start: float = Query(..., description="Start time in seconds"),
        end: float = Query(..., description="End time in seconds"),
        background_tasks: BackgroundTasks = BackgroundTasks()
    ):
        """
        Extract and return a segment of audio between the specified timestamps.
        
        Returns the relevant portion of the audio file that contains the answer
        to the user's question.
        """
        logger.info(f"Audio segment requested for file_id: {file_id}, start: {start}s, end: {end}s")
        segment_path = None
        
        try:
            # Validate parameters
            if not file_id or not isinstance(file_id, str):
                raise ValueError(f"Invalid file_id: {file_id}")
                
            if not isinstance(start, (int, float)) or start < 0:
                raise ValueError(f"Invalid start time: {start}. Must be a positive number.")
                
            if not isinstance(end, (int, float)) or end <= start:
                raise ValueError(f"Invalid end time: {end}. Must be greater than start time ({start}).")
            
            # Find the enhanced audio file
            file_path = None
            for filename in os.listdir(UPLOADS_DIR):
                if file_id in filename:
                    file_path = os.path.join(UPLOADS_DIR, filename)
                    logger.debug(f"Found audio file: {filename}")
                    break
            
            if not file_path:
                logger.warning(f"No audio file found with file_id: {file_id}")
                raise HTTPException(status_code=404, detail=f"Enhanced audio file not found for file_id: {file_id}")
            
            # Check if file exists and is readable
            if not os.path.isfile(file_path) or not os.access(file_path, os.R_OK):
                logger.error(f"File exists but is not readable: {file_path}")
                raise ValueError(f"Audio file exists but is not readable")
            
            # Load the audio file using pydub with explicit error handling
            try:
                logger.debug(f"Loading audio file: {file_path}")
                audio = AudioSegment.from_file(file_path)
                logger.debug(f"Audio loaded successfully: {len(audio)}ms duration")
            except Exception as audio_error:
                logger.error(f"Error loading audio file with pydub: {str(audio_error)}")
                raise ValueError(f"Failed to load audio file: {str(audio_error)}")
            
            # Convert seconds to milliseconds for pydub
            start_ms = int(start * 1000)
            end_ms = int(end * 1000)
            
            # Ensure end time is not beyond audio length
            if end_ms > len(audio):
                logger.warning(f"End time ({end_ms}ms) exceeds audio length ({len(audio)}ms). Adjusting to audio length.")
                end_ms = len(audio)
                
            # Add a small buffer before and after if possible (500ms)
            buffer_ms = 500
            if start_ms >= buffer_ms:
                start_ms -= buffer_ms
                
            if end_ms + buffer_ms <= len(audio):
                end_ms += buffer_ms
            
            # Validate segment boundaries
            if end_ms <= start_ms:
                raise ValueError(f"Invalid segment boundaries: start_ms={start_ms}, end_ms={end_ms}")
            
            # Extract the segment
            try:
                logger.debug(f"Extracting segment from {start_ms}ms to {end_ms}ms")
                segment = audio[start_ms:end_ms]
                
                if len(segment) == 0:
                    raise ValueError("Extracted segment has zero length")
                    
                logger.debug(f"Segment extracted successfully: {len(segment)}ms duration")
            except Exception as extract_error:
                logger.error(f"Error extracting segment: {str(extract_error)}")
                raise ValueError(f"Failed to extract audio segment: {str(extract_error)}")
            
            # Create a temporary file for the segment
            try:
                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
                segment_path = temp_file.name
                temp_file.close()
                
                segment.export(segment_path, format="wav")
                logger.debug(f"Audio segment exported to: {segment_path}")
                
                # Verify the file was created successfully
                if not os.path.exists(segment_path) or os.path.getsize(segment_path) == 0:
                    raise ValueError(f"Failed to create segment file or file is empty: {segment_path}")
            except Exception as export_error:
                logger.error(f"Error exporting segment to file: {str(export_error)}")
                
                # Clean up if file was created
                if segment_path and os.path.exists(segment_path):
                    try:
                        os.unlink(segment_path)
                    except:
                        pass
                        
                raise ValueError(f"Failed to save audio segment: {str(export_error)}")
            
            # Return the audio segment and clean up the temp file afterwards
            logger.info(f"Serving audio segment for file_id: {file_id}")
            
            # Add the cleanup task to the background tasks
            def cleanup_temp_file(file_path):
                try:
                    if os.path.exists(file_path):
                        os.unlink(file_path)
                        logger.debug(f"Temporary file removed: {file_path}")
                except Exception as e:
                    logger.error(f"Error removing temporary file {file_path}: {str(e)}")
            
            background_tasks.add_task(cleanup_temp_file, segment_path)
            
            return FileResponse(
                segment_path, 
                media_type="audio/wav",
                filename=f"answer_segment_{file_id}.wav",
                headers={
                    "X-Start-Time": str(start),
                    "X-End-Time": str(end),
                    "X-Duration": str(end - start),
                    "X-Segment-Length": str(len(segment)/1000)  # Duration in seconds
                }
            )
            
        except ValueError as ve:
            # Handle expected validation errors with details
            logger.error(f"Validation error in get_audio_segment: {str(ve)}")
            
            # Clean up if file was created
            if segment_path and os.path.exists(segment_path):
                try:
                    os.unlink(segment_path)
                except:
                    pass
                    
            raise HTTPException(status_code=400, detail=f"Input validation error: {str(ve)}")
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            # Add full error details including traceback to the logs
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in get_audio_segment for file_id {file_id}: {str(e)}\n{error_traceback}")
            
            # Clean up if file was created
            if segment_path and os.path.exists(segment_path):
                try:
                    os.unlink(segment_path)
                except:
                    pass
                    
            raise HTTPException(status_code=500, detail=f"Error extracting audio segment: {str(e) or 'Unknown error'}")

    @app.post("/diagnostic/transcribe-audio")
    async def diagnostic_transcribe_audio(
        question_audio: UploadFile = File(...),
        language: Optional[str] = None
    ):
        """
        Diagnostic endpoint to test audio transcription without the full question answering pipeline.
        This helps isolate issues with the audio processing or Whisper transcription.
        """
        logger.info(f"Diagnostic audio transcription requested for file: {question_audio.filename}")
        
        try:
            # Create a temporary file to store the uploaded audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                content = await question_audio.read()
                temp_file.write(content)
                temp_path = temp_file.name
                
            logger.debug(f"Audio saved to temp file: {temp_path}, size: {len(content)} bytes")
            
            # Get basic audio file info
            file_info = {
                "filename": question_audio.filename,
                "content_type": question_audio.content_type,
                "size_bytes": len(content),
                "temp_path": temp_path
            }
            
            # Try to transcribe the audio
            try:
                logger.info(f"Attempting to transcribe audio with Whisper")
                transcription, segments = transcriber.transcribe_with_timestamps(temp_path, language)
                
                # Clean up
                os.unlink(temp_path)
                
                return {
                    "status": "success",
                    "transcription": transcription,
                    "segments_count": len(segments),
                    "file_info": file_info
                }
            except Exception as whisper_error:
                logger.error(f"Whisper transcription failed: {str(whisper_error)}", exc_info=True)
                
                # Clean up
                os.unlink(temp_path)
                
                return {
                    "status": "error",
                    "message": f"Whisper transcription failed: {str(whisper_error)}",
                    "error_type": type(whisper_error).__name__,
                    "file_info": file_info
                }
        
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            logger.error(f"Error in diagnostic_transcribe_audio: {str(e)}\n{error_traceback}")
            
            return {
                "status": "error",
                "message": f"Error processing audio: {str(e)}",
                "error_type": type(e).__name__,
                "traceback": error_traceback
            }

    # Now add the new integrated endpoints for combined question answering and audio extraction
    if OLLAMA_AVAILABLE:
        @app.post("/audio-answers/{file_id}")
        async def audio_question_answer(
            file_id: str,
            question_audio: UploadFile = File(...),
            language: Optional[str] = None,
            include_audio: bool = Query(True, description="Whether to include audio segment in the response")
        ):
            """
            Integrated endpoint that accepts a question, finds the answer in the transcript,
            and returns both the answer text and the corresponding audio segment.
            
            This combines transcription, semantic search, and audio processing in one step.
            """
            logger.info(f"Audio answer requested for file_id: {file_id}, language: {language or 'auto'}")
            
            try:
                # Validation - check file_id format and find transcript
                if not file_id or not isinstance(file_id, str):
                    raise ValueError(f"Invalid file_id: {file_id}")
                
                transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{file_id}.json")
                if not os.path.exists(transcript_path):
                    logger.warning(f"Transcript not found for file_id: {file_id} at path: {transcript_path}")
                    raise HTTPException(status_code=404, detail=f"Transcript not found for file_id: {file_id}")
                
                # Find the audio file
                audio_path = None
                for filename in os.listdir(UPLOADS_DIR):
                    if file_id in filename:
                        audio_path = os.path.join(UPLOADS_DIR, filename)
                        logger.debug(f"Found audio file: {filename}")
                        break
                
                if not audio_path:
                    logger.warning(f"No audio file found with file_id: {file_id}")
                    raise HTTPException(status_code=404, detail=f"Audio file not found for file_id: {file_id}")
                
                # Process the question audio
                logger.debug(f"Processing question audio")
                content = await question_audio.read()
                if not content or len(content) < 100:
                    raise ValueError(f"Audio file content is too small or empty: {len(content)} bytes")
                
                # Save to temporary file
                with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                    temp_file.write(content)
                    question_audio_path = temp_file.name
                
                # Transcribe the question
                logger.info(f"Transcribing question audio with Whisper")
                question_text, _ = transcriber.transcribe_with_timestamps(question_audio_path, language)
                logger.info(f"Question transcribed: '{question_text}'")
                
                # Clean up temp file
                os.unlink(question_audio_path)
                
                # Load the transcript
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                
                # Find answer and extract audio segment
                if include_audio:
                    logger.info(f"Finding answer and extracting audio segment")
                    result = ollama_client.find_and_extract_audio_answer(
                        transcript_data=transcript_data,
                        original_audio_path=audio_path,
                        question=question_text
                    )
                    
                    answer_info = result["answer_info"]
                    audio_segment = result["audio_segment"]
                    start_time = result["start_time"]
                    end_time = result["end_time"]
                    
                    if audio_segment:
                        # If there's audio segment, create response with it
                        logger.info(f"Found answer with audio segment")
                        
                        # Create a response with both JSON data and audio segment
                        # Use StreamingResponse with multipart content type
                        response_json = {
                            "question": question_text,
                            "answer": answer_info["matched_segment"]["text"] if answer_info["matched_segment"] else "No answer found",
                            "start_time": start_time,
                            "end_time": end_time,
                            "confidence": answer_info["confidence"],
                            "metadata": answer_info["metadata"]
                        }
                        
                        # Return audio as bytes within the response
                        return {
                            "result": response_json,
                            "audio_segment_base64": base64.b64encode(audio_segment).decode('utf-8') if audio_segment else None,
                            "has_audio": audio_segment is not None
                        }
                    
                # If no audio segment or include_audio=False, return just the answer info
                logger.info(f"Returning answer without audio segment")
                matched_segment = answer_info["matched_segment"] if 'answer_info' in locals() else None
                
                if not matched_segment:
                    # If we don't have answer_info yet (when include_audio=False), find answer
                    answer_info = ollama_client.find_answer_in_transcript(transcript_data, question_text)
                    matched_segment = answer_info["matched_segment"]
                
                if matched_segment:
                    # Parse timestamps to seconds
                    start_time = 0
                    end_time = 0
                    
                    start_parts = matched_segment["start"].split(":")
                    if len(start_parts) == 3:  # Format is HH:MM:SS
                        start_time = int(start_parts[0]) * 3600 + int(start_parts[1]) * 60 + float(start_parts[2])
                    elif len(start_parts) == 2:  # Format is MM:SS
                        start_time = int(start_parts[0]) * 60 + float(start_parts[1])
                    
                    end_parts = matched_segment["end"].split(":")
                    if len(end_parts) == 3:  # Format is HH:MM:SS
                        end_time = int(end_parts[0]) * 3600 + int(end_parts[1]) * 60 + float(end_parts[2])
                    elif len(end_parts) == 2:  # Format is MM:SS
                        end_time = int(end_parts[0]) * 60 + float(end_parts[1])
                    
                    return {
                        "question": question_text,
                        "answer": matched_segment["text"],
                        "start_time": start_time,
                        "end_time": end_time,
                        "confidence": answer_info["confidence"],
                        "metadata": answer_info["metadata"],
                        "has_audio": False
                    }
                else:
                    return {
                        "question": question_text,
                        "answer": "No relevant answer found",
                        "confidence": 0.0,
                        "has_audio": False
                    }
                    
            except ValueError as ve:
                logger.error(f"Validation error in audio_question_answer: {str(ve)}")
                raise HTTPException(status_code=400, detail=f"Input validation error: {str(ve)}")
            except HTTPException:
                raise
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error in audio_question_answer: {str(e)}\n{error_traceback}")
                raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")
            
        @app.get("/stream-answer-audio/{file_id}")
        async def stream_answer_audio(
            file_id: str,
            question: str = Query(..., description="Question to ask about the transcript")
        ):
            """
            Find the answer to a question and stream the corresponding audio segment.
            
            This endpoint is optimized for direct audio playback in the browser.
            """
            logger.info(f"Streaming answer audio for file_id: {file_id}, question: '{question}'")
            
            try:
                # Find transcript
                transcript_path = os.path.join(TRANSCRIPTS_DIR, f"{file_id}.json")
                if not os.path.exists(transcript_path):
                    logger.warning(f"Transcript not found for file_id: {file_id}")
                    raise HTTPException(status_code=404, detail=f"Transcript not found for file_id: {file_id}")
                
                # Find the audio file
                audio_path = None
                for filename in os.listdir(UPLOADS_DIR):
                    if file_id in filename:
                        audio_path = os.path.join(UPLOADS_DIR, filename)
                        logger.debug(f"Found audio file: {filename}")
                        break
                
                if not audio_path:
                    logger.warning(f"No audio file found with file_id: {file_id}")
                    raise HTTPException(status_code=404, detail=f"Audio file not found for file_id: {file_id}")
                
                # Load transcript
                with open(transcript_path, "r", encoding="utf-8") as f:
                    transcript_data = json.load(f)
                
                # Find answer and extract audio
                result = ollama_client.find_and_extract_audio_answer(
                    transcript_data=transcript_data,
                    original_audio_path=audio_path,
                    question=question
                )
                
                if not result["audio_segment"]:
                    logger.warning(f"No audio segment extracted for question: '{question}'")
                    raise HTTPException(status_code=404, detail="No relevant audio segment found")
                
                # Create a buffer from the audio bytes
                buffer = io.BytesIO(result["audio_segment"])
                buffer.seek(0)
                
                # Extract metadata for headers
                metadata = result["answer_info"]["metadata"]
                start_time = result["start_time"]
                end_time = result["end_time"]
                
                # Stream the audio
                logger.info(f"Streaming answer audio segment ({len(result['audio_segment'])} bytes)")
                return StreamingResponse(
                    buffer, 
                    media_type="audio/wav",
                    headers={
                        "X-Answer-Text": result["answer_info"]["matched_segment"]["text"],
                        "X-Start-Time": str(start_time),
                        "X-End-Time": str(end_time),
                        "X-Duration": str(end_time - start_time),
                        "X-Confidence": str(result["answer_info"]["confidence"])
                    }
                )
                
            except HTTPException:
                raise
            except Exception as e:
                import traceback
                error_traceback = traceback.format_exc()
                logger.error(f"Error in stream_answer_audio: {str(e)}\n{error_traceback}")
                raise HTTPException(status_code=500, detail=f"Error streaming answer audio: {str(e)}")@app.get("/diagnostic/system-info")


async def diagnostic_system_info():
    """
    Get diagnostic information about the system setup.
    """
    try:
        # Check if directories exist and are writable
        uploads_writable = os.access(UPLOADS_DIR, os.W_OK)
        transcripts_writable = os.access(TRANSCRIPTS_DIR, os.W_OK)
        
        # Check Ollama connection if available
        ollama_status = "not_configured"
        if OLLAMA_AVAILABLE:
            try:
                import requests
                response = requests.get("http://localhost:11434/api/tags", timeout=2)
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    available_models = [m["name"] for m in models]
                    ollama_status = {
                        "status": "connected",
                        "available_models": available_models,
                        "deepseek_available": "deepseek-llm" in available_models
                    }
                else:
                    ollama_status = {
                        "status": "error",
                        "code": response.status_code,
                        "message": f"API returned status {response.status_code}"
                    }
            except Exception as e:
                ollama_status = {
                    "status": "error",
                    "message": str(e),
                    "error_type": type(e).__name__
                }
        
        # Check for transcripts
        transcript_files = [f for f in os.listdir(TRANSCRIPTS_DIR) if f.endswith('.json')]
        transcript_count = len(transcript_files)
        recent_transcripts = transcript_files[:5]  # Just the first 5 for brevity
        
        # Check for audio files
        audio_files = os.listdir(UPLOADS_DIR)
        audio_count = len(audio_files)
        recent_audio = audio_files[:5]  # Just the first 5 for brevity
        
        return {
            "api_version": "1.0.0",
            "whisper_available": WHISPER_AVAILABLE,
            "whisper_model": transcriber.model_size if WHISPER_AVAILABLE else None,
            "ollama_available": OLLAMA_AVAILABLE,
            "ollama_status": ollama_status,
            "uploads_dir": {
                "path": UPLOADS_DIR,
                "exists": os.path.exists(UPLOADS_DIR),
                "writable": uploads_writable,
                "file_count": audio_count,
                "recent_files": recent_audio
            },
            "transcripts_dir": {
                "path": TRANSCRIPTS_DIR,
                "exists": os.path.exists(TRANSCRIPTS_DIR),
                "writable": transcripts_writable,
                "file_count": transcript_count,
                "recent_files": recent_transcripts
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        logger.error(f"Error in diagnostic_system_info: {str(e)}\n{error_traceback}")
        
        return {
            "status": "error",
            "message": f"Error getting system info: {str(e)}",
            "error_type": type(e).__name__,
            "traceback": error_traceback
        }

# Direct audio processing endpoint - return the audio directly
@app.post("/process-audio-stream/")
async def process_audio_stream(
    audio_file: UploadFile = File(...),
    speed_factor: float = Form(0.75),
    volume_factor: float = Form(1.5),
    remove_noise: bool = Form(False),
    enhance_clarity: bool = Form(False),
):
    """
    Process audio and return it directly as a stream
    """
    request_id = str(uuid.uuid4())
    logger.info(f"Stream processing requested [request_id: {request_id}] - Original filename: {audio_file.filename}")
    logger.debug(f"Parameters - speed: {speed_factor}, volume: {volume_factor}, remove_noise: {remove_noise}, enhance_clarity: {enhance_clarity}")
    
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            content = await audio_file.read()
            temp_file.write(content)
            temp_path = temp_file.name
            logger.debug(f"Temporary file created: {temp_path} - Size: {len(content)} bytes")
            
        # Load the audio file
        logger.debug(f"Loading audio file with librosa [request_id: {request_id}]")
        y, sr = librosa.load(temp_path, sr=None)
        logger.debug(f"Audio loaded - Duration: {len(y)/sr:.2f}s, Sample rate: {sr}Hz")
        
        # Apply audio enhancements
        logger.info(f"Applying audio enhancements [request_id: {request_id}]")
        enhanced_audio = enhance_audio(
            y, sr, 
            speed_factor=speed_factor, 
            volume_factor=volume_factor, 
            remove_noise=remove_noise,
            enhance_clarity=enhance_clarity
        )
        
        # Clean up temporary file
        os.unlink(temp_path)
        logger.debug(f"Temporary file removed: {temp_path}")
        
        # Create an in-memory bytes buffer for the processed audio
        buffer = io.BytesIO()
        logger.debug(f"Writing processed audio to buffer")
        sf.write(buffer, enhanced_audio, sr, format='wav')
        buffer.seek(0)
        
        logger.info(f"Stream processing completed [request_id: {request_id}] - Streaming response")
        # Stream the audio back to the client
        return StreamingResponse(
            buffer, 
            media_type="audio/wav",
            headers={"Content-Disposition": f"attachment; filename=enhanced_{audio_file.filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error in process_audio_stream [request_id: {request_id}]: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing audio: {str(e)}")

# Application startup and shutdown events
@app.on_event("startup")
async def startup_event():
    logger.info("========== HearClear API Starting Up ==========")
    logger.info(f"Uploads directory: {UPLOADS_DIR}")
    logger.info(f"Transcripts directory: {TRANSCRIPTS_DIR}")
    logger.info(f"Whisper transcription available: {WHISPER_AVAILABLE}")
    logger.info(f"Ollama (DeepSeek-LLM) available: {OLLAMA_AVAILABLE}")
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("========== HearClear API Shutting Down ==========")

if __name__ == "__main__":
    # Run the server when the script is executed
    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)