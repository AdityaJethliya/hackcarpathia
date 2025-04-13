// src/components/VoiceRecorder.jsx
import React, { useState, useRef } from 'react';
import { Button, CircularProgress, Box } from '@mui/material';
import MicIcon from '@mui/icons-material/Mic';
import StopIcon from '@mui/icons-material/Stop';
import { speechToText } from '../api/googleApiClient';

const VoiceRecorder = ({ onTextReceived, disabled = false }) => {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const streamRef = useRef(null);

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
      
      // Clear previous recordings
      audioChunksRef.current = [];
      
      // Create media recorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm'
      });
      mediaRecorderRef.current = mediaRecorder;
      
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorder.onstop = async () => {
        setIsProcessing(true);
        
        try {
          // Create audio blob
          const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
          
          // Convert speech to text
          const transcribedText = await speechToText(audioBlob);
          
          if (transcribedText && onTextReceived) {
            onTextReceived(transcribedText);
          }
        } catch (error) {
          console.error('Error processing voice input:', error);
        } finally {
          setIsProcessing(false);
        }
        
        // Clean up
        if (streamRef.current) {
          streamRef.current.getTracks().forEach(track => track.stop());
        }
      };
      
      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
      alert('Could not access microphone. Please check permissions.');
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  // Clean up when component unmounts
  React.useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, []);

  return (
    <Box>
      {isProcessing ? (
        <CircularProgress size={24} />
      ) : isRecording ? (
        <Button
          color="error"
          variant="contained"
          startIcon={<StopIcon />}
          onClick={stopRecording}
          disabled={disabled}
        >
          Stop
        </Button>
      ) : (
        <Button
          color="primary"
          variant="contained"
          startIcon={<MicIcon />}
          onClick={startRecording}
          disabled={disabled}
        >
          Ask
        </Button>
      )}
    </Box>
  );
};

export default VoiceRecorder;