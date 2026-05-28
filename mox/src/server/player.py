"""
Player Manager - Controls mpv media player with IPC
"""

import os
import json
import socket
import threading
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List, Any
import logging
import time

logger = logging.getLogger('mox.player')


class PlayerManager:
    def __init__(self):
        self.mpv_process = None
        self.socket_path = None
        self.socket = None
        self.current_track = None
        self.queue = []
        self.history = []
        self.favorites = set()
        self.is_playing = False
        self.volume = 80
        self._lock = threading.Lock()
        
        # Start mpv
        self._start_mpv()
    
    def _start_mpv(self):
        """Start mpv with IPC socket"""
        self.socket_path = tempfile.mktemp(suffix='.sock')
        
        cmd = [
            'mpv',
            '--idle',
            '--no-terminal',
            '--input-ipc-server=' + self.socket_path,
            '--force-window=no'
        ]
        
        try:
            self.mpv_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Wait for socket to be created
            for _ in range(50):
                if os.path.exists(self.socket_path):
                    break
                time.sleep(0.1)
            
            self._connect_socket()
            logger.info("MPV started successfully")
        except Exception as e:
            logger.error(f"Failed to start MPV: {e}")
            raise
    
    def _connect_socket(self):
        """Connect to mpv IPC socket"""
        try:
            self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.socket.connect(self.socket_path)
        except Exception as e:
            logger.error(f"Failed to connect to MPV socket: {e}")
            raise
    
    def _send_command(self, command: List[Any]) -> Optional[Dict]:
        """Send command to mpv via IPC"""
        if not self.socket:
            return None
        
        try:
            message = json.dumps(command) + '\n'
            self.socket.sendall(message.encode())
            
            # Read response
            response = b''
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                response += chunk
                if b'\n' in response:
                    break
            
            if response:
                return json.loads(response.decode().strip())
        except Exception as e:
            logger.error(f"IPC command failed: {e}")
        
        return None
    
    def play(self, path: str, add_to_queue: bool = False) -> Dict:
        """Play a track"""
        with self._lock:
            try:
                if add_to_queue:
                    self._send_command(['loadfile', path, 'append'])
                    return {"status": "added_to_queue", "path": path}
                else:
                    self._send_command(['loadfile', path])
                    self.current_track = path
                    self.is_playing = True
                    self.history.append({
                        'track': path,
                        'played_at': time.time()
                    })
                    return {"status": "playing", "path": path}
            except Exception as e:
                logger.error(f"Play failed: {e}")
                return {"status": "error", "message": str(e)}
    
    def pause(self) -> Dict:
        """Pause playback"""
        self._send_command(['set', 'pause', True])
        self.is_playing = False
        return {"status": "paused"}
    
    def resume(self) -> Dict:
        """Resume playback"""
        self._send_command(['set', 'pause', False])
        self.is_playing = True
        return {"status": "resumed"}
    
    def stop(self) -> Dict:
        """Stop playback"""
        self._send_command(['stop'])
        self.is_playing = False
        self.current_track = None
        return {"status": "stopped"}
    
    def next_track(self) -> Dict:
        """Skip to next track"""
        self._send_command(['playlist-next'])
        return {"status": "next"}
    
    def prev_track(self) -> Dict:
        """Go to previous track"""
        self._send_command(['playlist-prev'])
        return {"status": "prev"}
    
    def seek(self, position: float) -> Dict:
        """Seek to position (in seconds)"""
        self._send_command(['seek', position, 'absolute'])
        return {"status": "seeked", "position": position}
    
    def set_volume(self, volume: int) -> Dict:
        """Set volume (0-100)"""
        self.volume = max(0, min(100, volume))
        self._send_command(['set', 'volume', self.volume])
        return {"status": "volume_set", "volume": self.volume}
    
    def get_state(self) -> Dict:
        """Get current player state"""
        try:
            # Get various properties
            duration = self._send_command(['get_property', 'duration'])
            time_pos = self._send_command(['get_property', 'time-pos'])
            pause = self._send_command(['get_property', 'pause'])
            volume = self._send_command(['get_property', 'volume'])
            path = self._send_command(['get_property', 'path'])
            
            return {
                'is_playing': not pause.get('data', True) if pause else False,
                'current_track': path.get('data') if path else None,
                'duration': duration.get('data') if duration else 0,
                'position': time_pos.get('data') if time_pos else 0,
                'volume': volume.get('data', self.volume) if volume else self.volume,
                'queue_length': len(self.queue),
                'history_count': len(self.history)
            }
        except Exception as e:
            logger.error(f"Get state failed: {e}")
            return {
                'is_playing': False,
                'current_track': None,
                'duration': 0,
                'position': 0,
                'volume': self.volume,
                'error': str(e)
            }
    
    def get_history(self, limit: int = 50) -> List[Dict]:
        """Get playback history"""
        return self.history[-limit:]
    
    def like_track(self, track_id: str) -> Dict:
        """Like a track"""
        self.favorites.add(track_id)
        return {"status": "liked", "track_id": track_id}
    
    def get_favorites(self) -> List[str]:
        """Get favorite tracks"""
        return list(self.favorites)
    
    def get_stats(self) -> Dict:
        """Get playback statistics"""
        return {
            'total_tracks_played': len(self.history),
            'favorites_count': len(self.favorites),
            'queue_length': len(self.queue),
            'uptime': time.time() - (self.mpv_process.create_time() if self.mpv_process else time.time())
        }
    
    def cleanup(self):
        """Cleanup resources"""
        if self.socket:
            self.socket.close()
        if self.mpv_process:
            self.mpv_process.terminate()
        if self.socket_path and os.path.exists(self.socket_path):
            os.unlink(self.socket_path)
