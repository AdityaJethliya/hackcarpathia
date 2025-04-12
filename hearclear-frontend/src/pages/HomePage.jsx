// src/pages/HomePage.jsx
import React from 'react';
import { Box, Typography, Container, Paper } from '@mui/material';
import HearingIcon from '@mui/icons-material/Hearing';
import AudioUploader from '../components/AudioUploader';
import { useAudio } from '../contexts/AudioContext';

const HomePage = () => {
  const { handleAudioSelected } = useAudio();

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Box sx={{ 
        display: 'flex', 
        flexDirection: 'column', 
        alignItems: 'center', 
        justifyContent: 'center',
        mb: 4
      }}>
        <Box sx={{ 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'center',
          backgroundColor: 'primary.main',
          color: 'white',
          width: 80,
          height: 80,
          borderRadius: '50%',
          mb: 2
        }}>
          <HearingIcon sx={{ fontSize: 40 }} />
        </Box>
        
        <Typography 
          variant="h4" 
          component="h1" 
          gutterBottom 
          align="center"
          sx={{ fontWeight: 'bold' }}
        >
          HearClear
        </Typography>
        
        <Typography 
          variant="h6" 
          gutterBottom 
          align="center" 
          color="textSecondary"
          sx={{ mb: 3 }}
        >
          Make spoken audio easier to hear and understand
        </Typography>
      </Box>
      
      <Paper 
        elevation={0} 
        sx={{ 
          p: 3, 
          mb: 4, 
          borderRadius: 2, 
          bgcolor: '#f0f7ff',
          border: '1px solid #cce5ff'
        }}
      >
        <Typography variant="body1" paragraph>
          HearClear helps you:
        </Typography>
        <Box component="ul" sx={{ pl: 2, mt: 0 }}>
          <Typography component="li" variant="body1" paragraph>
            Slow down fast speech to make it easier to understand
          </Typography>
          <Typography component="li" variant="body1" paragraph>
            Increase volume of quiet recordings
          </Typography>
          <Typography component="li" variant="body1" paragraph>
            Remove background noise
          </Typography>
          <Typography component="li" variant="body1" paragraph>
            Create transcripts of spoken content
          </Typography>
        </Box>
      </Paper>
      
      <Typography 
        variant="h6" 
        gutterBottom 
        align="center"
        sx={{ mb: 2 }}
      >
        Upload or Record Audio
      </Typography>
      
      <AudioUploader onAudioSelected={handleAudioSelected} />
    </Container>
  );
};

export default HomePage;