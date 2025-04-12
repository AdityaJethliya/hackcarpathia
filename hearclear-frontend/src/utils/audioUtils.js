// src/utils/audioUtils.js

/**
 * Creates a waveform visualization of an audio file on a canvas element
 * @param {Blob} audioBlob - The audio blob to visualize
 * @param {HTMLCanvasElement} canvas - The canvas element to draw on
 */
export const createWaveform = async (audioBlob, canvas) => {
    try {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      // Fetch and decode the audio data
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioData = await audioContext.decodeAudioData(arrayBuffer);
      
      // Get the time-domain data
      const channelData = audioData.getChannelData(0);
      
      // Set up the canvas
      const ctx = canvas.getContext('2d');
      const width = canvas.width = canvas.offsetWidth;
      const height = canvas.height = canvas.offsetHeight;
      
      // Clear the canvas
      ctx.clearRect(0, 0, width, height);
      
      // Draw the waveform
      ctx.beginPath();
      ctx.strokeStyle = '#2196f3';
      ctx.lineWidth = 2;
      
      // Sample the audio data to fit the canvas width
      const step = Math.ceil(channelData.length / width);
      const amplitude = height / 2;
      
      for (let i = 0; i < width; i++) {
        const sampleIndex = Math.floor(i * step);
        let min = 1.0;
        let max = -1.0;
        
        // Find min/max values in the current sample segment
        for (let j = 0; j < step; j++) {
          const datum = channelData[sampleIndex + j];
          if (datum < min) min = datum;
          if (datum > max) max = datum;
        }
        
        // Draw the vertical line segment
        const x = i;
        const y1 = (1 + min) * amplitude;
        const y2 = (1 + max) * amplitude;
        
        if (i === 0) {
          ctx.moveTo(x, y1);
        } else {
          ctx.lineTo(x, y1);
          ctx.lineTo(x, y2);
        }
      }
      
      ctx.stroke();
      
      // Clean up
      URL.revokeObjectURL(audioUrl);
      
    } catch (error) {
      console.error('Error creating waveform:', error);
    }
  };
  
  /**
   * Converts raw audio data to a WAV file
   * @param {Float32Array} audioData - Raw audio data
   * @param {number} sampleRate - Audio sample rate
   * @returns {Blob} - WAV file as blob
   */
  export const audioBufferToWav = (audioData, sampleRate) => {
    const numChannels = 1; // Mono
    const bitDepth = 16;
    
    // Create the buffer for the WAV file
    const buffer = new ArrayBuffer(44 + audioData.length * 2);
    const view = new DataView(buffer);
    
    // RIFF identifier
    writeString(view, 0, 'RIFF');
    // File length
    view.setUint32(4, 36 + audioData.length * 2, true);
    // RIFF type
    writeString(view, 8, 'WAVE');
    // Format chunk identifier
    writeString(view, 12, 'fmt ');
    // Format chunk length
    view.setUint32(16, 16, true);
    // Sample format (raw)
    view.setUint16(20, 1, true);
    // Channel count
    view.setUint16(22, numChannels, true);
    // Sample rate
    view.setUint32(24, sampleRate, true);
    // Byte rate (sample rate * block align)
    view.setUint32(28, sampleRate * numChannels * bitDepth / 8, true);
    // Block align (channel count * bytes per sample)
    view.setUint16(32, numChannels * bitDepth / 8, true);
    // Bits per sample
    view.setUint16(34, bitDepth, true);
    // Data chunk identifier
    writeString(view, 36, 'data');
    // Data chunk length
    view.setUint32(40, audioData.length * 2, true);
    
    // Write the PCM samples
    const volume = 1;
    let index = 44;
    for (let i = 0; i < audioData.length; i++) {
      // Clamp value between -1 and 1
      const sample = Math.max(-1, Math.min(1, audioData[i]));
      // Convert to 16-bit signed integer
      view.setInt16(index, sample < 0 ? sample * 0x8000 : sample * 0x7FFF, true);
      index += 2;
    }
    
    return new Blob([view], { type: 'audio/wav' });
  };
  
  /**
   * Helper function to write a string to a DataView
   */
  function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  }
  
  /**
   * Analyzes audio for statistics
   * @param {Blob} audioBlob - Audio blob to analyze
   * @returns {Promise<Object>} - Audio statistics
   */
  export const analyzeAudio = async (audioBlob) => {
    try {
      const audioUrl = URL.createObjectURL(audioBlob);
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      // Fetch and decode the audio data
      const response = await fetch(audioUrl);
      const arrayBuffer = await response.arrayBuffer();
      const audioData = await audioContext.decodeAudioData(arrayBuffer);
      
      // Get the time-domain data
      const channelData = audioData.getChannelData(0);
      
      // Calculate RMS (volume)
      let sum = 0;
      for (let i = 0; i < channelData.length; i++) {
        sum += channelData[i] * channelData[i];
      }
      const rms = Math.sqrt(sum / channelData.length);
      
      // Calculate duration
      const duration = audioData.duration;
      
      // Calculate silence percentage
      const silenceThreshold = 0.01;
      let silenceSamples = 0;
      for (let i = 0; i < channelData.length; i++) {
        if (Math.abs(channelData[i]) < silenceThreshold) {
          silenceSamples++;
        }
      }
      const silencePercentage = (silenceSamples / channelData.length) * 100;
      
      // Clean up
      URL.revokeObjectURL(audioUrl);
      
      return {
        duration,
        rms,
        volume: rms * 100,
        silencePercentage
      };
      
    } catch (error) {
      console.error('Error analyzing audio:', error);
      return {
        error: error.message
      };
    }
  };