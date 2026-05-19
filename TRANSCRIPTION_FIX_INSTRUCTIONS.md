# Transcription Issue Fix - "mmhmm" Problem

## Problem Identified
The system was transcribing "mmhmm" repeatedly instead of actual speech ("testing", "can you hear me?").

## Root Causes Found

1. **VAD (Voice Activity Detection) Too Lenient**
   - `VAD_AGGRESSIVENESS` was set to 0 (too lenient, accepting all noise)
   - `VAD_MIN_VOICED_RATIO` was set to 0.00 (accepting everything, even silence)
   - This caused the system to process background noise as speech

2. **RMS Threshold Too Low**
   - `RMS_MIN_LEVEL` was set to 0.0001 (accepting very quiet audio)
   - Background noise was passing through and being transcribed

3. **Audio Normalization Issues**
   - WebRTC audio was not properly normalized
   - Quiet audio wasn't being boosted appropriately

## Fixes Applied

### 1. realtime_transcriber.py
- Changed default `VAD_AGGRESSIVENESS` from 3 to 1 (moderate filtering)
- Changed default `VAD_MIN_VOICED_RATIO` from 0.2 to 0.05 (balanced)
- Added debug logging when audio passes VAD to help troubleshooting

### 2. webrtc_ingest.py
- Improved audio normalization logic
- Added gain boost for quiet audio (with 3x cap to prevent over-amplification)
- Added proper clipping to [-1, 1] range

### 3. run_backend.ps1
- Updated `VAD_MIN_VOICED_RATIO` from 0.00 to 0.05
- Updated `VAD_AGGRESSIVENESS` from 0 to 1
- Updated `RMS_MIN_LEVEL` from 0.0001 to 0.002

## How to Apply the Fix

### Step 1: Stop All Running Services
Close all PowerShell windows running:
- nlp_service.py
- realtime_transcriber.py
- webrtc_ingest.py
- frontend (npm run dev)

Or use Task Manager to end the Python/Node processes.

### Step 2: Restart Services
Run the updated startup script:
```powershell
.\run_backend.ps1
```

This will start all services with the new configuration.

### Step 3: Test the Fix
1. Open your browser to http://localhost:3000
2. Allow microphone access
3. Speak clearly: "testing, can you hear me?"
4. You should now see the correct transcription instead of "mmhmm"

## What to Monitor

Watch the realtime_transcriber logs for:
- `Audio passed VAD: ratio=X.XX, RMS=X.XXXX` - This means audio is being processed
- `VAD filtered: ratio=X.XX < 0.05` - This means silence/noise is being filtered (good)
- `Transcribed: ...` - The final transcription output

## If Issues Persist

### If no audio is being transcribed:
- Lower `VAD_MIN_VOICED_RATIO` to 0.03 in run_backend.ps1
- Lower `RMS_MIN_LEVEL` to 0.001 in run_backend.ps1

### If still getting wrong transcriptions:
- The RNNT model may need more training data for your audio quality
- Consider switching to Whisper by modifying the transcribe_worker() function
- Increase microphone volume/gain in system settings

### If audio is too quiet:
- The WebRTC ingest now has automatic gain control
- Check browser microphone permissions and volume
- Adjust the gain multiplier in webrtc_ingest.py (currently 0.3 / rms, capped at 3.0)

## Technical Details

**VAD Aggressiveness Levels:**
- 0 = Most lenient (accepts more noise)
- 1 = Moderate (balanced) ← **NEW SETTING**
- 2 = Aggressive
- 3 = Very aggressive (was old setting, too strict)

**Voiced Ratio:**
- 0.00 = Accept everything (old setting - BAD)
- 0.05 = Accept if 5% of frames contain voice ← **NEW SETTING**
- 0.20 = Accept if 20% of frames contain voice (old code default)

**RMS Levels:**
- 0.0001 = Very quiet audio accepted (old - too sensitive)
- 0.002 = Normal speech level ← **NEW SETTING**
- 0.01 = Louder speech required
