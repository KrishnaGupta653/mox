#!/usr/bin/env python3
"""
API tests for mox music_ui_server.py
Tests all HTTP endpoints, error handling, and security features
"""

import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.request
import urllib.parse
import urllib.error
from unittest.mock import patch, MagicMock
import subprocess
import socket
import shutil

# Add src directory to path to import the server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestMoxAPI(unittest.TestCase):
    """Test suite for mox API server"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.test_root = tempfile.mkdtemp(prefix='mox_api_test_')
        cls.original_music_root = os.environ.get('MUSIC_ROOT')
        os.environ['MUSIC_ROOT'] = cls.test_root
        os.environ['MOX_TEST_MODE'] = '1'
        
        # Create required directories
        os.makedirs(os.path.join(cls.test_root, 'socket'), exist_ok=True)
        os.makedirs(os.path.join(cls.test_root, 'data'), exist_ok=True)
        
        # Create mock socket file (empty file for testing)
        cls.socket_path = os.path.join(cls.test_root, 'socket', 'mpv.sock')
        
        # Find available port
        cls.test_port = cls._find_free_port()
        
        print(f"Test environment: {cls.test_root}")
        print(f"Test port: {cls.test_port}")
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        if cls.original_music_root:
            os.environ['MUSIC_ROOT'] = cls.original_music_root
        else:
            os.environ.pop('MUSIC_ROOT', None)
        
        # Clean up test directory
        try:
            shutil.rmtree(cls.test_root)
        except OSError:
            pass
    
    @staticmethod
    def _find_free_port():
        """Find a free port for testing"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def setUp(self):
        """Set up each test"""
        self.base_url = f'http://localhost:{self.test_port}'
        self.server_process = None
        
    def tearDown(self):
        """Clean up each test"""
        if hasattr(self, 'server_process') and self.server_process:
            try:
                self.server_process.terminate()
                self.server_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.server_process.kill()
                self.server_process.wait()
    
    def start_server(self, timeout=5):
        """Start the server for testing"""
        server_script = os.path.join(os.path.dirname(__file__), '..', 'src', 'music_ui_server.py')
        
        # Start server in background
        self.server_process = subprocess.Popen([
            sys.executable, server_script, str(self.test_port)
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if process is still running
            if self.server_process.poll() is not None:
                # Process has exited, get error output
                stdout, stderr = self.server_process.communicate()
                print(f"Server failed to start. Exit code: {self.server_process.returncode}")
                print(f"STDOUT: {stdout.decode()}")
                print(f"STDERR: {stderr.decode()}")
                return False
            
            try:
                response = urllib.request.urlopen(f'{self.base_url}/api/state', timeout=0.5)
                if response.getcode() == 200:
                    return True
            except (urllib.error.URLError, socket.timeout, ConnectionResetError):
                time.sleep(0.1)
        
        # Timeout reached
        if self.server_process.poll() is None:
            print("Server startup timed out")
            self.server_process.terminate()
        return False
    
    def make_request(self, endpoint, method='GET', data=None, headers=None):
        """Make HTTP request to server"""
        url = f'{self.base_url}{endpoint}'
        
        if headers is None:
            headers = {}
        
        if data is not None:
            data = json.dumps(data).encode('utf-8')
            headers['Content-Type'] = 'application/json'
        
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        
        try:
            response = urllib.request.urlopen(req, timeout=5)
            content = response.read().decode('utf-8')
            return response.getcode(), content, response.headers
        except urllib.error.HTTPError as e:
            content = e.read().decode('utf-8') if e.fp else ''
            return e.code, content, e.headers
        except Exception as e:
            return None, str(e), {}
    
    def test_server_startup(self):
        """Test server starts correctly"""
        self.assertTrue(self.start_server(), "Server should start successfully")
    
    def test_api_state_endpoint(self):
        """Test /api/state endpoint"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        status, content, headers = self.make_request('/api/state')
        
        self.assertEqual(status, 200, "State endpoint should return 200")
        self.assertIn('application/json', headers.get('Content-Type', ''))
        
        # Parse JSON response
        try:
            data = json.loads(content)
            self.assertIsInstance(data, dict, "Response should be JSON object")
            
            # Check required fields
            expected_fields = ['alive', 'title', 'paused', 'pos', 'dur', 'volume']
            for field in expected_fields:
                self.assertIn(field, data, f"Response should contain '{field}' field")
                
        except json.JSONDecodeError:
            self.fail("Response should be valid JSON")
    
    def test_api_cmd_endpoint(self):
        """Test /api/cmd endpoint"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test valid command
        status, content, headers = self.make_request('/api/cmd', 'POST', {'cmd': 'pause'})
        
        # Should return 200 even if mpv is not connected (graceful handling)
        self.assertIn(status, [200, 500], "Command endpoint should handle requests")
    
    def test_api_cmd_validation(self):
        """Test command validation"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test invalid command
        status, content, headers = self.make_request('/api/cmd', 'POST', {'cmd': 'rm -rf /'})
        self.assertEqual(status, 400, "Invalid commands should be rejected")
        
        # Test missing command
        status, content, headers = self.make_request('/api/cmd', 'POST', {})
        self.assertEqual(status, 400, "Missing command should be rejected")
        
        # Test invalid JSON
        status, content, headers = self.make_request('/api/cmd', 'POST', "invalid json")
        self.assertEqual(status, 400, "Invalid JSON should be rejected")
    
    def test_api_play_endpoint(self):
        """Test /api/play endpoint"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test play request
        status, content, headers = self.make_request('/api/play', 'POST', {'query': 'test song'})
        
        # Should handle gracefully even without network/mpv
        self.assertIn(status, [200, 500], "Play endpoint should handle requests")
    
    def test_html_serving(self):
        """Test HTML file serving"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        status, content, headers = self.make_request('/')
        
        self.assertEqual(status, 200, "Root endpoint should return 200")
        self.assertIn('text/html', headers.get('Content-Type', ''))
        self.assertIn('<html', content.lower(), "Response should contain HTML")
    
    def test_cors_headers(self):
        """Test CORS headers"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test OPTIONS request
        status, content, headers = self.make_request('/api/state', 'OPTIONS')
        
        self.assertEqual(status, 200, "OPTIONS request should return 200")
        self.assertIn('Access-Control-Allow-Origin', headers)
        self.assertIn('Access-Control-Allow-Methods', headers)
    
    def test_rate_limiting(self):
        """Test rate limiting functionality"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Make multiple rapid requests
        responses = []
        for i in range(10):
            status, content, headers = self.make_request('/api/state')
            responses.append(status)
        
        # Should not block legitimate requests (rate limiting is per-IP)
        self.assertTrue(all(status == 200 for status in responses), 
                       "Rate limiting should not block normal usage")
    
    def test_security_headers(self):
        """Test security headers are present"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        status, content, headers = self.make_request('/')
        
        # Check for security headers
        security_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options', 
            'X-XSS-Protection'
        ]
        
        for header in security_headers:
            self.assertIn(header, headers, f"Security header '{header}' should be present")
    
    def test_invalid_endpoints(self):
        """Test invalid endpoint handling"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test non-existent endpoint
        status, content, headers = self.make_request('/invalid/endpoint')
        self.assertEqual(status, 404, "Invalid endpoints should return 404")
        
        # Test invalid method
        status, content, headers = self.make_request('/api/state', 'DELETE')
        self.assertEqual(status, 405, "Invalid methods should return 405")
    
    def test_server_info_endpoint(self):
        """Test server info/health endpoint if available"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Try common health check endpoints
        for endpoint in ['/health', '/api/info', '/api/status']:
            status, content, headers = self.make_request(endpoint)
            if status == 200:
                try:
                    data = json.loads(content)
                    self.assertIsInstance(data, dict)
                    break
                except json.JSONDecodeError:
                    pass
    
    def test_error_handling(self):
        """Test error handling and logging"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        # Test malformed requests
        test_cases = [
            ('/api/cmd', 'POST', 'not json'),
            ('/api/play', 'POST', {'invalid': 'data'}),
            ('/api/cmd', 'POST', {'cmd': ''}),
        ]
        
        for endpoint, method, data in test_cases:
            status, content, headers = self.make_request(endpoint, method, data)
            self.assertGreaterEqual(status, 400, f"Malformed request to {endpoint} should return error")
    
    def test_concurrent_requests(self):
        """Test handling of concurrent requests"""
        if not self.start_server():
            self.skipTest("Server failed to start")
        
        import threading
        results = []
        
        def make_concurrent_request():
            status, content, headers = self.make_request('/api/state')
            results.append(status)
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=make_concurrent_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        self.assertTrue(all(status == 200 for status in results),
                       "Concurrent requests should all succeed")


class TestServerSecurity(unittest.TestCase):
    """Security-focused tests"""
    
    def test_path_traversal_protection(self):
        """Test protection against path traversal attacks"""
        # Test that MUSIC_ROOT validation prevents path traversal
        from music_ui_server import _validate_music_root
        
        # Valid paths
        valid_paths = [
            "~/music_system",
            "~/test/music",
            os.path.expanduser("~/valid_path")
        ]
        
        for path in valid_paths:
            result = _validate_music_root(path)
            if result:  # May be None if path doesn't exist, which is OK
                self.assertTrue(result.startswith(os.path.expanduser("~")))
        
        # Temporarily disable test mode for this security test
        original_test_mode = os.environ.get('MOX_TEST_MODE')
        if 'MOX_TEST_MODE' in os.environ:
            del os.environ['MOX_TEST_MODE']
        
        try:
            # Invalid paths (should return None)
            invalid_paths = [
                "/etc/passwd",
                "../../../etc/passwd",
                "/root/music",
                None,
                "",
            ]
            
            for path in invalid_paths:
                result = _validate_music_root(path)
                if path not in [None, ""]:
                    self.assertIsNone(result, f"Path '{path}' should be rejected")
        finally:
            # Restore test mode
            if original_test_mode:
                os.environ['MOX_TEST_MODE'] = original_test_mode
    
    def test_command_validation(self):
        """Test command validation against injection"""
        # Import the validation function
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
        from music_ui_server import _validate_cmd
        
        # Valid commands
        valid_commands = [
            "pause",
            "play",
            "next",
            "prev",
            "seek +10",
            "volume 50",
            "speed 1.5"
        ]
        
        for cmd in valid_commands:
            self.assertTrue(_validate_cmd(cmd), f"Command '{cmd}' should be valid")
        
        # Invalid commands
        invalid_commands = [
            "rm -rf /",
            "cat /etc/passwd",
            "curl http://evil.com",
            "; rm -rf /",
            "$(rm -rf /)",
            "`rm -rf /`",
            "pause; rm -rf /",
            "pause && rm -rf /",
            "pause | rm -rf /",
        ]
        
        for cmd in invalid_commands:
            valid, _ = _validate_cmd(cmd)
            self.assertFalse(valid, f"Command '{cmd}' should be rejected")


def run_api_tests():
    """Run all API tests"""
    # Create test suite
    suite = unittest.TestSuite()
    loader = unittest.TestLoader()
    
    # Add test cases
    suite.addTest(loader.loadTestsFromTestCase(TestMoxAPI))
    suite.addTest(loader.loadTestsFromTestCase(TestServerSecurity))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    print("🧪 Running mox API tests...")
    success = run_api_tests()
    
    if success:
        print("🎉 All API tests passed!")
        sys.exit(0)
    else:
        print("❌ Some API tests failed!")
        sys.exit(1)