// src/api/googleApiClient.js
import axios from 'axios';

const API_KEY = process.env.REACT_APP_GOOGLE_API_KEY;

export const translateText = async (text, targetLanguage = 'es') => {
  try {
    const response = await axios.post(
      `https://translation.googleapis.com/language/translate/v2?key=${API_KEY}`,
      {
        q: text,
        target: targetLanguage,
        format: 'text'
      }
    );
    return response.data.data.translations[0].translatedText;
  } catch (error) {
    console.error('Translation error:', error);
    throw new Error('Failed to translate text: ' + error.message);
  }
};

export const textToSpeech = async (text, voice = 'en-US-Neural2-A') => {
  try {
    const response = await axios.post(
      `https://texttospeech.googleapis.com/v1/text:synthesize?key=${API_KEY}`,
      {
        input: { text },
        voice: {
          languageCode: voice.split('-').slice(0, 2).join('-'),
          name: voice
        },
        audioConfig: {
          audioEncoding: 'MP3'
        }
      }
    );
    
    // Convert base64 audio content to blob URL
    const audioContent = response.data.audioContent;
    const binaryData = atob(audioContent);
    const bytes = new Uint8Array(binaryData.length);
    for (let i = 0; i < binaryData.length; i++) {
      bytes[i] = binaryData.charCodeAt(i);
    }
    const audioBlob = new Blob([bytes], { type: 'audio/mp3' });
    return URL.createObjectURL(audioBlob);
  } catch (error) {
    console.error('Text-to-Speech error:', error);
    throw new Error('Failed to convert text to speech: ' + error.message);
  }
};

// Add Speech-to-Text functionality
export const speechToText = async (audioBlob, languageCode = 'en-US') => {
  try {
    // Convert audio blob to base64
    const reader = new FileReader();
    const audioBase64 = await new Promise((resolve, reject) => {
      reader.onload = () => {
        const base64 = reader.result.split(',')[1];
        resolve(base64);
      };
      reader.onerror = reject;
      reader.readAsDataURL(audioBlob);
    });
    
    const response = await axios.post(
      `https://speech.googleapis.com/v1/speech:recognize?key=${API_KEY}`,
      {
        config: {
          encoding: 'WEBM_OPUS',
          sampleRateHertz: 48000,
          languageCode: languageCode,
          enableAutomaticPunctuation: true,
        },
        audio: {
          content: audioBase64
        }
      }
    );
    
    if (response.data.results && response.data.results.length > 0) {
      return response.data.results[0].alternatives[0].transcript;
    }
    
    return '';
  } catch (error) {
    console.error('Speech-to-Text error:', error);
    throw new Error('Failed to convert speech to text: ' + error.message);
  }
};