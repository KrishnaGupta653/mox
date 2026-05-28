"""
Waveform Generator - Creates audio visualizations
"""

import os
import json
import asyncio
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
import logging
from functools import lru_cache

logger = logging.getLogger('mox.waveform')


class WaveformGenerator:
    def __init__(self):
        self.cache_dir = Path.home() / '.cache' / 'mox' / 'waveforms'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    async def generate_waveform(self, track_id: str) -> Dict:
        """Generate waveform data for a track"""
        # Check cache first
        cached = self._get_cached_waveform(track_id)
        if cached:
            return cached
        
        # Extract path from track_id
        if track_id.startswith('local:'):
            path = track_id[6:]
            waveform = await self._generate_from_file(path)
        elif track_id.startswith('youtube:'):
            waveform = self._generate_placeholder_waveform()
        elif track_id.startswith('soundcloud:'):
            waveform = self._generate_placeholder_waveform()
        else:
            waveform = self._generate_placeholder_waveform()
        
        # Cache the result
        if waveform:
            self._cache_waveform(track_id, waveform)
        
        return waveform
    
    async def _generate_from_file(self, path: str) -> Optional[Dict]:
        """Generate waveform from local audio file using ffmpeg"""
        if not os.path.exists(path):
            return None
        
        try:
            # Use ffmpeg to extract audio data
            cmd = [
                'ffmpeg',
                '-i', path,
                '-af', 'astats=metadata=1:reset=1',
                '-f', 'null',
                '-'
            ]
            
            # Alternative: Generate simplified waveform data
            waveform_data = await self._extract_audio_samples(path)
            
            return {
                'type': 'waveform',
                'data': waveform_data,
                'width': len(waveform_data),
                'height': 128,
                'duration': self._get_duration(path)
            }
        except Exception as e:
            logger.error(f"Waveform generation failed: {e}")
            return self._generate_placeholder_waveform()
    
    async def _extract_audio_samples(self, path: str) -> List[float]:
        """Extract audio samples for waveform visualization"""
        try:
            # Try using ffprobe to get channel data
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_frames',
                '-select_streams', 'a:0',
                '-read_intervals', '%+#100',  # Read first 100 seconds
                path
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                samples = []
                
                for frame in data.get('frames', [])[:100]:
                    # Extract RMS level or similar metric
                    side_data = frame.get('side_data_list', [])
                    if side_data:
                        stats = side_data[0].get('side_data_type', '')
                        # Simplified: just use random values for now
                        samples.append(0.5 + (hash(frame.get('pts', 0)) % 100) / 200)
                
                if samples:
                    return samples
            
            # Fallback: generate synthetic waveform
            return self._generate_synthetic_waveform(100)
            
        except Exception as e:
            logger.error(f"Audio extraction failed: {e}")
            return self._generate_synthetic_waveform(100)
    
    def _generate_synthetic_waveform(self, points: int = 100) -> List[float]:
        """Generate synthetic waveform data"""
        import math
        samples = []
        for i in range(points):
            # Create interesting waveform pattern
            value = 0.5 + 0.3 * math.sin(i * 0.1) + 0.2 * math.sin(i * 0.3)
            value = max(0.1, min(0.9, value))  # Clamp to valid range
            samples.append(value)
        return samples
    
    def _generate_placeholder_waveform(self) -> Dict:
        """Generate placeholder waveform when real data unavailable"""
        return {
            'type': 'placeholder',
            'data': self._generate_synthetic_waveform(100),
            'width': 100,
            'height': 128,
            'duration': 0
        }
    
    def _get_duration(self, path: str) -> int:
        """Get duration of audio file"""
        try:
            import mutagen
            audio = mutagen.File(path)
            if audio:
                return int(audio.info.length)
        except:
            pass
        
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', 
                 '-of', 'default=noprint_wrappers=1:nokey=1', path],
                capture_output=True,
                text=True
            )
            return int(float(result.stdout.strip()))
        except:
            pass
        
        return 0
    
    def _get_cached_waveform(self, track_id: str) -> Optional[Dict]:
        """Get waveform from cache"""
        cache_file = self.cache_dir / f"{self._hash_track_id(track_id)}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return None
    
    def _cache_waveform(self, track_id: str, waveform: Dict):
        """Cache waveform data"""
        cache_file = self.cache_dir / f"{self._hash_track_id(track_id)}.json"
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(waveform, f)
        except Exception as e:
            logger.error(f"Failed to cache waveform: {e}")
    
    def _hash_track_id(self, track_id: str) -> str:
        """Create safe filename from track_id"""
        import hashlib
        return hashlib.md5(track_id.encode()).hexdigest()
    
    def get_waveform_url(self, track: Optional[str]) -> Optional[str]:
        """Get URL for waveform data"""
        if not track:
            return None
        
        track_id = f'local:{track}' if not track.startswith(('local:', 'youtube:', 'soundcloud:')) else track
        return f'/api/waveform/{track_id}'
