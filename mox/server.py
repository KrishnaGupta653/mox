"""
Mox Music System - Modern FastAPI Server
Main server entry point with security, performance, and extensibility
"""

import os
import sys
import logging
import uvicorn
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.gzip import GZipMiddleware
import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Optional, List
import secrets
import hashlib

# Import components
from src.server.player import PlayerManager
from src.server.search import SearchEngine
from src.server.queue import SmartQueue
from src.server.scheduler import PlaybackScheduler
from src.server.plugins import PluginManager
from src.server.auth import AuthManager, get_current_user
from src.server.share import ShareManager
from src.server.waveform import WaveformGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/mox_server.log')
    ]
)
logger = logging.getLogger('mox.server')


class MoxServer:
    def __init__(self, host: str = "127.0.0.1", port: int = 8080, pin: Optional[str] = None):
        self.host = host
        self.port = port
        self.pin = pin or os.environ.get('MOX_PIN', '000000')
        
        # Initialize FastAPI app
        self.app = FastAPI(
            title="Mox Music Server",
            description="Modern music player backend",
            version="2.0.0"
        )
        
        # Add middleware
        self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[f"http://{host}:{port}"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        # Initialize managers
        self.player = PlayerManager()
        self.search_engine = SearchEngine()
        self.queue_manager = SmartQueue()
        self.scheduler = PlaybackScheduler()
        self.plugin_manager = PluginManager()
        self.auth_manager = AuthManager(self.pin)
        self.share_manager = ShareManager()
        self.waveform_gen = WaveformGenerator()
        
        # Security
        self.security = HTTPBearer(auto_error=False)
        
        # Rate limiting storage
        self.rate_limit_store = {}
        
        # Setup routes
        self.setup_routes()
        
        # Load plugins
        self.plugin_manager.load_all_plugins()
    
    def setup_routes(self):
        """Setup all API routes"""
        
        @self.app.get("/")
        async def root():
            """Serve main UI"""
            return FileResponse('src/ui/index.html')
        
        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "version": "2.0.0"
            }
        
        @self.app.post("/api/auth")
        async def authenticate(request: Request):
            """Authenticate user with PIN"""
            data = await request.json()
            pin = data.get('pin', '')
            
            # Rate limiting
            client_ip = request.client.host
            if not self.auth_manager.check_rate_limit(client_ip):
                raise HTTPException(status_code=429, detail="Too many attempts")
            
            token = self.auth_manager.authenticate(pin)
            if not token:
                self.auth_manager.record_failed_attempt(client_ip)
                raise HTTPException(status_code=401, detail="Invalid PIN")
            
            return {"token": token, "expires_in": 86400}
        
        @self.app.get("/api/state")
        async def get_state(current_user: dict = Depends(get_current_user)):
            """Get current player state"""
            state = self.player.get_state()
            state['queue'] = self.queue_manager.get_queue()
            state['waveform'] = self.waveform_gen.get_waveform_url(state.get('current_track'))
            return state
        
        @self.app.websocket("/ws/state")
        async def websocket_state(websocket):
            """WebSocket for real-time state updates"""
            await websocket.accept()
            try:
                while True:
                    state = self.player.get_state()
                    await websocket.send_json(state)
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
        
        @self.app.post("/api/play")
        async def play_track(request: Request, current_user: dict = Depends(get_current_user)):
            """Play a track"""
            data = await request.json()
            path = data.get('path')
            if not path:
                raise HTTPException(status_code=400, detail="Path required")
            
            result = self.player.play(path)
            return result
        
        @self.app.post("/api/pause")
        async def pause(current_user: dict = Depends(get_current_user)):
            """Pause playback"""
            return self.player.pause()
        
        @self.app.post("/api/resume")
        async def resume(current_user: dict = Depends(get_current_user)):
            """Resume playback"""
            return self.player.resume()
        
        @self.app.post("/api/next")
        async def next_track(current_user: dict = Depends(get_current_user)):
            """Skip to next track"""
            return self.player.next_track()
        
        @self.app.post("/api/prev")
        async def prev_track(current_user: dict = Depends(get_current_user)):
            """Go to previous track"""
            return self.player.prev_track()
        
        @self.app.post("/api/seek")
        async def seek(request: Request, current_user: dict = Depends(get_current_user)):
            """Seek to position"""
            data = await request.json()
            position = data.get('position')
            if position is None:
                raise HTTPException(status_code=400, detail="Position required")
            
            return self.player.seek(position)
        
        @self.app.post("/api/volume")
        async def set_volume(request: Request, current_user: dict = Depends(get_current_user)):
            """Set volume"""
            data = await request.json()
            volume = data.get('volume')
            if volume is None or not 0 <= volume <= 100:
                raise HTTPException(status_code=400, detail="Volume must be 0-100")
            
            return self.player.set_volume(volume)
        
        @self.app.get("/api/search")
        async def search(q: str, current_user: dict = Depends(get_current_user)):
            """Search for music"""
            results = await self.search_engine.search(q)
            return {"query": q, "results": results}
        
        @self.app.get("/api/search/{source}")
        async def search_source(source: str, q: str, current_user: dict = Depends(get_current_user)):
            """Search specific source"""
            results = await self.search_engine.search_source(source, q)
            return {"source": source, "query": q, "results": results}
        
        @self.app.get("/api/queue")
        async def get_queue(current_user: dict = Depends(get_current_user)):
            """Get current queue"""
            return self.queue_manager.get_queue()
        
        @self.app.post("/api/queue")
        async def add_to_queue(request: Request, current_user: dict = Depends(get_current_user)):
            """Add track to queue"""
            data = await request.json()
            tracks = data.get('tracks', [])
            position = data.get('position')
            
            return self.queue_manager.add_tracks(tracks, position)
        
        @self.app.delete("/api/queue/{index}")
        async def remove_from_queue(index: int, current_user: dict = Depends(get_current_user)):
            """Remove track from queue"""
            return self.queue_manager.remove_track(index)
        
        @self.app.put("/api/queue/reorder")
        async def reorder_queue(request: Request, current_user: dict = Depends(get_current_user)):
            """Reorder queue"""
            data = await request.json()
            from_idx = data.get('from')
            to_idx = data.get('to')
            
            return self.queue_manager.reorder(from_idx, to_idx)
        
        @self.app.post("/api/queue/smart")
        async def generate_smart_queue(request: Request, current_user: dict = Depends(get_current_user)):
            """Generate smart queue based on preferences"""
            data = await request.json()
            seed_track = data.get('seed_track')
            count = data.get('count', 20)
            
            queue = self.queue_manager.generate_smart_queue(seed_track, count)
            return {"queue": queue}
        
        @self.app.get("/api/waveform/{track_id}")
        async def get_waveform(track_id: str, current_user: dict = Depends(get_current_user)):
            """Get waveform data for track"""
            waveform = await self.waveform_gen.generate_waveform(track_id)
            return waveform
        
        @self.app.post("/api/share")
        async def create_share_link(request: Request, current_user: dict = Depends(get_current_user)):
            """Create shareable link"""
            data = await request.json()
            share_type = data.get('type')  # 'track', 'queue', 'playlist'
            share_data = data.get('data')
            
            link = self.share_manager.create_link(share_type, share_data)
            return link
        
        @self.app.get("/api/share/{link_id}")
        async def resolve_share_link(link_id: str):
            """Resolve share link"""
            data = self.share_manager.resolve_link(link_id)
            if not data:
                raise HTTPException(status_code=404, detail="Link not found")
            
            return data
        
        @self.app.get("/api/share/{link_id}/qr")
        async def get_qr_code(link_id: str):
            """Get QR code for share link"""
            qr_image = self.share_manager.generate_qr(link_id)
            return Response(content=qr_image, media_type="image/png")
        
        @self.app.post("/api/schedule")
        async def create_schedule(request: Request, current_user: dict = Depends(get_current_user)):
            """Create scheduled playback"""
            data = await request.json()
            schedule_type = data.get('type')  # 'alarm', 'sleep', 'reminder'
            time_str = data.get('time')
            playlist = data.get('playlist')
            days = data.get('days')
            
            schedule = self.scheduler.add_schedule(
                schedule_type, time_str, playlist, days
            )
            return schedule
        
        @self.app.get("/api/schedule")
        async def get_schedules(current_user: dict = Depends(get_current_user)):
            """Get all schedules"""
            return self.scheduler.get_schedules()
        
        @self.app.delete("/api/schedule/{schedule_id}")
        async def delete_schedule(schedule_id: str, current_user: dict = Depends(get_current_user)):
            """Delete schedule"""
            return self.scheduler.delete_schedule(schedule_id)
        
        @self.app.get("/api/plugins")
        async def list_plugins(current_user: dict = Depends(get_current_user)):
            """List installed plugins"""
            return self.plugin_manager.list_plugins()
        
        @self.app.post("/api/plugins/{plugin_name}/enable")
        async def enable_plugin(plugin_name: str, current_user: dict = Depends(get_current_user)):
            """Enable plugin"""
            return self.plugin_manager.enable_plugin(plugin_name)
        
        @self.app.post("/api/plugins/{plugin_name}/disable")
        async def disable_plugin(plugin_name: str, current_user: dict = Depends(get_current_user)):
            """Disable plugin"""
            return self.plugin_manager.disable_plugin(plugin_name)
        
        @self.app.get("/api/lyrics")
        async def get_lyrics(artist: str, title: str, current_user: dict = Depends(get_current_user)):
            """Get lyrics for track"""
            lyrics = await self.search_engine.fetch_lyrics(artist, title)
            return lyrics
        
        @self.app.get("/api/history")
        async def get_history(limit: int = 50, current_user: dict = Depends(get_current_user)):
            """Get playback history"""
            return self.player.get_history(limit)
        
        @self.app.post("/api/like")
        async def like_track(request: Request, current_user: dict = Depends(get_current_user)):
            """Like current track"""
            data = await request.json()
            track_id = data.get('track_id')
            return self.player.like_track(track_id)
        
        @self.app.get("/api/favorites")
        async def get_favorites(current_user: dict = Depends(get_current_user)):
            """Get favorite tracks"""
            return self.player.get_favorites()
        
        @self.app.get("/api/stats")
        async def get_stats(current_user: dict = Depends(get_current_user)):
            """Get playback statistics"""
            return self.player.get_stats()
    
    def run(self):
        """Start the server"""
        logger.info(f"Starting Mox server on {self.host}:{self.port}")
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Mox Music Server")
    parser.add_argument("--host", default="127.0.0.1", help="Server host")
    parser.add_argument("--port", type=int, default=8080, help="Server port")
    parser.add_argument("--pin", help="Authentication PIN")
    
    args = parser.parse_args()
    
    server = MoxServer(host=args.host, port=args.port, pin=args.pin)
    server.run()


if __name__ == "__main__":
    main()
