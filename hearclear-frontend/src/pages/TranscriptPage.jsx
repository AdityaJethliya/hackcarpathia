// src/pages/TranscriptPage.jsx
import React, { useState, useEffect } from 'react';
import { Container, Typography, Box, Button, TextField, Paper, Divider, Chip } from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import SearchIcon from '@mui/icons-material/Search';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import { useNavigate } from 'react-router-dom';
import { useAudio } from '../contexts/AudioContext';
import { queryTranscript } from '../api/apiClient';

const TranscriptPage = () => {
  const navigate = useNavigate();
  const { transcript, enhancedAudioUrl } = useAudio();
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  
  // Redirect if no transcript is available
  useEffect(() => {
    if (!transcript) {
      navigate('/');
    }
  }, [transcript, navigate]);

  const handleQuestionChange = (event) => {
    setQuestion(event.target.value);
  };

  const handleSearch = async () => {
    if (!question.trim() || !transcript || !transcript.file_id) return;
    
    setIsSearching(true);
    try {
      const result = await queryTranscript(transcript.file_id, question);
      setAnswer(result);
    } catch (error) {
      console.error('Error searching transcript:', error);
      alert('Failed to search the transcript. Please try again.');
    } finally {
      setIsSearching(false);
    }
  };

  const handleCopyTranscript = () => {
    if (transcript && transcript.text) {
      navigator.clipboard.writeText(transcript.text)
        .then(() => {
          alert('Transcript copied to clipboard');
        })
        .catch(err => {
          console.error('Failed to copy: ', err);
        });
    }
  };

  if (!transcript) {
    return <Typography>Loading...</Typography>;
  }

  return (
    <Container maxWidth="sm" sx={{ py: 4 }}>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <Button 
            startIcon={<ArrowBackIcon />} 
            onClick={() => navigate('/playback')}
            sx={{ mr: 2 }}
          >
            Back
          </Button>
          <Typography variant="h5" component="h1">
            Transcript
          </Typography>
        </Box>
        
        <Button
          size="small"
          startIcon={<ContentCopyIcon />}
          onClick={handleCopyTranscript}
        >
          Copy
        </Button>
      </Box>
      
      <Paper elevation={2} sx={{ p: 2, mb: 4, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            placeholder="Ask a question about the transcript..."
            value={question}
            onChange={handleQuestionChange}
            size="small"
            InputProps={{
              endAdornment: (
                <Button 
                  onClick={handleSearch}
                  disabled={isSearching || !question.trim()}
                  sx={{ minWidth: 'auto' }}
                >
                  <SearchIcon />
                </Button>
              ),
            }}
          />
        </Box>
        
        {answer && (
          <Paper 
            variant="outlined" 
            sx={{ p: 2, mb: 2, borderRadius: 2, bgcolor: '#f5f5f5' }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Answer:
            </Typography>
            <Typography variant="body1" paragraph>
              {answer.text}
            </Typography>
            {answer.start_time && (
              <Chip 
                icon={<AccessTimeIcon />} 
                label={`${Math.floor(answer.start_time / 60)}:${Math.floor(answer.start_time % 60).toString().padStart(2, '0')} - ${Math.floor(answer.end_time / 60)}:${Math.floor(answer.end_time % 60).toString().padStart(2, '0')}`}
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Paper>
        )}
      </Paper>
      
      <Paper elevation={2} sx={{ p: 2, borderRadius: 2 }}>
        <Typography variant="h6" gutterBottom>
          Full Transcript
        </Typography>
        
        <Box sx={{ maxHeight: '60vh', overflowY: 'auto', pr: 1 }}>
          {transcript.segments.map((segment, index) => (
            <Box key={index} sx={{ mb: 2 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                <Typography variant="caption" color="textSecondary">
                  {segment.start}
                </Typography>
                <Typography variant="caption" color="textSecondary">
                  {segment.end}
                </Typography>
              </Box>
              <Typography variant="body1">
                {segment.text}
              </Typography>
              {index < transcript.segments.length - 1 && <Divider sx={{ mt: 1 }} />}
            </Box>
          ))}
        </Box>
      </Paper>
    </Container>
  );
};

export default TranscriptPage;