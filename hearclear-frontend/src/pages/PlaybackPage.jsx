// src/pages/PlaybackPage.jsx
import React, { useEffect } from 'react';
import { Container, Typography, Box, Button, Divider, Paper } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import DownloadIcon from '@mui/icons-material/Download';
import TextsmsIcon from '@mui/icons-material/Textsms';
import { useNavigate } from 'react-router-dom';
import { useAudio } from '../contexts/AudioContext';
import AudioPlayer from '../components/AudioPlayer';
import { transcribeAudio } from '../api/apiClient';

const PlaybackPage = () => {
  const navigate = useNavigate();
  const { 
    originalAudioUrl, 
    enhancedAudioUrl, 
    audioProcessingResult,
    setIsProcessing,
    handleTranscriptReceived
  } = useAudio();
  
  // Redirect if no enhanced audio is available
  useEffect(() => {
    if (!enhancedAudioUrl) {
      navigate('/');
    }
  }, [enhancedAudioUrl, navigate]);

  const handleDownload = () => {
    if (enhancedAudioUrl) {
      const link = document.createElement('a');
      link.href = enhancedAudioUrl;
      link.download = audioProcessingResult.enhanced_filename || 'enhanced-audio.wav';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    }
  };

  const handleTranscribe = async () => {
    if (!audioProcessingResult || !audioProcessingResult.file_id) return;
    
    setIsProcessing(true);
    
    try {
      const result = await transcribeAudio(audioProcessingResult.file_id);
      handleTranscriptReceived(result);
      navigate('/transcript');
    } catch (error) {
      console.error('Error transcribing audio:', error);
      alert('Failed to transcribe audio. Please try again.');
    } finally {
      setIsProcessing(false);
    }
  };

  if (!enhancedAudioUrl || !audioProcessingResult) {
    return <Typography>Loading...</Typography>;
  }

  // Format the enhancement stats for display
  const formatStats = () => {
    const stats = audioProcessingResult.processing_stats;
    return {
      speedFactor: `${(stats.speed_factor * 100).toFixed(0)}%`,
      volumeFactor: `${(stats.volume_factor * 100).toFixed(0)}%`,
      noiseRemoval: stats.noise_removal_applied ? 'Applied' : 'Not Applied',
      clarityEnhancement: stats.clarity_enhancement_applied ? 'Applied' : 'Not Applied',
      duration: `${audioProcessingResult.duration_seconds.toFixed(1)} seconds`
    };
  };

  const stats = formatStats();

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center' }}>
        <Button 
          startIcon={<ArrowBackIcon />} 
          onClick={() => navigate('/enhance')}
          sx={{ mr: 2 }}
        >
          Back
        </Button>
        <Typography variant="h5" component="h1">
          Enhanced Audio
        </Typography>
      </Box>
      
      <Box sx={{ mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Enhanced Version
        </Typography>
        <AudioPlayer 
          audioUrl={enhancedAudioUrl} 
          title="Enhanced Audio" 
        />
      </Box>
      
      {originalAudioUrl && (
        <Box sx={{ mb: 4 }}>
          <Typography variant="h6" gutterBottom>
            Original Version
          </Typography>
          <AudioPlayer 
            audioUrl={originalAudioUrl} 
            title="Original Audio" 
          />
        </Box>
      )}
      
      <Paper elevation={2} sx={{ p: 2, mb: 4, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>
          Enhancement Details
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="textSecondary">Speed:</Typography>
            <Typography variant="body2">{stats.speedFactor} of original speed</Typography>
          </Box>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="textSecondary">Volume:</Typography>
            <Typography variant="body2">{stats.volumeFactor} of original volume</Typography>
          </Box>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="textSecondary">Noise Removal:</Typography>
            <Typography variant="body2">{stats.noiseRemoval}</Typography>
          </Box>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="textSecondary">Clarity Enhancement:</Typography>
            <Typography variant="body2">{stats.clarityEnhancement}</Typography>
          </Box>
          <Divider />
          <Box sx={{ display: 'flex', justifyContent: 'space-between' }}>
            <Typography variant="body2" color="textSecondary">Duration:</Typography>
            <Typography variant="body2">{stats.duration}</Typography>
          </Box>
        </Box>
      </Paper>
      
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Button
          variant="contained"
          color="primary"
          startIcon={<DownloadIcon />}
          onClick={handleDownload}
          fullWidth
          sx={{ py: 1.5, borderRadius: 8 }}
        >
          Download Enhanced Audio
        </Button>
        
        <Button
          variant="outlined"
          color="primary"
          startIcon={<TextsmsIcon />}
          onClick={handleTranscribe}
          fullWidth
          sx={{ py: 1.5, borderRadius: 8 }}
        >
          Generate Transcript
        </Button>
      </Box>
    </Container>
  );
};

export default PlaybackPage;