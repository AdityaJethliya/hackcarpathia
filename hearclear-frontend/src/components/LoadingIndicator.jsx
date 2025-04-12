// src/components/LoadingIndicator.jsx
import React from 'react';
import { Box, CircularProgress, Typography, Paper } from '@mui/material';

const LoadingIndicator = ({ message = 'Loading...', fullScreen = false }) => {
  const content = (
    <Box sx={{ 
      display: 'flex', 
      flexDirection: 'column', 
      alignItems: 'center', 
      justifyContent: 'center',
      p: 3
    }}>
      <CircularProgress size={40} sx={{ mb: 2 }} />
      <Typography variant="body1" color="textSecondary">
        {message}
      </Typography>
    </Box>
  );

  if (fullScreen) {
    return (
      <Box sx={{ 
        position: 'fixed', 
        top: 0, 
        left: 0, 
        right: 0, 
        bottom: 0, 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        bgcolor: 'rgba(255, 255, 255, 0.9)',
        zIndex: 9999
      }}>
        <Paper elevation={3} sx={{ borderRadius: 2 }}>
          {content}
        </Paper>
      </Box>
    );
  }

  return (
    <Paper elevation={2} sx={{ borderRadius: 2, my: 2 }}>
      {content}
    </Paper>
  );
};

export default LoadingIndicator;