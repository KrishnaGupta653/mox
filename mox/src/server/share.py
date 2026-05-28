"""
Share Link Manager - Creates shareable links with QR codes
"""

import os
import json
import time
import secrets
from typing import Optional, Dict, List
from pathlib import Path
import logging
from datetime import datetime

logger = logging.getLogger('mox.share')


class ShareManager:
    def __init__(self):
        self.data_dir = Path.home() / '.local' / 'share' / 'mox' / 'shares'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # In production, would use Redis or database
        self.links = {}
    
    def create_link(self, share_type: str, data: Dict) -> Dict:
        """Create a shareable link"""
        link_id = secrets.token_urlsafe(8)
        
        share_data = {
            'id': link_id,
            'type': share_type,  # 'track', 'queue', 'playlist'
            'data': data,
            'created_at': datetime.now().isoformat(),
            'expires_at': None,  # Never expires by default
            'views': 0,
            'active': True
        }
        
        # Save to disk
        self._save_share(link_id, share_data)
        self.links[link_id] = share_data
        
        # Generate short URL (in production would use domain)
        short_url = f"https://mox.music/s/{link_id}"
        
        return {
            'id': link_id,
            'url': short_url,
            'qr_code_url': f'/api/share/{link_id}/qr',
            'expires_at': None,
            'created_at': share_data['created_at']
        }
    
    def resolve_link(self, link_id: str) -> Optional[Dict]:
        """Resolve share link and return data"""
        share_data = self._load_share(link_id)
        
        if not share_data:
            return None
        
        if not share_data.get('active', True):
            return None
        
        # Check expiration
        expires_at = share_data.get('expires_at')
        if expires_at:
            if datetime.fromisoformat(expires_at) < datetime.now():
                return None
        
        # Increment view count
        share_data['views'] = share_data.get('views', 0) + 1
        self._save_share(link_id, share_data)
        
        return {
            'type': share_data['type'],
            'data': share_data['data'],
            'created_at': share_data['created_at'],
            'views': share_data['views']
        }
    
    def generate_qr(self, link_id: str) -> bytes:
        """Generate QR code for share link"""
        try:
            import qrcode
            
            url = f"https://mox.music/s/{link_id}"
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            from io import BytesIO
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            return buffer.getvalue()
            
        except Exception as e:
            logger.error(f"QR generation failed: {e}")
            return b''
    
    def delete_link(self, link_id: str) -> bool:
        """Delete a share link"""
        share_file = self.data_dir / f"{link_id}.json"
        
        if share_file.exists():
            share_file.unlink()
            if link_id in self.links:
                del self.links[link_id]
            return True
        
        return False
    
    def list_links(self, limit: int = 50) -> List[Dict]:
        """List all active share links"""
        links = []
        
        for share_file in self.data_dir.glob("*.json"):
            try:
                with open(share_file, 'r') as f:
                    data = json.load(f)
                    if data.get('active', True):
                        links.append({
                            'id': data['id'],
                            'type': data['type'],
                            'created_at': data['created_at'],
                            'views': data.get('views', 0)
                        })
            except:
                continue
            
            if len(links) >= limit:
                break
        
        return sorted(links, key=lambda x: x['created_at'], reverse=True)
    
    def _save_share(self, link_id: str, data: Dict):
        """Save share data to disk"""
        share_file = self.data_dir / f"{link_id}.json"
        
        try:
            with open(share_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save share: {e}")
    
    def _load_share(self, link_id: str) -> Optional[Dict]:
        """Load share data from disk"""
        share_file = self.data_dir / f"{link_id}.json"
        
        if not share_file.exists():
            return None
        
        try:
            with open(share_file, 'r') as f:
                return json.load(f)
        except:
            return None
