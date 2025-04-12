// src/components/AudioUploader.jsx
import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Box, Typography, Button, Paper, CircularProgress } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import MicIcon from '@mui/icons-material/Mic';
import { useNavigate } from 'react-router-dom';

const AudioUploader = ({ onAudioSelected }) => {
  const [isUploading, setIsUploading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [audioStream, setAudioStream] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [recordedChunks, setRecordedChunks] = useState([]);
  const [recordingTime, setRecordingTime] = useState(0);
  const [timer, setTimer] = useState(null);
  
  const navigate = useNavigate();

  const onDrop = useCallback((acceptedFiles) => {
    setIsUploading(true);
    const file = acceptedFiles[0];
    
    // Create a preview for the audio file
    const audioUrl = URL.createObjectURL(file);
    
    // Call the parent handler with the file and URL
    onAudioSelected(file, audioUrl);
    setIsUploading(false);
    
    // Navigate to enhancement page
    navigate('/enhance');
  }, [onAudioSelected, navigate]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'audio/*': ['.mp3', '.wav', '.m4a', '.aac', '.ogg']
    },
    maxFiles: 1
  });

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      setAudioStream(stream);
      
      const recorder = new MediaRecorder(stream);
      setMediaRecorder(recorder);
      
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          setRecordedChunks((prev) => [...prev, event.data]);
        }
      };
      
      recorder.onstop = () => {
        const audioBlob = new Blob(recordedChunks, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        const file = new File([audioBlob], "recording.wav", { type: 'audio/wav' });
        
        onAudioSelected(file, audioUrl);
        
        // Clean up
        if (audioStream) {
          audioStream.getTracks().forEach(track => track.stop());
        }
        
        // Navigate to enhancement page
        navigate('/enhance');
      };
      
      // Start recording
      recorder.start();
      setIsRecording(true);
      
      // Set up timer to display recording time
      const startTime = Date.now();
      const interval = setInterval(() => {
        setRecordingTime((Date.now() - startTime) / 1000);
      }, 100);
      setTimer(interval);
      
    } catch (error) {
      console.error("Error accessing microphone:", error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorder && isRecording) {
      mediaRecorder.stop();
      setIsRecording(false);
      
      // Clear the timer
      if (timer) {
        clearInterval(timer);
        setTimer(null);
      }
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Box sx={{ width: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
      {isRecording ? (
        <Paper 
          elevation={3} 
          sx={{ 
            width: '100%', 
            padding: 3, 
            display: 'flex', 
            flexDirection: 'column', 
            alignItems: 'center',
            backgroundColor: '#f8f8f8',
            borderRadius: 2
          }}
        >
          <Box sx={{ 
            width: 150, 
            height: 150, 
            borderRadius: '50%', 
            backgroundColor: '#ff4444', 
            display: 'flex', 
            justifyContent: 'center', 
            alignItems: 'center',
            boxShadow: '0 0 20px rgba(255, 0, 0, 0.5)',
            animation: 'pulse 1.5s infinite'
          }}>
            <Typography variant="h4" color="white">
              {formatTime(recordingTime)}
            </Typography>
          </Box>
          
          <Typography variant="h6" sx={{ mt: 2 }}>
            Recording...
          </Typography>
          
          <Button 
            variant="contained" 
            color="error" 
            onClick={stopRecording}
            sx={{ mt: 2, width: '80%', padding: 1.5, borderRadius: 8 }}
          >
            Stop Recording
          </Button>
        </Paper>
      ) : (
        <>
          <Paper
            {...getRootProps()}
            elevation={3}
            sx={{
              width: '100%',
              padding: 3,
              border: isDragActive ? '2px dashed #2196f3' : '2px dashed #cccccc',
              backgroundColor: isDragActive ? '#e3f2fd' : '#f8f8f8',
              borderRadius: 2,
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              textAlign: 'center',
              minHeight: 200,
            }}
          >
            <input {...getInputProps()} />
            <CloudUploadIcon sx={{ fontSize: 64, color: '#666' }} />
            {isUploading ? (
              <CircularProgress sx={{ mt: 2 }} />
            ) : (
              <>
                <Typography variant="h6" sx={{ mt: 2 }}>
                  Tap or drop audio files here
                </Typography>
                <Typography variant="body2" color="textSecondary" sx={{ mt: 1 }}>
                  Supports MP3, WAV, M4A, AAC, and OGG formats
                </Typography>
              </>
            )}
          </Paper>

          <Typography variant="h6" sx={{ mt: 4, mb: 2, textAlign: 'center' }}>
            OR
          </Typography>

          <Button
            variant="contained"
            color="primary"
            startIcon={<MicIcon />}
            onClick={startRecording}
            sx={{ 
              width: '100%', 
              padding: 2, 
              borderRadius: 8,
              fontSize: '1.1rem'
            }}
          >
            Record Audio
          </Button>
        </>
      )}
    </Box>
  );
};

export default AudioUploader;