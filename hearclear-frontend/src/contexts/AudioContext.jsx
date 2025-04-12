// src/contexts/AudioContext.jsx
import React, { createContext, useState, useContext } from 'react';

const AudioContext = createContext();

export const useAudio = () => useContext(AudioContext);

export const AudioProvider = ({ children }) => {
  const [originalAudio, setOriginalAudio] = useState(null);
  const [originalAudioUrl, setOriginalAudioUrl] = useState(null);
  const [enhancedAudio, setEnhancedAudio] = useState(null);
  const [enhancedAudioUrl, setEnhancedAudioUrl] = useState(null);
  const [audioProcessingResult, setAudioProcessingResult] = useState(null);
  const [transcript, setTranscript] = useState(null);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAudioSelected = (file, url) => {
    setOriginalAudio(file);
    setOriginalAudioUrl(url);
    // Reset any enhanced audio and transcript data when a new file is selected
    setEnhancedAudio(null);
    setEnhancedAudioUrl(null);
    setAudioProcessingResult(null);
    setTranscript(null);
  };

  const handleAudioEnhanced = (result, enhancedUrl) => {
    setAudioProcessingResult(result);
    setEnhancedAudioUrl(enhancedUrl);
    setIsProcessing(false);
  };

  const handleTranscriptReceived = (transcriptData) => {
    setTranscript(transcriptData);
  };

  const resetAudio = () => {
    setOriginalAudio(null);
    setOriginalAudioUrl(null);
    setEnhancedAudio(null);
    setEnhancedAudioUrl(null);
    setAudioProcessingResult(null);
    setTranscript(null);
  };

  return (
    <AudioContext.Provider
      value={{
        originalAudio,
        originalAudioUrl,
        enhancedAudio,
        enhancedAudioUrl,
        audioProcessingResult,
        transcript,
        isProcessing,
        setIsProcessing,
        handleAudioSelected,
        handleAudioEnhanced,
        handleTranscriptReceived,
        resetAudio
      }}
    >
      {children}
    </AudioContext.Provider>
  );
};

export default AudioContext;