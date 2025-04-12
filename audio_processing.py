import numpy as np
import librosa
import soundfile as sf
import noisereduce as nr
from scipy import signal

def enhance_audio(audio_data, sr, speed_factor=0.75, volume_factor=1.5, remove_noise=False,
                  enhance_clarity=False):
    """
    Enhanced audio processing with multiple enhancement options.
    
    Args:
        audio_data: numpy array of audio samples
        sr: sample rate
        speed_factor: 0.5-1.0 (lower value = slower speech)
        volume_factor: 1.0-2.0 (higher value = louder speech)
        remove_noise: whether to apply noise reduction
        enhance_clarity: whether to enhance speech clarity
        
    Returns:
        Processed audio as numpy array
    """
    # 1. Time stretching (slow down while preserving pitch)
    speed_factor = max(0.5, min(1.0, speed_factor))  # Clamp between 0.5 and 1.0
    y_stretched = librosa.effects.time_stretch(audio_data, rate=speed_factor)
    
    # 2. Apply noise reduction if selected
    if remove_noise:
        # Using noisereduce library for better noise reduction
        # Estimate noise from the first second
        noise_sample = y_stretched[:int(sr)]
        y_stretched = nr.reduce_noise(
            y=y_stretched, 
            sr=sr,
            prop_decrease=0.8,
            stationary=True
        )
    
    # 3. Enhance speech clarity if selected
    if enhance_clarity:
        # Apply a bandpass filter around speech frequencies (300Hz - 3000Hz)
        sos = signal.butter(4, [300, 3000], 'bandpass', fs=sr, output='sos')
        y_filtered = signal.sosfilt(sos, y_stretched)
        
        # Apply a slight compression to make speech more consistent in volume
        # Simple compression implementation
        threshold = 0.1
        ratio = 0.5
        makeup_gain = 1.2
        
        # Apply compression
        abs_y = np.abs(y_filtered)
        mask = abs_y > threshold
        compressed = np.copy(y_filtered)
        compressed[mask] = threshold + (abs_y[mask] - threshold) * ratio * np.sign(y_filtered[mask])
        
        # Apply makeup gain
        y_stretched = compressed * makeup_gain
    
    # 4. Apply volume adjustment
    volume_factor = max(1.0, min(2.0, volume_factor))  # Clamp between 1.0 and 2.0
    y_enhanced = y_stretched * volume_factor
    
    # Ensure the output doesn't clip
    if np.max(np.abs(y_enhanced)) > 1.0:
        y_enhanced = y_enhanced / np.max(np.abs(y_enhanced))
    
    return y_enhanced

def get_speech_stats(audio_data, sr):
    """
    Analyze speech characteristics of the audio.
    
    Args:
        audio_data: numpy array of audio samples
        sr: sample rate
        
    Returns:
        Dictionary with speech statistics
    """
    try:
        # Extract speech features
        
        # 1. Estimate average speech rate
        onset_env = librosa.onset.onset_strength(y=audio_data, sr=sr)
        tempo, _ = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
        
        # 2. Estimate pitch
        pitches, magnitudes = librosa.piptrack(y=audio_data, sr=sr)
        pitch_indices = np.argmax(magnitudes, axis=0)
        pitches = pitches[pitch_indices, range(magnitudes.shape[1])]
        pitch_mean = np.mean(pitches[pitches > 0])
        
        # 3. Calculate volume (RMS energy)
        rms = librosa.feature.rms(y=audio_data)[0]
        rms_mean = np.mean(rms)
        
        # 4. Detect silences
        non_silent = librosa.effects.split(audio_data, top_db=30)
        silence_percentage = 100 - (sum(e - s for s, e in non_silent) / len(audio_data) * 100)
        
        return {
            "estimated_tempo": float(tempo),
            "average_pitch_hz": float(pitch_mean) if not np.isnan(pitch_mean) else 0,
            "average_volume": float(rms_mean),
            "silence_percentage": float(silence_percentage)
        }
    except Exception as e:
        # Fallback to simpler stats if we hit errors
        rms = librosa.feature.rms(y=audio_data)[0]
        return {
            "average_volume": float(np.mean(rms)),
            "error": str(e)
        }

def save_audio_with_format(audio_data, sr, output_path, format='wav'):
    """
    Save audio with the specified format and parameters.
    
    Args:
        audio_data: numpy array of audio samples
        sr: sample rate
        output_path: path to save the audio file
        format: audio format (wav, mp3, etc.)
    """
    # Set optimal parameters for elderly listening
    if format == 'wav':
        sf.write(output_path, audio_data, sr, subtype='PCM_16')
    else:
        # For non-wav formats, use soundfile with format parameter
        sf.write(output_path, audio_data, sr, format=format)