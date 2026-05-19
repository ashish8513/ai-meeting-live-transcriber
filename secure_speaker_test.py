#!/usr/bin/env python3
"""
Secure speaker diarization test - records audio locally
"""

import numpy as np
import sounddevice as sd
import wave
import os
import time
from speaker import get_speaker_model

def record_audio_securely(filename, duration=5.0, sample_rate=16000):
    """Record audio and save locally (no network transmission)"""
    print(f"🎤 Recording {duration} seconds to {filename}...")
    print("⏰ Start speaking now!")
    
    # Record audio
    audio_data = sd.rec(int(duration * sample_rate), 
                       samplerate=sample_rate, 
                       channels=1, 
                       dtype=np.float32)
    sd.wait()  # Wait until recording is finished
    
    # Save locally (no network)
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit
        wf.setframerate(sample_rate)
        wf.writeframes((audio_data * 32767).astype(np.int16).tobytes())
    
    print(f"✅ Audio saved locally to {filename}")
    return audio_data

def secure_speaker_test():
    """Secure speaker diarization test"""
    print("🔒 SECURE SPEAKER DIARIZATION TEST")
    print("=" * 50)
    print("🎯 Audio stays on your computer - no network transmission!")
    print()
    
    # Check token
    pyannote_token = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
    if not pyannote_token:
        print("❌ Set PYANNOTE_TOKEN first")
        return False
    
    speaker_model = get_speaker_model(threshold=0.70)
    
    print("👥 Testing with multiple speakers...")
    print("📝 Instructions:")
    print("   1. Person 1: Record 5 seconds")
    print("   2. Person 2: Record 5 seconds") 
    print("   3. Person 1: Record again 5 seconds")
    print("   4. Person 2: Record again 5 seconds")
    print()
    
    recordings = []
    
    try:
        for i in range(4):
            if i % 2 == 0:
                print("🎤 PERSON 1 - Speak now!")
            else:
                print("🎤 PERSON 2 - Speak now!")
            
            filename = f"recording_{i+1}.wav"
            
            # Record
            audio_data = record_audio_securely(filename, duration=5.0)
            recordings.append((filename, audio_data))
            
            # Identify speaker
            speaker_label = speaker_model.identify(audio_data, pyannote_token)
            profile_info = speaker_model.get_profile_info()
            
            person = "Person 1" if i % 2 == 0 else "Person 2"
            print(f"🔍 {person} identified as: {speaker_label}")
            print(f"   Total speakers: {profile_info['speaker_count']}")
            print(f"   All speakers: {', '.join(profile_info['speakers'])}")
            print()
            
            time.sleep(2)  # Pause between recordings
    
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    
    # Final results
    profile_info = speaker_model.get_profile_info()
    print("📊 FINAL RESULTS:")
    print(f"   Total speakers detected: {profile_info['speaker_count']}")
    print(f"   Speaker labels: {profile_info['speakers']}")
    print(f"   Threshold used: {profile_info['threshold']}")
    
    # Clean up local files
    print("\n🗑️  Cleaning up local files...")
    for filename, _ in recordings:
        try:
            os.remove(filename)
            print(f"   Removed {filename}")
        except:
            pass
    
    return True

if __name__ == "__main__":
    success = secure_speaker_test()
    
    if success:
        print("\n🎉 Secure speaker diarization test completed!")
        print("🔒 All audio processing was done locally")
    else:
        print("\n❌ Test failed")
    
    exit(0 if success else 1)
