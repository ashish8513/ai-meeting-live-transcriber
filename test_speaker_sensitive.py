#!/usr/bin/env python3
"""
Speaker diarization test with lower threshold for more sensitive detection
"""

import numpy as np
import wave
import os
from speaker import get_speaker_model

def create_diverse_voices():
    """Create more diverse synthetic voices"""
    print("🎵 Creating diverse test voices...")
    
    sample_rate = 16000
    duration = 3.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # More diverse voice patterns
    voices = []
    
    # Voice 1: Complex male-like (100Hz + harmonics)
    voice1 = 0.3 * (np.sin(2 * np.pi * 100 * t) + 
                   0.5 * np.sin(2 * np.pi * 200 * t) + 
                   0.3 * np.sin(2 * np.pi * 300 * t))
    
    # Voice 2: Complex female-like (250Hz + harmonics)  
    voice2 = 0.3 * (np.sin(2 * np.pi * 250 * t) + 
                   0.5 * np.sin(2 * np.pi * 500 * t) + 
                   0.3 * np.sin(2 * np.pi * 750 * t))
    
    # Voice 3: Child-like (400Hz + higher harmonics)
    voice3 = 0.3 * (np.sin(2 * np.pi * 400 * t) + 
                   0.5 * np.sin(2 * np.pi * 800 * t) + 
                   0.3 * np.sin(2 * np.pi * 1200 * t))
    
    # Voice 4: Deep voice (80Hz + sub-harmonics)
    voice4 = 0.3 * (np.sin(2 * np.pi * 80 * t) + 
                   0.5 * np.sin(2 * np.pi * 160 * t) + 
                   0.3 * np.sin(2 * np.pi * 240 * t))
    
    # Add noise and variation
    for i, voice in enumerate([voice1, voice2, voice3, voice4]):
        # Add slight noise
        voice += 0.02 * np.random.randn(len(voice))
        # Add volume variation
        voice *= (1 + 0.1 * np.sin(2 * np.pi * 2 * t))
        # Convert to int16
        voice = (voice * 32767).astype(np.int16)
        voices.append(voice)
    
    # Save files
    files = []
    for i, voice in enumerate(voices, 1):
        filename = f"diverse_voice_{i}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(voice.tobytes())
        files.append(filename)
        print(f"✅ Created {filename}")
    
    return files

def test_sensitive_speaker():
    """Test with lower threshold for more sensitive detection"""
    print("🎤 Sensitive Speaker Diarization Test")
    print("=" * 50)
    
    # Get token
    pyannote_token = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
    if not pyannote_token:
        print("❌ Set PYANNOTE_TOKEN")
        return False
    
    # Create diverse voices
    files = create_diverse_voices()
    
    # Test with different thresholds
    thresholds = [0.7, 0.6, 0.5, 0.4]
    
    for threshold in thresholds:
        print(f"\n🧪 Testing with threshold: {threshold}")
        print("-" * 30)
        
        # Reset model with new threshold
        speaker_model = get_speaker_model(threshold=threshold)
        
        try:
            for i, filename in enumerate(files, 1):
                # Read audio file
                with wave.open(filename, 'rb') as wf:
                    frames = wf.readframes(-1)
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
                
                # Identify speaker
                speaker_label = speaker_model.identify(audio_data, pyannote_token)
                
                print(f"🎙️  Voice {i}: {speaker_label}")
            
            # Show results
            profile_info = speaker_model.get_profile_info()
            print(f"📊 Total speakers: {profile_info['speaker_count']}")
            print(f"   Labels: {profile_info['speakers']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    # Clean up
    for filename in files:
        try:
            os.remove(filename)
        except:
            pass
    
    return True

if __name__ == "__main__":
    success = test_sensitive_speaker()
    
    if success:
        print("\n🎉 Sensitive speaker test completed!")
        print("🔍 Try different thresholds to see speaker separation")
    else:
        print("\n❌ Test failed")
    
    exit(0 if success else 1)
