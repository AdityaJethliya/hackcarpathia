// src/pages/SettingsPage.jsx
import React, { useState } from 'react';
import { 
  Container, 
  Typography, 
  Box, 
  Switch, 
  List, 
  ListItem, 
  ListItemText, 
  ListItemIcon, 
  ListItemSecondaryAction,
  Divider,
  Paper,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle
} from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import VolumeUpIcon from '@mui/icons-material/VolumeUp';
import SpeedIcon from '@mui/icons-material/Speed';
import DeleteIcon from '@mui/icons-material/Delete';
import InfoIcon from '@mui/icons-material/Info';
import { useNavigate } from 'react-router-dom';
import { useAudio } from '../contexts/AudioContext';

const SettingsPage = () => {
  const navigate = useNavigate();
  const { resetAudio } = useAudio();
  
  const [darkMode, setDarkMode] = useState(false);
  const [defaultEnhanceVolume, setDefaultEnhanceVolume] = useState(true);
  const [defaultSlowerSpeed, setDefaultSlowerSpeed] = useState(true);
  const [isDialogOpen, setIsDialogOpen] = useState(false);

  const handleToggleChange = (setting) => (event) => {
    switch (setting) {
      case 'darkMode':
        setDarkMode(event.target.checked);
        break;
      case 'enhanceVolume':
        setDefaultEnhanceVolume(event.target.checked);
        break;
      case 'slowerSpeed':
        setDefaultSlowerSpeed(event.target.checked);
        break;
      default:
        break;
    }
  };

  const handleClearData = () => {
    resetAudio();
    setIsDialogOpen(false);
    navigate('/');
  };

  const openConfirmDialog = () => {
    setIsDialogOpen(true);
  };

  const closeConfirmDialog = () => {
    setIsDialogOpen(false);
  };

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Typography variant="h5" component="h1" gutterBottom sx={{ mb: 3 }}>
        Settings
      </Typography>
      
      <Paper elevation={2} sx={{ borderRadius: 2, mb: 4 }}>
        <List disablePadding>
          <ListItem>
            <ListItemIcon>
              <DarkModeIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Dark Mode" 
              secondary="Use dark theme for the app"
            />
            <ListItemSecondaryAction>
              <Switch
                edge="end"
                checked={darkMode}
                onChange={handleToggleChange('darkMode')}
              />
            </ListItemSecondaryAction>
          </ListItem>
          
          <Divider component="li" />
          
          <ListItem>
            <ListItemIcon>
              <VolumeUpIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Enhance Volume by Default" 
              secondary="Automatically increase volume when enhancing audio"
            />
            <ListItemSecondaryAction>
              <Switch
                edge="end"
                checked={defaultEnhanceVolume}
                onChange={handleToggleChange('enhanceVolume')}
              />
            </ListItemSecondaryAction>
          </ListItem>
          
          <Divider component="li" />
          
          <ListItem>
            <ListItemIcon>
              <SpeedIcon />
            </ListItemIcon>
            <ListItemText 
              primary="Slower Speed by Default" 
              secondary="Automatically slow down audio when enhancing"
            />
            <ListItemSecondaryAction>
              <Switch
                edge="end"
                checked={defaultSlowerSpeed}
                onChange={handleToggleChange('slowerSpeed')}
              />
            </ListItemSecondaryAction>
          </ListItem>
        </List>
      </Paper>
      
      <Paper elevation={2} sx={{ p: 2, borderRadius: 2, mb: 4 }}>
        <Typography variant="h6" gutterBottom>
          Data Management
        </Typography>
        
        <Button
          variant="outlined"
          color="error"
          startIcon={<DeleteIcon />}
          onClick={openConfirmDialog}
          fullWidth
          sx={{ mt: 1 }}
        >
          Clear All Audio Data
        </Button>
      </Paper>
      
      <Paper elevation={2} sx={{ p: 2, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
          <InfoIcon color="primary" sx={{ mr: 1 }} />
          <Typography variant="h6">
            About HearClear
          </Typography>
        </Box>
        
        <Typography variant="body2" paragraph>
          HearClear is an audio enhancement application designed to make spoken content easier to hear and understand.
        </Typography>
        
        <Typography variant="body2" paragraph>
          Version 1.0.0
        </Typography>
        
        <Typography variant="body2" color="textSecondary">
          © 2025 HearClear. All rights reserved.
        </Typography>
      </Paper>
      
      <Dialog
        open={isDialogOpen}
        onClose={closeConfirmDialog}
      >
        <DialogTitle>Clear All Data?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            This will remove all audio files, enhancements, and transcripts from the app. This action cannot be undone.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeConfirmDialog} color="primary">
            Cancel
          </Button>
          <Button onClick={handleClearData} color="error">
            Clear All Data
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default SettingsPage;