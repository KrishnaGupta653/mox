"""
Command Handler - CLI command implementations
"""

import os
import sys
import json
import subprocess
import webbrowser
from typing import List, Dict, Optional
import logging
from pathlib import Path

logger = logging.getLogger('mox.commands')


class CommandHandler:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.server_host = "127.0.0.1"
        self.server_port = 8080
    
    def play(self, args: List[str], add_to_queue: bool = False) -> str:
        """Play a track"""
        if not args:
            return "Error: No track specified"
        
        path = args[0]
        
        # Check if file exists
        if not os.path.exists(path):
            # Try searching
            search_result = self.search(path)
            if search_result and len(search_result) > 0:
                path = search_result[0].get('path', path)
        
        return self._send_command('play', {'path': path, 'queue': add_to_queue})
    
    def pause(self) -> str:
        """Pause playback"""
        return self._send_command('pause', {})
    
    def resume(self) -> str:
        """Resume playback"""
        return self._send_command('resume', {})
    
    def stop(self) -> str:
        """Stop playback"""
        return self._send_command('stop', {})
    
    def next_track(self) -> str:
        """Skip to next track"""
        return self._send_command('next', {})
    
    def prev_track(self) -> str:
        """Go to previous track"""
        return self._send_command('prev', {})
    
    def search(self, query: str) -> List[Dict]:
        """Search for music"""
        try:
            import requests
            response = requests.get(
                f'http://{self.server_host}:{self.server_port}/api/search',
                params={'q': query},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get('results', [])
        except Exception as e:
            if self.verbose:
                print(f"Search failed: {e}")
        
        return []
    
    def show_queue(self) -> str:
        """Show current queue"""
        try:
            import requests
            response = requests.get(
                f'http://{self.server_host}:{self.server_port}/api/queue',
                timeout=5
            )
            
            if response.status_code == 200:
                queue = response.json()
                if isinstance(queue, list):
                    output = "Current Queue:\n"
                    for i, track in enumerate(queue[:20], 1):
                        title = track.get('title', 'Unknown')
                        artist = track.get('artist', 'Unknown')
                        output += f"{i}. {title} - {artist}\n"
                    
                    if len(queue) > 20:
                        output += f"... and {len(queue) - 20} more tracks\n"
                    
                    return output
        except Exception as e:
            if self.verbose:
                print(f"Failed to get queue: {e}")
        
        return "Unable to fetch queue"
    
    def launch_ui(self, host: str = "127.0.0.1", port: int = 8080) -> str:
        """Launch web UI"""
        self.server_host = host
        self.server_port = port
        
        url = f"http://{host}:{port}"
        
        # Open in browser
        try:
            webbrowser.open(url)
            return f"Opening Mox UI at {url}"
        except Exception as e:
            return f"Failed to open browser: {e}. Please visit {url} manually"
    
    def plugin_command(self, args: List[str]) -> str:
        """Plugin management commands"""
        if not args:
            return "Usage: mox plugin [list|enable|disable|install] [name]"
        
        action = args[0]
        
        try:
            import requests
            
            if action == 'list':
                response = requests.get(
                    f'http://{self.server_host}:{self.server_port}/api/plugins',
                    timeout=5
                )
                
                if response.status_code == 200:
                    plugins = response.json()
                    output = "Installed Plugins:\n"
                    for p in plugins:
                        status = "✓" if p.get('enabled') else "✗"
                        output += f"{status} {p['name']} v{p['version']} - {p.get('description', '')}\n"
                    return output
            
            elif action == 'enable' and len(args) > 1:
                name = args[1]
                response = requests.post(
                    f'http://{self.server_host}:{self.server_port}/api/plugins/{name}/enable',
                    timeout=5
                )
                return f"Plugin {name} enabled" if response.status_code == 200 else "Failed to enable"
            
            elif action == 'disable' and len(args) > 1:
                name = args[1]
                response = requests.post(
                    f'http://{self.server_host}:{self.server_port}/api/plugins/{name}/disable',
                    timeout=5
                )
                return f"Plugin {name} disabled" if response.status_code == 200 else "Failed to disable"
            
            elif action == 'install' and len(args) > 1:
                return "Manual installation required. See documentation."
            
        except Exception as e:
            if self.verbose:
                print(f"Plugin command failed: {e}")
        
        return "Plugin command failed"
    
    def share(self, args: List[str]) -> str:
        """Create share link"""
        if not args:
            return "Usage: mox share [track|queue|playlist] [id]"
        
        share_type = args[0]
        share_id = args[1] if len(args) > 1 else None
        
        try:
            import requests
            response = requests.post(
                f'http://{self.server_host}:{self.server_port}/api/share',
                json={'type': share_type, 'data': {'id': share_id}},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return f"Share link: {data.get('url', 'N/A')}"
        except Exception as e:
            if self.verbose:
                print(f"Share failed: {e}")
        
        return "Failed to create share link"
    
    def schedule(self, args: List[str]) -> str:
        """Schedule playback"""
        if not args:
            return "Usage: mox schedule [alarm|sleep] [time] [playlist]"
        
        schedule_type = args[0]
        time_str = args[1] if len(args) > 1 else "00:00"
        playlist = args[2] if len(args) > 2 else ""
        
        try:
            import requests
            response = requests.post(
                f'http://{self.server_host}:{self.server_port}/api/schedule',
                json={
                    'type': schedule_type,
                    'time': time_str,
                    'playlist': playlist
                },
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return f"Scheduled {schedule_type} for {data.get('execute_at', 'N/A')}"
        except Exception as e:
            if self.verbose:
                print(f"Schedule failed: {e}")
        
        return "Failed to schedule"
    
    def _send_command(self, command: str, data: Dict) -> str:
        """Send command to server"""
        try:
            import requests
            response = requests.post(
                f'http://{self.server_host}:{self.server_port}/api/{command}',
                json=data,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                return json.dumps(result, indent=2)
            else:
                return f"Command failed with status {response.status_code}"
                
        except Exception as e:
            return f"Failed to send command: {e}"
