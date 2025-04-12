// src/components/EnhancementForm.jsx
import React, { useState } from 'react';
import { 
  Box, 
  Typography, 
  Slider, 
  Switch, 
  FormControlLabel, 
  Button, 
  Paper,
  CircularProgress
} from '@mui/material';
import SpeedIcon from '@mui/icons-material/Speed';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import BuildIcon from '@mui/icons-material/Build';
import NoiseAwareIcon from '@mui/icons-material/NoiseAware';

const EnhancementForm = ({ 
  onEnhance, 
  isProcessing, 
  audioName, 
  initialValues = {
    speedFactor: 0.75,
    volumeFactor: 1.5,
    removeNoise: false,
    enhanceClarity: false
  }
}) => {
  const [enhancementParams, setEnhancementParams] = useState(initialValues);

  const handleSpeedChange = (event, newValue) => {
    setEnhancementParams(prev => ({ ...prev, speedFactor: newValue }));
  };

  const handleVolumeChange = (event, newValue) => {
    setEnhancementParams(prev => ({ ...prev, volumeFactor: newValue }));
  };

  const handleSwitchChange = (name) => (event) => {
    setEnhancementParams(prev => ({ ...prev, [name]: event.target.checked }));
  };

  const handleSubmit = () => {
    onEnhance(enhancementParams);
  };

  return (
    <Paper elevation={3} sx={{ p: 3, borderRadius: 2, width: '100%' }}>
      <Typography variant="h5" gutterBottom align="center" sx={{ mb: 3 }}>
        Enhance Audio
      </Typography>

      {audioName && (
        <Typography variant="body2" color="textSecondary" align="center" sx={{ mb: 3 }}>
          File: {audioName}
        </Typography>
      )}

      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <SpeedIcon color="primary" sx={{ mr: 1 }} />
          <Typography id="speed-slider" gutterBottom>
            Speech Speed: {enhancementParams.speedFactor === 1 ? "Normal" : 
              enhancementParams.speedFactor < 1 ? `${Math.round((1-enhancementParams.speedFactor)*100)}% Slower` : 
              `${Math.round((enhancementParams.speedFactor-1)*100)}% Faster`}
          </Typography>
        </Box>
        <Slider
          aria-labelledby="speed-slider"
          value={enhancementParams.speedFactor}
          onChange={handleSpeedChange}
          step={0.05}
          marks={[
            { value: 0.5, label: 'Slow' },
            { value: 0.75, label: '' },
            { value: 1, label: 'Normal' },
          ]}
          min={0.5}
          max={1}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value.toFixed(2)}`}
        />
      </Box>

      <Box sx={{ mb: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <VolumeUpIcon color="primary" sx={{ mr: 1 }} />
          <Typography id="volume-slider" gutterBottom>
            Volume: {enhancementParams.volumeFactor === 1 ? "Normal" : 
              `${Math.round((enhancementParams.volumeFactor-1)*100)}% Louder`}
          </Typography>
        </Box>
        <Slider
          aria-labelledby="volume-slider"
          value={enhancementParams.volumeFactor}
          onChange={handleVolumeChange}
          step={0.1}
          marks={[
            { value: 1, label: 'Normal' },
            { value: 1.5, label: '' },
            { value: 2, label: 'Loud' },
          ]}
          min={1}
          max={2}
          valueLabelDisplay="auto"
          valueLabelFormat={(value) => `${value.toFixed(1)}x`}
        />
      </Box>

      <Box sx={{ mb: 4 }}>
        <FormControlLabel
          control={
            <Switch
              checked={enhancementParams.removeNoise}
              onChange={handleSwitchChange('removeNoise')}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <NoiseAwareIcon color="primary" sx={{ mr: 1 }} />
              <Typography>Remove Background Noise</Typography>
            </Box>
          }
        />
      </Box>

      <Box sx={{ mb: 4 }}>
        <FormControlLabel
          control={
            <Switch
              checked={enhancementParams.enhanceClarity}
              onChange={handleSwitchChange('enhanceClarity')}
              color="primary"
            />
          }
          label={
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <BuildIcon color="primary" sx={{ mr: 1 }} />
              <Typography>Enhance Speech Clarity</Typography>
            </Box>
          }
        />
      </Box>

      <Button
        variant="contained"
        color="primary"
        fullWidth
        size="large"
        onClick={handleSubmit}
        disabled={isProcessing}
        sx={{ 
          mt: 2, 
          py: 1.5, 
          borderRadius: 8,
          fontSize: '1.1rem'
        }}
      >
        {isProcessing ? (
          <CircularProgress size={24} color="inherit" sx={{ mr: 1 }} />
        ) : 'Enhance Audio'}
      </Button>
    </Paper>
  );
};

export default EnhancementForm;