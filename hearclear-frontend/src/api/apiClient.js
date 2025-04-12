// src/api/apiClient.js
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000'; // Change to your backend URL

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'multipart/form-data',
  },
});

// Audio enhancement API calls
export const enhanceAudio = async (audioFile, enhancementParams) => {
  const formData = new FormData();
  formData.append('audio_file', audioFile);
  formData.append('speed_factor', enhancementParams.speedFactor);
  formData.append('volume_factor', enhancementParams.volumeFactor);
  formData.append('remove_noise', enhancementParams.removeNoise);
  formData.append('enhance_clarity', enhancementParams.enhanceClarity);

  const response = await apiClient.post('/enhance-audio/', formData);
  return response.data;
};

export const downloadEnhancedAudio = (fileId) => {
  return `${API_BASE_URL}/download-enhanced/${fileId}`;
};

export const streamProcessAudio = async (audioFile, enhancementParams) => {
  const formData = new FormData();
  formData.append('audio_file', audioFile);
  formData.append('speed_factor', enhancementParams.speedFactor);
  formData.append('volume_factor', enhancementParams.volumeFactor);
  formData.append('remove_noise', enhancementParams.removeNoise);
  formData.append('enhance_clarity', enhancementParams.enhanceClarity);

  const response = await apiClient.post('/process-audio-stream/', formData, {
    responseType: 'blob',
  });
  return response.data;
};

// Transcription API calls
export const transcribeAudio = async (fileId, language = null) => {
  const params = language ? { language } : {};
  const response = await apiClient.post(`/transcribe/${fileId}`, null, { params });
  return response.data;
};

export const queryTranscript = async (fileId, question) => {
  const response = await apiClient.post(`/query-transcript/${fileId}`, null, {
    params: { question },
  });
  return response.data;
};

export default apiClient;