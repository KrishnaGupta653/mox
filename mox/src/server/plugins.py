"""
Plugin Manager - Extensible plugin system with sandboxing
"""

import os
import json
import importlib.util
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
import hashlib

logger = logging.getLogger('mox.plugins')


class PluginManager:
    def __init__(self):
        self.plugin_dir = Path.home() / '.local' / 'share' / 'mox' / 'plugins'
        self.plugin_dir.mkdir(parents=True, exist_ok=True)
        
        self.plugins = {}
        self.enabled_plugins = set()
        self._endpoints = {}
        self._ui_extensions = []
    
    def load_all_plugins(self):
        """Load all plugins from plugin directory"""
        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir() and (plugin_path / 'manifest.json').exists():
                try:
                    self.load_plugin(plugin_path)
                except Exception as e:
                    logger.error(f"Failed to load plugin {plugin_path}: {e}")
    
    def load_plugin(self, plugin_path: Path) -> bool:
        """Load a single plugin"""
        try:
            # Read manifest
            manifest_file = plugin_path / 'manifest.json'
            with open(manifest_file, 'r') as f:
                manifest = json.load(f)
            
            # Validate manifest
            required_fields = ['name', 'version']
            for field in required_fields:
                if field not in manifest:
                    raise ValueError(f"Missing required field: {field}")
            
            plugin_name = manifest['name']
            
            # Check permissions
            if not self._validate_permissions(manifest.get('permissions', [])):
                logger.warning(f"Plugin {plugin_name} requests denied permissions")
                return False
            
            # Load plugin module
            main_file = plugin_path / 'main.py'
            if main_file.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{plugin_name}",
                    main_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Store plugin info
                self.plugins[plugin_name] = {
                    'manifest': manifest,
                    'module': module,
                    'path': str(plugin_path),
                    'enabled': True
                }
                
                self.enabled_plugins.add(plugin_name)
                
                # Register endpoints
                self._register_endpoints(plugin_name, manifest, module)
                
                # Register UI extensions
                self._register_ui_extensions(plugin_name, manifest)
                
                logger.info(f"Loaded plugin: {plugin_name} v{manifest['version']}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to load plugin: {e}")
            return False
    
    def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            
            # Call cleanup if available
            if hasattr(plugin['module'], 'cleanup'):
                try:
                    plugin['module'].cleanup()
                except:
                    pass
            
            # Remove endpoints
            endpoints_to_remove = [
                ep for ep in self._endpoints 
                if self._endpoints[ep].get('plugin') == plugin_name
            ]
            for ep in endpoints_to_remove:
                del self._endpoints[ep]
            
            # Remove UI extensions
            self._ui_extensions = [
                ext for ext in self._ui_extensions 
                if ext.get('plugin') != plugin_name
            ]
            
            del self.plugins[plugin_name]
            self.enabled_plugins.discard(plugin_name)
            
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
        
        return False
    
    def enable_plugin(self, plugin_name: str) -> Dict:
        """Enable a plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name]['enabled'] = True
            self.enabled_plugins.add(plugin_name)
            return {'status': 'enabled', 'plugin': plugin_name}
        return {'status': 'error', 'message': 'Plugin not found'}
    
    def disable_plugin(self, plugin_name: str) -> Dict:
        """Disable a plugin"""
        if plugin_name in self.plugins:
            self.plugins[plugin_name]['enabled'] = False
            self.enabled_plugins.discard(plugin_name)
            return {'status': 'disabled', 'plugin': plugin_name}
        return {'status': 'error', 'message': 'Plugin not found'}
    
    def list_plugins(self) -> List[Dict]:
        """List all installed plugins"""
        return [
            {
                'name': p['manifest']['name'],
                'version': p['manifest']['version'],
                'description': p['manifest'].get('description', ''),
                'author': p['manifest'].get('author', 'Unknown'),
                'enabled': p['enabled'],
                'permissions': p['manifest'].get('permissions', [])
            }
            for p in self.plugins.values()
        ]
    
    def get_endpoint(self, path: str, method: str) -> Optional[Dict]:
        """Get plugin endpoint handler"""
        key = f"{method}:{path}"
        if key in self._endpoints:
            return self._endpoints[key]
        return None
    
    def get_ui_extensions(self, target: str) -> List[Dict]:
        """Get UI extensions for a target location"""
        return [
            ext for ext in self._ui_extensions 
            if ext.get('target') == target and self.plugins.get(ext.get('plugin'), {}).get('enabled', False)
        ]
    
    def _validate_permissions(self, permissions: List[str]) -> bool:
        """Validate plugin permissions"""
        allowed_permissions = {'network', 'storage', 'player_control', 'ui_extension'}
        denied_permissions = {'system', 'shell', 'unsafe_eval'}
        
        for perm in permissions:
            if perm in denied_permissions:
                return False
            if perm not in allowed_permissions and not perm.startswith('api:'):
                return False
        
        return True
    
    def _register_endpoints(self, plugin_name: str, manifest: Dict, module):
        """Register plugin endpoints"""
        endpoints = manifest.get('endpoints', [])
        
        for endpoint in endpoints:
            path = endpoint.get('path')
            method = endpoint.get('method', 'GET').upper()
            handler_name = endpoint.get('handler')
            
            if path and handler_name and hasattr(module, handler_name):
                key = f"{method}:{path}"
                self._endpoints[key] = {
                    'plugin': plugin_name,
                    'handler': getattr(module, handler_name),
                    'permissions': endpoint.get('permissions', [])
                }
    
    def _register_ui_extensions(self, plugin_name: str, manifest: Dict):
        """Register plugin UI extensions"""
        extensions = manifest.get('ui_extensions', [])
        
        for ext in extensions:
            target = ext.get('target')
            component = ext.get('component')
            
            if target and component:
                self._ui_extensions.append({
                    'plugin': plugin_name,
                    'target': target,
                    'component': component,
                    'props': ext.get('props', {})
                })
    
    def install_plugin(self, plugin_url: str) -> Dict:
        """Install a plugin from URL or file"""
        # In production, would download and verify plugin
        # For now, just return error
        return {
            'status': 'error',
            'message': 'Manual installation required. Place plugin folder in ~/.local/share/mox/plugins/'
        }
    
    def uninstall_plugin(self, plugin_name: str) -> Dict:
        """Uninstall a plugin"""
        if plugin_name in self.plugins:
            self.unload_plugin(plugin_name)
            
            # Remove from disk
            plugin_path = Path(self.plugins[plugin_name]['path'])
            if plugin_path.exists():
                import shutil
                shutil.rmtree(plugin_path)
            
            return {'status': 'uninstalled', 'plugin': plugin_name}
        
        return {'status': 'error', 'message': 'Plugin not found'}
    
    def get_plugin_info(self, plugin_name: str) -> Optional[Dict]:
        """Get detailed plugin information"""
        if plugin_name in self.plugins:
            plugin = self.plugins[plugin_name]
            return {
                **plugin['manifest'],
                'enabled': plugin['enabled'],
                'path': plugin['path']
            }
        return None
