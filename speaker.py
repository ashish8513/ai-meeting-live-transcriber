import numpy as np
import torch
from sklearn.metrics.pairwise import cosine_similarity
import os
import warnings
from typing import Optional, Dict, Any

# Suppress warnings about torchaudio backend
warnings.filterwarnings("ignore", message="torchaudio.set_audio_backend.*", module=".*")


class SpeakerModel:
    """
    Real-time speaker diarization using pyannote embeddings.
    
    This class identifies speakers automatically by comparing audio chunk embeddings
    against stored speaker profiles using cosine similarity.
    """
    
    def __init__(self, embedder=None, threshold: float = 0.70, device: str = "auto"):
        """
        Initialize the speaker model.
        
        Args:
            embedder: Pre-loaded pyannote embedding model
            threshold: Similarity threshold for speaker identification (0.0-1.0)
            device: Device to run embeddings on ("auto", "cpu", "cuda")
        """
        self.embedder = embedder
        self.threshold = threshold
        self.profiles: Dict[str, np.ndarray] = {}
        self.device = self._determine_device(device)
        self._init_attempted = False
        
    def _determine_device(self, device: str) -> str:
        """Determine the appropriate device for computation."""
        if device == "auto":
            return "cuda" if torch.cuda.is_available() else "cpu"
        return device
        
    def _load_embedder(self, pyannote_token: Optional[str] = None) -> bool:
        """
        Load the pyannote embedding model if not already loaded.
        
        Args:
            pyannote_token: Hugging Face token for pyannote model
            
        Returns:
            True if embedder loaded successfully, False otherwise
        """
        if self.embedder is not None or self._init_attempted:
            return self.embedder is not None
            
        self._init_attempted = True
        
        if not pyannote_token:
            print("SpeakerModel: No pyannote token provided. Speaker identification disabled.")
            return False
            
        try:
            # PyTorch 2.6+ defaults weights_only=True; pyannote checkpoints need False.
            _orig_torch_load = torch.load

            def _torch_load_compat(*args, **kwargs):
                kwargs.setdefault("weights_only", False)
                return _orig_torch_load(*args, **kwargs)

            torch.load = _torch_load_compat  # type: ignore[method-assign]

            # Patch torchaudio to handle the set_audio_backend issue
            import torchaudio
            if not hasattr(torchaudio, 'set_audio_backend'):
                # Add a dummy set_audio_backend function if it doesn't exist
                torchaudio.set_audio_backend = lambda *args, **kwargs: None
            
            from pyannote.audio import Model
            print("SpeakerModel: Loading pyannote embedding model...")
            self.embedder = Model.from_pretrained("pyannote/embedding", use_auth_token=pyannote_token)
            
            if self.embedder is not None:
                self.embedder = self.embedder.to(self.device)
                print(f"SpeakerModel: Model loaded successfully on {self.device}")
                return True
            else:
                print("SpeakerModel: Failed to load model - None returned")
                return False
                
        except Exception as e:
            print(f"SpeakerModel: Failed to load pyannote model - {type(e).__name__}: {e}")
            self.embedder = None
            return False
            
    def _extract_embedding(self, audio_chunk: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract embedding from audio chunk.
        
        Args:
            audio_chunk: Audio data as numpy array (float32, mono)
            
        Returns:
            Embedding vector or None if extraction fails
        """
        if self.embedder is None:
            return None
            
        try:
            # Ensure audio is float32 and mono
            audio = audio_chunk.astype(np.float32)
            if audio.ndim > 1:
                audio = audio.squeeze()
                
            # Resample to 16kHz if needed (pyannote expects 16kHz)
            target_sr = 16000
            if hasattr(audio_chunk, 'sample_rate'):
                current_sr = audio_chunk.sample_rate
            else:
                # Assume 16kHz if no sample rate info
                current_sr = 16000
                
            if current_sr != target_sr:
                # Simple linear resampling
                audio = self._resample_audio(audio, current_sr, target_sr)
                
            # Convert to tensor and add batch dimension
            waveform = torch.from_numpy(audio).to(self.device)
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
                
            # Extract embedding
            with torch.no_grad():
                embedding = self.embedder(waveform)
                
            return embedding.cpu().numpy()
            
        except Exception as e:
            print(f"SpeakerModel: Embedding extraction failed - {type(e).__name__}: {e}")
            return None
            
    def _resample_audio(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """Simple linear resampling of audio."""
        if orig_sr == target_sr:
            return audio
            
        n_samples = int(len(audio) * target_sr / orig_sr)
        if n_samples <= 0:
            return audio
            
        # Linear interpolation
        x_old = np.linspace(0.0, 1.0, num=len(audio), endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_samples, endpoint=False)
        resampled = np.interp(x_new, x_old, audio)
        
        return resampled.astype(np.float32)
        
    def identify(self, audio_chunk: np.ndarray, pyannote_token: Optional[str] = None) -> str:
        """
        Identify the speaker for a given audio chunk.
        
        Args:
            audio_chunk: Audio data as numpy array (float32, mono)
            pyannote_token: Hugging Face token (only needed for first call)
            
        Returns:
            Speaker label (e.g., "Speaker 1", "Speaker 2", etc.)
        """
        # Try to load embedder if not already loaded
        if not self._load_embedder(pyannote_token):
            return "Speaker"
            
        # Extract embedding from audio chunk
        embedding = self._extract_embedding(audio_chunk)
        if embedding is None:
            return "Speaker"
            
        # If no profiles exist, create first speaker
        if len(self.profiles) == 0:
            speaker_label = "Speaker 1"
            self.profiles[speaker_label] = embedding
            print(f"SpeakerModel: Created {speaker_label} profile")
            return speaker_label
            
        # Compare with existing speaker profiles
        similarities = {}
        for speaker_id, profile_embedding in self.profiles.items():
            try:
                similarity = cosine_similarity(embedding, profile_embedding)[0][0]
                similarities[speaker_id] = similarity
            except Exception as e:
                print(f"SpeakerModel: Similarity calculation failed for {speaker_id} - {e}")
                similarities[speaker_id] = 0.0
                
        # Find best matching speaker
        if similarities:
            best_speaker, best_score = max(similarities.items(), key=lambda x: x[1])
            
            if best_score >= self.threshold:
                return best_speaker
                
        # Create new speaker if no good match found
        new_speaker_id = f"Speaker {len(self.profiles) + 1}"
        self.profiles[new_speaker_id] = embedding
        print(f"SpeakerModel: Created {new_speaker_id} profile (best score: {best_score:.2f})")
        return new_speaker_id
        
    def get_speaker_count(self) -> int:
        """Get the number of registered speakers."""
        return len(self.profiles)
        
    def get_speaker_labels(self) -> list:
        """Get list of all speaker labels."""
        return list(self.profiles.keys())
        
    def reset_profiles(self):
        """Clear all speaker profiles."""
        self.profiles.clear()
        print("SpeakerModel: All speaker profiles cleared")
        
    def update_threshold(self, new_threshold: float):
        """Update the similarity threshold."""
        if 0.0 <= new_threshold <= 1.0:
            self.threshold = new_threshold
            print(f"SpeakerModel: Threshold updated to {new_threshold}")
        else:
            print(f"SpeakerModel: Invalid threshold {new_threshold}. Must be between 0.0 and 1.0")
            
    def get_profile_info(self) -> Dict[str, Any]:
        """Get information about current speaker profiles."""
        return {
            "speaker_count": len(self.profiles),
            "speakers": list(self.profiles.keys()),
            "threshold": self.threshold,
            "device": self.device,
            "embedder_loaded": self.embedder is not None
        }


# Global speaker model instance (singleton pattern)
_speaker_model: Optional[SpeakerModel] = None


def get_speaker_model(embedder=None, threshold: float = 0.70, device: str = "auto") -> SpeakerModel:
    """
    Get or create the global speaker model instance.
    
    Args:
        embedder: Pre-loaded pyannote embedding model
        threshold: Similarity threshold for speaker identification
        device: Device to run embeddings on
        
    Returns:
        SpeakerModel instance
    """
    global _speaker_model
    
    if _speaker_model is None:
        _speaker_model = SpeakerModel(embedder, threshold, device)
        
    return _speaker_model


def identify_speaker(audio_chunk: np.ndarray, pyannote_token: Optional[str] = None) -> str:
    """
    Convenience function to identify speaker using global model.
    
    Args:
        audio_chunk: Audio data as numpy array
        pyannote_token: Hugging Face token for pyannote model
        
    Returns:
        Speaker label
    """
    model = get_speaker_model()
    return model.identify(audio_chunk, pyannote_token)
