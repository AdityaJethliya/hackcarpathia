// src/components/BottomNav.jsx
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Paper, BottomNavigation, BottomNavigationAction } from '@mui/material';
import HomeIcon from '@mui/icons-material/Home';
import TuneIcon from '@mui/icons-material/Tune';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import TextsmsIcon from '@mui/icons-material/Textsms';
import SettingsIcon from '@mui/icons-material/Settings';
import { useAudio } from '../contexts/AudioContext';

const BottomNav = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { originalAudio, enhancedAudioUrl, transcript } = useAudio();
  
  const getActiveRoute = () => {
    if (location.pathname === '/') return 0;
    if (location.pathname === '/enhance') return 1;
    if (location.pathname === '/playback') return 2;
    if (location.pathname === '/transcript') return 3;
    if (location.pathname === '/settings') return 4;
    return 0;
  };

  const handleNavChange = (event, newValue) => {
    switch (newValue) {
      case 0:
        navigate('/');
        break;
      case 1:
        if (originalAudio) {
          navigate('/enhance');
        }
        break;
      case 2:
        if (enhancedAudioUrl) {
          navigate('/playback');
        }
        break;
      case 3:
        if (transcript) {
          navigate('/transcript');
        }
        break;
      case 4:
        navigate('/settings');
        break;
      default:
        navigate('/');
    }
  };

  return (
    <Paper 
      sx={{ 
        position: 'fixed', 
        bottom: 0, 
        left: 0, 
        right: 0, 
        zIndex: 1100,
        elevation: 3
      }} 
      elevation={3}
    >
      <BottomNavigation
        value={getActiveRoute()}
        onChange={handleNavChange}
        showLabels
      >
        <BottomNavigationAction 
          label="Home" 
          icon={<HomeIcon />} 
        />
        <BottomNavigationAction 
          label="Enhance" 
          icon={<TuneIcon />} 
          disabled={!originalAudio}
        />
        <BottomNavigationAction 
          label="Playback" 
          icon={<PlayArrowIcon />} 
          disabled={!enhancedAudioUrl}
        />
        <BottomNavigationAction 
          label="Transcript" 
          icon={<TextsmsIcon />} 
          disabled={!transcript}
        />
        <BottomNavigationAction 
          label="Settings" 
          icon={<SettingsIcon />} 
        />
      </BottomNavigation>
    </Paper>
  );
};

export default BottomNav;