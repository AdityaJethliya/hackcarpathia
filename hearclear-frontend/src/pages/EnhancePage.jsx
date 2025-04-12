// src/pages/EnhancePage.jsx
import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Button, CircularProgress } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import { useNavigate } from 'react-router-dom';
import { useAudio } from '../contexts/AudioContext';
import EnhancementForm from '../components/EnhancementForm';
import AudioPlayer from '../components/AudioPlayer';
import { enhanceAudio, downloadEnhancedAudio } from '../api/apiClient';

const EnhancePage = () => {
  const navigate = useNavigate();
  const { 
    originalAudio, 
    originalAudioUrl, 
    isProcessing, 
    setIsProcessing,
    handleAudioEnhanced
  } = useAudio();
  
  const [error, setError] = useState(null);

  // Redirect if no audio file is selected
  useEffect(() => {
    if (!originalAudio) {
      navigate('/');
    }
  }, [originalAudio, navigate]);

  const handleEnhanceAudio = async (enhancementParams) => {
    if (!originalAudio) return;
    
    setError(null);
    setIsProcessing(true);
    
    try {
      // Call the API to enhance the audio
      const result = await enhanceAudio(originalAudio, enhancementParams);
      
      // Get the URL for the enhanced audio file
      const enhancedUrl = downloadEnhancedAudio(result.file_id);
      
      // Update the context with the results
      handleAudioEnhanced(result, enhancedUrl);
      
      // Navigate to the playback page
      navigate('/playback');
    } catch (err) {
      console.error('Error enhancing audio:', err);
      setError('Failed to enhance audio. Please try again.');
      setIsProcessing(false);
    }
  };

  if (!originalAudio) {
    return (
      <Container maxWidth="sm" sx={{ py: 4, display: 'flex', justifyContent: 'center' }}>
        <CircularProgress />
      </Container>
    );
  }

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <Button 
          startIcon={<ArrowBackIcon />} 
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h5" component="h1">
          Enhance Audio
        </Typography>
      </Box>
      
      {originalAudioUrl && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Original Audio
          </Typography>
          <AudioPlayer audioUrl={originalAudioUrl} />
        </Box>
      )}
      
      <EnhancementForm 
        onEnhance={handleEnhanceAudio} 
        isProcessing={isProcessing}
        audioName={originalAudio ? originalAudio.name : ''}
      />
      
      {error && (
        <Typography color="error" sx={{ mt: 2, textAlign: 'center' }}>
          {error}
        </Typography>
      )}
    </Container>
  );
};

export default EnhancePage;