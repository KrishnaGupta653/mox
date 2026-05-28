"""
Smart Queue Manager with AI-powered recommendations
"""

import random
import time
import json
from typing import List, Dict, Optional
from collections import defaultdict
import logging
import hashlib

logger = logging.getLogger('mox.queue')


class SmartQueue:
    def __init__(self):
        self.queue = []
        self.history = []
        self.preferences = defaultdict(float)
        self._lock = None
        
        try:
            from threading import Lock
            self._lock = Lock()
        except:
            pass
    
    def get_queue(self) -> List[Dict]:
        """Get current queue"""
        return self.queue
    
    def add_tracks(self, tracks: List[Dict], position: Optional[int] = None) -> Dict:
        """Add tracks to queue"""
        if self._lock:
            with self._lock:
                return self._add_tracks_impl(tracks, position)
        return self._add_tracks_impl(tracks, position)
    
    def _add_tracks_impl(self, tracks: List[Dict], position: Optional[int] = None) -> Dict:
        """Internal implementation for adding tracks"""
        if position is None:
            self.queue.extend(tracks)
        else:
            for i, track in enumerate(tracks):
                self.queue.insert(position + i, track)
        
        return {
            "status": "added",
            "count": len(tracks),
            "queue_length": len(self.queue)
        }
    
    def remove_track(self, index: int) -> Dict:
        """Remove track from queue"""
        if 0 <= index < len(self.queue):
            removed = self.queue.pop(index)
            return {
                "status": "removed",
                "track": removed
            }
        return {"status": "error", "message": "Invalid index"}
    
    def reorder(self, from_idx: int, to_idx: int) -> Dict:
        """Reorder queue items"""
        if 0 <= from_idx < len(self.queue) and 0 <= to_idx < len(self.queue):
            item = self.queue.pop(from_idx)
            self.queue.insert(to_idx, item)
            return {
                "status": "reordered",
                "from": from_idx,
                "to": to_idx
            }
        return {"status": "error", "message": "Invalid indices"}
    
    def clear_queue(self) -> Dict:
        """Clear the queue"""
        self.queue = []
        return {"status": "cleared"}
    
    def generate_smart_queue(self, seed_track: Optional[Dict] = None, count: int = 20) -> List[Dict]:
        """Generate smart queue based on preferences and seed track"""
        if not seed_track:
            # Generate based on listening history
            return self._generate_from_history(count)
        
        # Generate based on seed track similarity
        return self._generate_from_seed(seed_track, count)
    
    def _generate_from_history(self, count: int) -> List[Dict]:
        """Generate queue from listening history"""
        # Analyze preferences from history
        preferred_genres = self._get_preferred_genres()
        preferred_artists = self._get_preferred_artists()
        
        # For now, return placeholder - in production would query music database
        queue = []
        for i in range(count):
            queue.append({
                'id': f'smart_{i}',
                'title': f'Recommended Track {i+1}',
                'artist': 'Various Artists',
                'duration': 180 + random.randint(0, 120),
                'source': 'recommendation'
            })
        
        return queue
    
    def _generate_from_seed(self, seed_track: Dict, count: int) -> List[Dict]:
        """Generate queue similar to seed track"""
        # Calculate similarity scores
        candidates = self._get_candidates(seed_track)
        scored = [(track, self._score_track(track, seed_track)) for track in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)
        
        return [track for track, score in scored[:count]]
    
    def _get_candidates(self, seed_track: Dict) -> List[Dict]:
        """Get candidate tracks for recommendation"""
        # Placeholder - would query music database in production
        candidates = []
        for i in range(50):
            candidates.append({
                'id': f'candidate_{i}',
                'title': f'Candidate Track {i+1}',
                'artist': 'Artist Name',
                'genre': seed_track.get('genre', 'Unknown'),
                'bpm': 120 + random.randint(-20, 20),
                'key': random.choice(['C', 'D', 'E', 'F', 'G', 'A', 'B']),
                'duration': 180 + random.randint(0, 120)
            })
        return candidates
    
    def _score_track(self, track: Dict, seed: Dict) -> float:
        """Score track based on multiple factors"""
        score = 0.0
        
        # Genre match (30%)
        if track.get('genre') == seed.get('genre'):
            score += 0.3
        
        # BPM similarity (20%)
        bpm_diff = abs(track.get('bpm', 120) - seed.get('bpm', 120))
        score += max(0, 0.2 - (bpm_diff / 100))
        
        # Key compatibility (15%)
        if track.get('key') == seed.get('key'):
            score += 0.15
        
        # User preference (25%)
        score += self._user_preference_score(track) * 0.25
        
        # Novelty bonus (10%)
        score += self._novelty_bonus(track) * 0.1
        
        return score
    
    def _get_preferred_genres(self) -> List[str]:
        """Get user's preferred genres from history"""
        # Placeholder implementation
        return ['Pop', 'Rock', 'Electronic']
    
    def _get_preferred_artists(self) -> List[str]:
        """Get user's preferred artists from history"""
        # Placeholder implementation
        return []
    
    def _user_preference_score(self, track: Dict) -> float:
        """Calculate user preference score for track"""
        # Based on listening history, likes, skips
        return 0.5  # Neutral default
    
    def _novelty_bonus(self, track: Dict) -> float:
        """Give bonus to tracks not recently played"""
        # Prevent repetition
        track_id = track.get('id', '')
        recent_ids = [h.get('id') for h in self.history[-20:]]
        
        if track_id in recent_ids:
            return 0.0
        return 1.0
    
    def save_queue(self, name: str) -> Dict:
        """Save queue as playlist"""
        playlist = {
            'name': name,
            'tracks': self.queue.copy(),
            'created_at': time.time()
        }
        
        # In production, would save to database
        return {
            "status": "saved",
            "name": name,
            "track_count": len(self.queue)
        }
    
    def load_queue(self, name: str) -> Dict:
        """Load queue from saved playlist"""
        # In production, would load from database
        return {
            "status": "error",
            "message": "Playlist not found"
        }
