#!/usr/bin/env python3
"""
Create a proper test audio file for testing audio separation
"""

import numpy as np
import wave
import tempfile
import os

def create_test_audio(filename, duration=10, sample_rate=44100):
    """Create a test audio file with multiple frequencies"""
    
    # Generate multiple sine waves to simulate different instruments
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create different frequency components
    vocals = 0.3 * np.sin(2 * np.pi * 440 * t)  # A4 note
    drums = 0.2 * np.sin(2 * np.pi * 80 * t)    # Low frequency for bass drum
    bass = 0.25 * np.sin(2 * np.pi * 110 * t)   # A2 note
    other = 0.2 * np.sin(2 * np.pi * 880 * t)   # A5 note
    
    # Combine all components
    audio = vocals + drums + bass + other
    
    # Normalize and convert to 16-bit integers
    audio = np.clip(audio, -1, 1)
    audio_int16 = (audio * 32767).astype(np.int16)
    
    # Write to WAV file
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    
    print(f"Created test audio file: {filename}")
    print(f"Duration: {duration} seconds")
    print(f"Sample rate: {sample_rate} Hz")

if __name__ == "__main__":
    # Create a test file
    test_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    create_test_audio(test_file.name, duration=10)
    print(f"Test file created at: {test_file.name}")
