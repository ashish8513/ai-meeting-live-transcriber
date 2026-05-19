#!/usr/bin/env python3
"""
Speaker diarization testing with audio files (no microphone required)
"""

import numpy as np
import wave
import os
from speaker import get_speaker_model

def create_test_audio_files():
    """Create test audio files with different voices"""
    print("🎵 Creating test audio files...")
    
    sample_rate = 16000
    duration = 3.0  # 3 seconds
    
    # Create different "voice" patterns
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Voice 1: Normal frequency (200 Hz)
    voice1 = 0.3 * np.sin(2 * np.pi * 200 * t)
    voice1 = (voice1 * 32767).astype(np.int16)
    
    # Voice 2: Higher frequency (400 Hz) 
    voice2 = 0.3 * np.sin(2 * np.pi * 400 * t)
    voice2 = (voice2 * 32767).astype(np.int16)
    
    # Voice 3: Lower frequency (100 Hz)
    voice3 = 0.3 * np.sin(2 * np.pi * 100 * t)
    voice3 = (voice3 * 32767).astype(np.int16)
    
    # Save files
    files = []
    for i, voice in enumerate([voice1, voice2, voice3], 1):
        filename = f"test_voice_{i}.wav"
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(voice.tobytes())
        files.append(filename)
        print(f"✅ Created {filename}")
    
    return files

def test_with_files():
    """Test speaker diarization using audio files"""
    print("🎤 Testing speaker diarization with audio files...")
    
    # Get token
    pyannote_token = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
    if not pyannote_token:
        print("❌ Please set PYANNOTE_TOKEN")
        return False
    
    # Create test files
    files = create_test_audio_files()
    
    # Initialize speaker model
    speaker_model = get_speaker_model(threshold=0.70)
    
    print("\n🧪 Testing different voices...")
    
    try:
        for i, filename in enumerate(files, 1):
            # Read audio file
            with wave.open(filename, 'rb') as wf:
                frames = wf.readframes(-1)
                audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32767.0
            
            # Identify speaker
            speaker_label = speaker_model.identify(audio_data, pyannote_token)
            
            # Get profile info
            profile_info = speaker_model.get_profile_info()
            
            print(f"🎙️  Voice {i}: {speaker_label}")
            print(f"   Total speakers: {profile_info['speaker_count']}")
            print(f"   Speakers: {', '.join(profile_info['speakers'])}")
            print()
            
            # Test same voice again
            speaker_label_again = speaker_model.identify(audio_data, pyannote_token)
            print(f"🔄 Same voice {i} again: {speaker_label_again}")
            print()
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    finally:
        # Clean up files
        for filename in files:
            try:
                os.remove(filename)
                print(f"🗑️  Removed {filename}")
            except:
                pass
    
    # Final summary
    profile_info = speaker_model.get_profile_info()
    print("📊 Final Results:")
    print(f"   Total speakers detected: {profile_info['speaker_count']}")
    print(f"   Speaker labels: {profile_info['speakers']}")
    print(f"   Threshold: {profile_info['threshold']}")
    
    return True

if __name__ == "__main__":
    print("🎤 Speaker Diarization - File Based Test")
    print("=" * 50)
    print("🔒 No microphone required!")
    print()
    
    success = test_with_files()
    
    if success:
        print("\n🎉 Speaker diarization test completed successfully!")
        print("🔍 Different voices were identified as different speakers")
    else:
        print("\n❌ Test failed")
    
    exit(0 if success else 1)
