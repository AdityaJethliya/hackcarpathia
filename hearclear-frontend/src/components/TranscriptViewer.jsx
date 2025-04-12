// src/components/TranscriptViewer.jsx
import React, { useState } from 'react';
import { Typography, Box, Paper, Divider, Chip, TextField, Button } from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

const TranscriptViewer = ({ transcript, onSearch }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResult, setSearchResult] = useState(null);

  const handleSearch = async () => {
    if (!searchQuery.trim() || !onSearch) return;
    
    const result = await onSearch(searchQuery);
    setSearchResult(result);
  };

  if (!transcript || !transcript.segments) {
    return (
      <Typography color="textSecondary" align="center">
        No transcript available
      </Typography>
    );
  }

  return (
    <Box>
      <Paper elevation={2} sx={{ p: 2, mb: 3, borderRadius: 2 }}>
        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <TextField
            fullWidth
            placeholder="Ask a question about the transcript..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            size="small"
            InputProps={{
              endAdornment: (
                <Button 
                  onClick={handleSearch}
                  disabled={!searchQuery.trim()}
                  sx={{ minWidth: 'auto' }}
                >
                  <SearchIcon />
                </Button>
              ),
            }}
          />
        </Box>
        
        {searchResult && (
          <Paper 
            variant="outlined" 
            sx={{ p: 2, borderRadius: 2, bgcolor: '#f5f5f5' }}
          >
            <Typography variant="subtitle2" gutterBottom>
              Answer:
            </Typography>
            <Typography variant="body1" paragraph>
              {searchResult.text}
            </Typography>
            {searchResult.start_time && (
              <Chip 
                icon={<AccessTimeIcon />} 
                label={`${Math.floor(searchResult.start_time / 60)}:${Math.floor(searchResult.start_time % 60).toString().padStart(2, '0')} - ${Math.floor(searchResult.end_time / 60)}:${Math.floor(searchResult.end_time % 60).toString().padStart(2, '0')}`}
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
          Transcript
        </Typography>
        
        <Box sx={{ maxHeight: '50vh', overflowY: 'auto', pr: 1 }}>
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
    </Box>
  );
};

export default TranscriptViewer;