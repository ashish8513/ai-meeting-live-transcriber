#!/usr/bin/env python3
"""
Real-time speaker diarization test using microphone input.
"""

import numpy as np
import sounddevice as sd
import time
import os
from speaker import get_speaker_model

def test_real_time_speaker_detection():
    """Test speaker identification with real microphone input."""
    print("🎤 Real-Time Speaker Detection Test")
    print("=" * 50)
    
    # Check for token
    pyannote_token = os.getenv("PYANNOTE_TOKEN") or os.getenv("HF_TOKEN")
    if not pyannote_token:
        print("❌ Please set PYANNOTE_TOKEN environment variable")
        return False
    
    print("✅ Speaker identification enabled")
    
    # Get speaker model
    speaker_model = get_speaker_model(threshold=0.70)
    
    # Audio settings
    SAMPLE_RATE = 16000
    CHUNK_DURATION = 3.0  # 3 seconds chunks
    CHUNK_SIZE = int(SAMPLE_RATE * CHUNK_DURATION)
    
    print(f"🎧 Listening for {CHUNK_DURATION}s chunks...")
    print("👥 Speak with different voices to test speaker identification")
    print("🛑 Press Ctrl+C to stop")
    
    try:
        def audio_callback(indata, frames, time_info, status):
            if status:
                print(f"Audio callback status: {status}")
            
            # Process audio chunk
            audio_chunk = indata.flatten()
            
            if len(audio_chunk) >= CHUNK_SIZE:
                try:
                    # Identify speaker
                    speaker_label = speaker_model.identify(audio_chunk, pyannote_token)
                    
                    # Get profile info
                    profile_info = speaker_model.get_profile_info()
                    
                    # Display results
                    timestamp = time.strftime("%H:%M:%S")
                    print(f"[{timestamp}] 🎙️  {speaker_label} | "
                          f"Total speakers: {profile_info['speaker_count']} | "
                          f"Speakers: {', '.join(profile_info['speakers'])}")
                    
                except Exception as e:
                    print(f"❌ Speaker identification error: {e}")
        
        # Start audio stream
        with sd.InputStream(callback=audio_callback,
                           channels=1,
                           samplerate=SAMPLE_RATE,
                           dtype=np.float32,
                           blocksize=CHUNK_SIZE):
            print("🎯 Listening... Start speaking!")
            
            # Keep listening indefinitely
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🛑 Test stopped by user")
        
        # Final summary
        profile_info = speaker_model.get_profile_info()
        print(f"\n📊 Final Results:")
        print(f"   Total speakers detected: {profile_info['speaker_count']}")
        print(f"   Speaker labels: {profile_info['speakers']}")
        print(f"   Threshold used: {profile_info['threshold']}")
        print(f"   Device: {profile_info['device']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Audio stream error: {e}")
        return False

def test_two_speaker_scenario():
    """Test with predefined two-speaker scenario."""
    print("\n👥 Two-Speaker Test Scenario")
    print("=" * 50)
    print("📋 Instructions:")
    print("   1. Person 1: Speak for 5 seconds ('Hello, this is speaker one')")
    print("   2. Person 2: Speak for 5 seconds ('Hi, this is speaker two')") 
    print("   3. Alternate between speakers for 30 seconds")
    print("   4. Watch for speaker label changes")
    
    input("\n🎯 Press Enter to start two-speaker test...")
    
    return test_real_time_speaker_detection()

def main():
    """Main test function."""
    print("🎤 Speaker Diarization Real-Time Test")
    print("=" * 60)
    
    # Check audio device
    try:
        devices = sd.query_devices()
        print(f"🎧 Found {len(devices)} audio devices")
        
        # Show default input device
        default_input = sd.default.device[0]
        if default_input >= 0:
            print(f"📱 Default input device: {devices[default_input]['name']}")
        else:
            print("⚠️  No default input device found")
            
    except Exception as e:
        print(f"❌ Audio device error: {e}")
        return False
    
    # Test options
    print("\n🧪 Test Options:")
    print("1. Real-time speaker detection")
    print("2. Two-speaker scenario test")
    print("3. Exit")
    
    while True:
        try:
            choice = input("\n🎯 Choose test (1-3): ").strip()
            
            if choice == "1":
                return test_real_time_speaker_detection()
            elif choice == "2":
                return test_two_speaker_scenario()
            elif choice == "3":
                print("👋 Exiting...")
                return True
            else:
                print("❌ Invalid choice. Please enter 1, 2, or 3.")
                
        except KeyboardInterrupt:
            print("\n👋 Test interrupted...")
            return True
        except Exception as e:
            print(f"❌ Error: {e}")
            return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
