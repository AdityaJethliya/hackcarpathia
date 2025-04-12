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
from typing import Dict, List, Optional, Union
import uvicorn

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
        question: str = Query(..., description="Question to ask about the transcript")
    ):
        """
        Query a transcript using natural language
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
            
            # Find relevant segment
            logger.debug(f"Searching for answer to question: '{question}'")
            segment = transcriber.get_segment_by_question(transcript_data, question)
            
            if segment:
                logger.info(f"Answer found in segment at {segment['start']} - {segment['end']}")
                return QuestionResult(
                    answer_segment=segment,
                    start_time=float(segment["start"].split(":")[0]) * 60 + float(segment["start"].split(":")[1]),
                    end_time=float(segment["end"].split(":")[0]) * 60 + float(segment["end"].split(":")[1]),
                    text=segment["text"]
                )
            else:
                logger.info(f"No relevant answer found for question: '{question}'")
                return QuestionResult(
                    answer_segment=None,
                    start_time=None,
                    end_time=None,
                    text="No relevant answer found"
                )
                
        except Exception as e:
            logger.error(f"Error in query_transcript for file_id {file_id}: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error querying transcript: {str(e)}")

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
    
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("========== HearClear API Shutting Down ==========")

if __name__ == "__main__":
    # Run the server when the script is executed
    logger.info("Starting uvicorn server")
    uvicorn.run(app, host="0.0.0.0", port=8000)