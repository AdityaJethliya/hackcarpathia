// src/components/AudioPlayer.jsx
import React, { useEffect, useRef, useState } from 'react';
import { Box, IconButton, Slider, Typography, Paper } from '@mui/material';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import PauseIcon from '@mui/icons-material/Pause';
import ReplayIcon from '@mui/icons-material/Replay';
import Forward10Icon from '@mui/icons-material/Forward10';
import Replay10Icon from '@mui/icons-material/Replay10';

const AudioPlayer = ({ audioUrl, title }) => {
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [currentTime, setCurrentTime] = useState(0);
  const [isLoaded, setIsLoaded] = useState(false);
  const [error, setError] = useState(null);
  const animationRef = useRef(null);

  useEffect(() => {
    const audio = audioRef.current;
    
    // Reset state when audioUrl changes
    setIsLoaded(false);
    setError(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
    
    const setAudioData = () => {
      setDuration(audio.duration);
      setIsLoaded(true);
    };
    
    const updateTime = () => {
      setCurrentTime(audio.currentTime);
    };
    
    const handleError = (e) => {
      console.error('Audio loading error:', e);
      setError('Failed to load audio');
      setIsPlaying(false);
    };

    // Events
    audio.addEventListener('loadedmetadata', setAudioData);
    audio.addEventListener('timeupdate', updateTime);
    audio.addEventListener('ended', () => setIsPlaying(false));
    audio.addEventListener('error', handleError);

    // Force reload of the audio element when URL changes
    audio.load();

    return () => {
      audio.removeEventListener('loadedmetadata', setAudioData);
      audio.removeEventListener('timeupdate', updateTime);
      audio.removeEventListener('ended', () => setIsPlaying(false));
      audio.removeEventListener('error', handleError);
      
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [audioUrl]);

  const togglePlayPause = async () => {
    const audio = audioRef.current;
    
    if (!isLoaded) return;
    
    if (isPlaying) {
      audio.pause();
      cancelAnimationFrame(animationRef.current);
      setIsPlaying(false);
    } else {
      try {
        await audio.play();
        animationRef.current = requestAnimationFrame(whilePlaying);
        setIsPlaying(true);
      } catch (err) {
        console.error('Playback error:', err);
        setError(`Playback error: ${err.message}`);
      }
    }
  };

  const whilePlaying = () => {
    setCurrentTime(audioRef.current.currentTime);
    animationRef.current = requestAnimationFrame(whilePlaying);
  };

  const changeRange = (event, newValue) => {
    const audio = audioRef.current;
    audio.currentTime = newValue;
    setCurrentTime(newValue);
  };

  const skipForward = () => {
    if (!isLoaded) return;
    audioRef.current.currentTime += 10;
  };

  const skipBackward = () => {
    if (!isLoaded) return;
    audioRef.current.currentTime -= 10;
  };

  const restart = () => {
    if (!isLoaded) return;
    audioRef.current.currentTime = 0;
  };

  const formatTime = (seconds) => {
    if (isNaN(seconds)) return '0:00';
    
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 2, 
        borderRadius: 2, 
        bgcolor: '#f9f9f9',
        width: '100%'
      }}
    >
      {title && (
        <Typography variant="subtitle1" gutterBottom align="center">
          {title}
        </Typography>
      )}
      
      <audio ref={audioRef} src={audioUrl || ''} preload="metadata" />
      
      {error && (
        <Typography variant="body2" color="error" align="center" sx={{ mb: 1 }}>
          {error}
        </Typography>
      )}
      
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="body2" color="textSecondary">
          {formatTime(currentTime)}
        </Typography>
        <Typography variant="body2" color="textSecondary">
          {formatTime(duration)}
        </Typography>
      </Box>
      
      <Slider
        value={currentTime}
        min={0}
        max={duration || 0}
        onChange={changeRange}
        disabled={!isLoaded}
        sx={{ 
          color: 'primary.main', 
          height: 4,
          '& .MuiSlider-thumb': {
            width: 12,
            height: 12,
          }
        }}
      />
      
      <Box sx={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center',
        mt: 1
      }}>
        <IconButton onClick={restart} size="small" disabled={!isLoaded}>
          <ReplayIcon />
        </IconButton>
        
        <IconButton onClick={skipBackward} size="small" disabled={!isLoaded}>
          <Replay10Icon />
        </IconButton>
        
        <IconButton 
          onClick={togglePlayPause} 
          disabled={!isLoaded && !error}
          sx={{ 
            mx: 1,
            backgroundColor: isLoaded ? 'primary.main' : 'grey.400',
            color: 'white',
            '&:hover': {
              backgroundColor: isLoaded ? 'primary.dark' : 'grey.500',
            },
            width: 48,
            height: 48
          }}
        >
          {isPlaying ? <PauseIcon /> : <PlayArrowIcon />}
        </IconButton>
        
        <IconButton onClick={skipForward} size="small" disabled={!isLoaded}>
          <Forward10Icon />
        </IconButton>
      </Box>
    </Paper>
  );
};

export default AudioPlayer;