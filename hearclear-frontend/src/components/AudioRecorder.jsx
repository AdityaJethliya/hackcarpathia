// src/components/AudioRecorder.jsx - Fixed version
import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, Typography, CircularProgress, Paper } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import StopIcon from '@mui/icons-material/Stop';
import DeleteIcon from '@mui/icons-material/Delete';
import { createWaveform } from '../utils/audioUtils';

const AudioRecorder = ({ onAudioRecorded }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [visualizerData, setVisualizerData] = useState([]);
  
  const mediaRecorderRef = useRef(null);
  const streamRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);
  const analyserRef = useRef(null);
  const animationRef = useRef(null);
  const canvasRef = useRef(null);

  // Start recording
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      streamRef.current = stream;
      
      // Set up audio analysis
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioContext.createMediaStreamSource(stream);
      const analyser = audioContext.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);
      analyserRef.current = analyser;
      
      // Clear previous recordings
      audioChunksRef.current = [];
      
      // Create media recorder with proper MIME type
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported('audio/webm') 
          ? 'audio/webm' 
          : 'audio/mp4'
      });
      
      mediaRecorderRef.current = mediaRecorder;
      
      // Set up event handlers
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        // Determine the correct MIME type
        const mimeType = mediaRecorder.mimeType || 'audio/webm';
        
        // Create the audio blob with the correct MIME type
        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType });
        
        // Create object URL
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // Update state
        setAudioBlob(audioBlob);
        setAudioUrl(audioUrl);
        
        console.log("Recording completed. Blob created:", audioBlob);
        console.log("Audio URL:", audioUrl);
        console.log("MIME type:", mimeType);
        
        // Clean up visualization
        if (animationRef.current) {
          cancelAnimationFrame(animationRef.current);
        }
      };
      
      // Start recording
      mediaRecorder.start(100); // Collect data every 100ms
      setIsRecording(true);
      
      // Start timer
      const startTime = Date.now();
      timerRef.current = setInterval(() => {
        setRecordingTime((Date.now() - startTime) / 1000);
      }, 100);
      
      // Start visualizer
      visualize();
      
    } catch (error) {
      console.error("Error accessing microphone:", error);
      alert("Could not access microphone. Please check permissions.");
    }
  };

  // Visualization logic
  const visualize = () => {
    if (!analyserRef.current) return;
    
    const analyser = analyserRef.current;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);
    
    const updateVisualizer = () => {
      if (!isRecording) return;
      
      analyser.getByteFrequencyData(dataArray);
      
      // Simplify the data for visualization
      const simplifiedData = [];
      for (let i = 0; i < bufferLength; i += 4) {
        simplifiedData.push(dataArray[i] / 255.0);
      }
      
      setVisualizerData(simplifiedData);
      animationRef.current = requestAnimationFrame(updateVisualizer);
    };
    
    updateVisualizer();
  };

  // Stop recording
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      
      // Clear timer
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      
      // Stop all tracks on the stream
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    }
  };

  // Reset recording
  const resetRecording = () => {
    if (audioUrl) {
      URL.revokeObjectURL(audioUrl);
    }
    
    setAudioBlob(null);
    setAudioUrl(null);
    setRecordingTime(0);
    setVisualizerData([]);
  };

  // Submit recording
  const submitRecording = () => {
    if (audioBlob && onAudioRecorded) {
      // Create a proper file from the blob with the correct type
      const mimeType = audioBlob.type || 'audio/webm';
      const file = new File([audioBlob], "recording." + (mimeType.includes('webm') ? 'webm' : 'mp4'), { 
        type: mimeType
      });
      
      onAudioRecorded(file, audioUrl);
    }
  };

  // Test audio before submission
  const testAudio = () => {
    if (audioUrl) {
      const audio = new Audio(audioUrl);
      audio.play().catch(error => {
        console.error("Error playing test audio:", error);
      });
    }
  };

  // Format time display
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
      
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
      
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl);
      }
    };
  }, [audioUrl]);

  return (
    <Paper elevation={2} sx={{ p: 3, borderRadius: 2, width: '100%' }}>
      <Typography variant="h6" gutterBottom align="center">
        {isRecording ? "Recording..." : audioBlob ? "Recording Complete" : "Record Audio"}
      </Typography>
      
      {isRecording && (
        <Box sx={{ 
          display: 'flex', 
          justifyContent: 'center', 
          mb: 3,
          height: 60,
          overflow: 'hidden'
        }}>
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            width: '100%',
            height: '100%'
          }}>
            {visualizerData.map((value, index) => (
              <Box 
                key={index} 
                sx={{ 
                  width: 3, 
                  height: `${value * 100}%`, 
                  backgroundColor: 'primary.main',
                  borderRadius: 2,
                  mx: 0.5,
                  transition: 'height 0.1s ease-in-out'
                }} 
              />
            ))}
          </Box>
        </Box>
      )}
      
      {audioBlob && !isRecording && (
        <Box sx={{ mb: 3 }}>
          <canvas ref={canvasRef} style={{ width: '100%', height: '60px' }} />
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 1 }}>
            <audio src={audioUrl} controls style={{ width: '100%' }} />
          </Box>
        </Box>
      )}
      
      <Box sx={{ 
        display: 'flex', 
        justifyContent: 'center', 
        alignItems: 'center',
        mb: 2
      }}>
        {isRecording ? (
          <Typography variant="h4" sx={{ 
            color: 'error.main', 
            fontWeight: 'bold',
            animation: 'pulse 1.5s infinite',
            '@keyframes pulse': {
              '0%': { opacity: 1 },
              '50%': { opacity: 0.6 },
              '100%': { opacity: 1 },
            }
          }}>
            {formatTime(recordingTime)}
          </Typography>
        ) : (
          audioBlob ? (
            <Typography variant="h5">
              {formatTime(recordingTime)}
            </Typography>
          ) : null
        )}
      </Box>
      
      <Box sx={{ display: 'flex', justifyContent: 'center', gap: 2 }}>
        {!isRecording && !audioBlob && (
          <Button
            variant="contained"
            color="primary"
            startIcon={<MicIcon />}
            onClick={startRecording}
            sx={{ borderRadius: 8, py: 1.5, px: 4 }}
          >
            Start Recording
          </Button>
        )}
        
        {isRecording && (
          <Button
            variant="contained"
            color="error"
            startIcon={<StopIcon />}
            onClick={stopRecording}
            sx={{ borderRadius: 8, py: 1.5, px: 4 }}
          >
            Stop Recording
          </Button>
        )}
        
        {audioBlob && !isRecording && (
          <>
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={resetRecording}
              sx={{ borderRadius: 8, py: 1.5 }}
            >
              Discard
            </Button>
            
            <Button
              variant="contained"
              color="primary"
              onClick={submitRecording}
              sx={{ borderRadius: 8, py: 1.5, px: 4 }}
            >
              Use Recording
            </Button>
          </>
        )}
      </Box>
    </Paper>
  );
};

export default AudioRecorder;