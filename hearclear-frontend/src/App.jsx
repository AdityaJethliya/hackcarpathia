// src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Box } from '@mui/material';

// Pages
import HomePage from './pages/HomePage';
import EnhancePage from './pages/EnhancePage';
import PlaybackPage from './pages/PlaybackPage';
import TranscriptPage from './pages/TranscriptPage';
import SettingsPage from './pages/SettingsPage';

// Components
import BottomNav from './components/BottomNav';

// Context Provider
import { AudioProvider } from './contexts/AudioContext';

// Create a theme instance
const theme = createTheme({
  palette: {
    primary: {
      main: '#2196f3',
    },
    secondary: {
      main: '#f50057',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

const App = () => {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <AudioProvider>
        <Router>
          <Box sx={{ pb: 7 }}> {/* Bottom padding for navigation */}
            <Routes>
              <Route path="/" element={<HomePage />} />
              <Route path="/enhance" element={<EnhancePage />} />
              <Route path="/playback" element={<PlaybackPage />} />
              <Route path="/transcript" element={<TranscriptPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
            <BottomNav />
          </Box>
        </Router>
      </AudioProvider>
    </ThemeProvider>
  );
};

export default App;