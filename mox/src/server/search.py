"""
Search Engine - Multi-source music search (local, YouTube, SoundCloud)
"""

import os
import json
import asyncio
import subprocess
import requests
from typing import List, Dict, Optional
from pathlib import Path
import logging
from urllib.parse import quote

logger = logging.getLogger('mox.search')


class SearchEngine:
    def __init__(self):
        self.local_dirs = [
            os.path.expanduser("~/Music"),
            os.path.expanduser("~/Downloads")
        ]
        self.supported_formats = ['.mp3', '.flac', '.wav', '.m4a', '.ogg', '.webm']
    
    async def search(self, query: str) -> List[Dict]:
        """Search all sources concurrently"""
        tasks = [
            self.search_local(query),
            self.search_youtube(query),
            self.search_soundcloud(query)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Merge and format results
        merged = []
        for result in results:
            if isinstance(result, list):
                merged.extend(result)
        
        return merged[:50]  # Limit total results
    
    async def search_source(self, source: str, query: str) -> List[Dict]:
        """Search specific source"""
        if source == 'local':
            return await self.search_local(query)
        elif source == 'youtube':
            return await self.search_youtube(query)
        elif source == 'soundcloud':
            return await self.search_soundcloud(query)
        else:
            return []
    
    async def search_local(self, query: str) -> List[Dict]:
        """Search local music library"""
        results = []
        query_lower = query.lower()
        
        for base_dir in self.local_dirs:
            if not os.path.exists(base_dir):
                continue
            
            try:
                for root, dirs, files in os.walk(base_dir):
                    for file in files:
                        if any(file.endswith(ext) for ext in self.supported_formats):
                            if query_lower in file.lower():
                                path = os.path.join(root, file)
                                results.append({
                                    'id': f'local:{path}',
                                    'type': 'local',
                                    'title': file,
                                    'artist': 'Unknown',
                                    'duration': self._get_duration(path),
                                    'path': path,
                                    'thumbnail': None
                                })
                                
                                if len(results) >= 20:
                                    return results
            except Exception as e:
                logger.error(f"Local search error: {e}")
        
        return results
    
    async def search_youtube(self, query: str) -> List[Dict]:
        """Search YouTube using yt-dlp"""
        try:
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--no-warnings',
                f'ytsearch10:{query}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            results = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        results.append({
                            'id': f'youtube:{data.get("id", "")}',
                            'type': 'youtube',
                            'title': data.get('title', 'Unknown'),
                            'artist': data.get('uploader', 'Unknown'),
                            'duration': data.get('duration', 0),
                            'url': f'https://www.youtube.com/watch?v={data.get("id", "")}',
                            'thumbnail': data.get('thumbnail', '')
                        })
                    except json.JSONDecodeError:
                        continue
            
            return results
        except Exception as e:
            logger.error(f"YouTube search error: {e}")
            return []
    
    async def search_soundcloud(self, query: str) -> List[Dict]:
        """Search SoundCloud using yt-dlp"""
        try:
            cmd = [
                'yt-dlp',
                '--flat-playlist',
                '--dump-json',
                '--no-warnings',
                f'scsearch10:{query}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            results = []
            for line in result.stdout.strip().split('\n'):
                if line:
                    try:
                        data = json.loads(line)
                        results.append({
                            'id': f'soundcloud:{data.get("id", "")}',
                            'type': 'soundcloud',
                            'title': data.get('title', 'Unknown'),
                            'artist': data.get('uploader', 'Unknown'),
                            'duration': data.get('duration', 0),
                            'url': data.get('url', ''),
                            'thumbnail': data.get('thumbnail', '')
                        })
                    except json.JSONDecodeError:
                        continue
            
            return results
        except Exception as e:
            logger.error(f"SoundCloud search error: {e}")
            return []
    
    async def fetch_lyrics(self, artist: str, title: str) -> Optional[Dict]:
        """Fetch lyrics from lrclib.net"""
        try:
            url = f"https://lrclib.net/api/get?artist_name={quote(artist)}&track_name={quote(title)}"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'synced': data.get('syncedLyrics'),
                    'plain': data.get('plainLyrics'),
                    'source': 'lrclib'
                }
        except Exception as e:
            logger.error(f"Lyrics fetch error: {e}")
        
        return None
    
    def _get_duration(self, path: str) -> int:
        """Get duration of audio file using ffprobe or mutagen"""
        try:
            import mutagen
            audio = mutagen.File(path)
            if audio:
                return int(audio.info.length)
        except:
            pass
        
        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path],
                capture_output=True,
                text=True
            )
            data = json.loads(result.stdout)
            return int(float(data['format']['duration']))
        except:
            pass
        
        return 0
