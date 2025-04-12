// src/hooks/useAudioEnhancement.js
import { useState, useCallback } from 'react';
import { enhanceAudio, downloadEnhancedAudio, streamProcessAudio } from '../api/apiClient';

/**
 * Custom hook for handling audio enhancement functionality
 */
const useAudioEnhancement = () => {
  const [isProcessing, setIsProcessing] = useState(false);
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  
  /**
   * Enhance audio with the given parameters
   * @param {File} audioFile - The audio file to enhance
   * @param {Object} params - Enhancement parameters
   * @param {boolean} streamMode - Whether to use streaming mode
   * @returns {Promise<Object>} - Enhancement result
   */
  const processAudio = useCallback(async (audioFile, params, streamMode = false) => {
    if (!audioFile) {
      setError('No audio file provided');
      return null;
    }
    
    setIsProcessing(true);
    setError(null);
    setProgress(0);
    
    try {
      // Simulate progress updates
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          const newProgress = prev + (5 + Math.random() * 10);
          return newProgress >= 90 ? 90 : newProgress;
        });
      }, 300);
      
      let enhancementResult;
      let enhancedUrl;
      
      if (streamMode) {
        // Stream mode returns audio directly
        const blob = await streamProcessAudio(audioFile, params);
        enhancedUrl = URL.createObjectURL(blob);
        enhancementResult = {
          file_id: 'stream-' + Date.now(),
          original_filename: audioFile.name,
          enhanced_filename: `enhanced_${audioFile.name}`,
          processing_stats: {
            speed_factor: params.speedFactor,
            volume_factor: params.volumeFactor,
            noise_removal_applied: params.removeNoise,
            clarity_enhancement_applied: params.enhanceClarity
          },
          duration_seconds: 0 // Not available in stream mode
        };
      } else {
        // Regular mode returns metadata, then we get the file
        enhancementResult = await enhanceAudio(audioFile, params);
        enhancedUrl = downloadEnhancedAudio(enhancementResult.file_id);
      }
      
      clearInterval(progressInterval);
      setProgress(100);
      setResult({
        ...enhancementResult,
        enhancedUrl
      });
      
      setIsProcessing(false);
      return {
        ...enhancementResult,
        enhancedUrl
      };
      
    } catch (err) {
      setIsProcessing(false);
      setError(err.message || 'Error enhancing audio');
      console.error('Audio enhancement error:', err);
      return null;
    }
  }, []);
  
  /**
   * Reset the enhancement state
   */
  const reset = useCallback(() => {
    setIsProcessing(false);
    setError(null);
    setProgress(0);
    setResult(null);
  }, []);
  
  return {
    processAudio,
    isProcessing,
    error,
    progress,
    result,
    reset
  };
};

export default useAudioEnhancement;