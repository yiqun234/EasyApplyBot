#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import webbrowser
import threading
import platform
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import socket
import urllib.parse

# Global variables for storing authentication data
auth_data = None
auth_complete = threading.Event()
server_running = threading.Event()

def reset_auth_state():
    """Reset authentication state for clean restart"""
    global auth_data, auth_complete, server_running
    auth_data = None
    auth_complete.clear()
    server_running.clear()
    print("[Auth Server] Authentication state reset")

class AuthHTTPRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for processing authentication callback requests"""
    
    def do_OPTIONS(self):
        """Handle preflight requests"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24 hours
        self.end_headers()
    
    def do_POST(self):
        """Handle POST requests to receive authentication data"""
        global auth_data
        
        # Set CORS headers to allow cross-origin requests
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # Read request body
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # Parse JSON data
        try:
            auth_data = json.loads(post_data.decode('utf-8'))
            print("[Auth Server] Authentication data received")
            
            # Notify waiting thread that authentication data has been received
            auth_complete.set()
            
            # Send success response
            response = {'success': True, 'message': 'Authentication data received successfully'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            # Send error response
            print(f"[Auth Server] Error processing authentication data: {str(e)}")
            response = {'success': False, 'message': f'Error processing authentication data: {str(e)}'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """Custom log output, can be disabled or customized"""
        # Comment out the line below to disable logging
        print(f"[Auth Server] {self.address_string()} - {format%args}")

def is_port_available(port):
    """Check if port is available"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def find_available_port(start_port=5000, max_tries=10):
    """Find available port"""
    for port in range(start_port, start_port + max_tries):
        if is_port_available(port):
            return port
    raise RuntimeError(f"Unable to find available port in range {start_port} to {start_port + max_tries - 1}")

def run_server(port):
    """Run HTTP server"""
    global server_running
    
    # Create HTTP server
    server = HTTPServer(('localhost', port), AuthHTTPRequestHandler)
    print(f"[Auth Server] Authentication server started at http://localhost:{port}")
    server_running.set()
    
    # Start server until authentication data is received or timeout
    max_wait_time = 300  # Maximum wait time (seconds)
    start_time = time.time()
    
    while not auth_complete.is_set() and (time.time() - start_time) < max_wait_time:
        server.handle_request()
    
    print("[Auth Server] Authentication server closed")

def open_auth_url(auth_server_url, redirect_url, lang='en-US'):
    """Open browser for authentication with multi-language support"""
    # Build complete authentication URL
    query_params = urllib.parse.urlencode({
        'callback': redirect_url,
        'lang': lang
    })
    full_auth_url = f"{auth_server_url}?{query_params}"
    
    print(f"[Auth Server] Opening browser for authentication: {full_auth_url}")
    
    # Try to open browser
    try:
        webbrowser.open(full_auth_url)
    except Exception as e:
        print(f"[Auth Server] Unable to open browser: {str(e)}")
        print(f"[Auth Server] Please manually visit this URL for authentication: {full_auth_url}")

def start_auth_process(server_url="", lang='en-US'):
    """Start complete authentication process with multi-language support"""
    # Find available port
    port = find_available_port()
    
    # Create and start server thread
    server_thread = threading.Thread(target=run_server, args=(port,))
    server_thread.daemon = True
    server_thread.start()
    
    # Wait for server to start
    server_running.wait()
    
    # Authentication server and callback URL
    auth_server_url = server_url  # Use passed parameter, might be remote server
    redirect_url = f"http://localhost:{port}/auth/callback"
    
    # Open browser for authentication, pass lang parameter
    open_auth_url(auth_server_url, redirect_url, lang=lang)
    
    # Wait for authentication completion or timeout
    timeout = 300  # seconds
    auth_success = auth_complete.wait(timeout)
    
    if auth_success:
        print("[Auth Server] Authentication successful!")
        return auth_data
    else:
        print("[Auth Server] Authentication timeout or failed")
        return None

def check_node_server():
    """Check if Node.js authentication server is running"""
    try:
        # Try to connect to Node.js server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(('localhost', 3000))
            return result == 0
    except:
        return False

def start_node_server():
    """Start Node.js authentication server"""
    try:
        # Check if node folder exists in current directory
        node_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node')
        
        if not os.path.exists(node_dir):
            print("[Auth Server] Error: Node.js server directory not found")
            return False
        
        # Change to node directory
        os.chdir(node_dir)
        
        # Choose start command based on operating system
        if platform.system() == 'Windows':
            subprocess.Popen('npm start', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.Popen('npm start', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for server to start
        for _ in range(10):
            if check_node_server():
                print("[Auth Server] Node.js authentication server started successfully")
                return True
            time.sleep(1)
        
        print("[Auth Server] Starting Node.js authentication server timeout")
        return False
    
    except Exception as e:
        print(f"[Auth Server] Error starting Node.js authentication server: {str(e)}")
        return False

def save_auth_data(auth_data):
    """Save authentication data to local JSON file"""
    if not auth_data:
        return False
    
    try:
        # Ensure user ID and API key exist
        user_id = auth_data.get('user_id')
        api_key = auth_data.get('api_key')

        if not user_id or not api_key:
            print("[Auth Server] Authentication data incomplete, cannot save")
            return False

        # Create authentication data JSON object
        auth_json = {
            "userId": user_id,
            "apiKey": api_key,
            "authenticated": True,
            "timestamp": time.time()
        }
        
        # Save to current folder
        auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        
        # Write to JSON file
        with open(auth_file_path, 'w', encoding='utf-8') as f:
            json.dump(auth_json, f, indent=2)
        return True
        
    except Exception as e:
        print(f"[Auth Server] Error saving authentication data: {str(e)}")
        return False

def get_auth_data():
    """Get authentication data from local JSON file"""
    try:
        auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        
        if not os.path.exists(auth_file_path):
            return None
            
        with open(auth_file_path, 'r', encoding='utf-8') as f:
            auth_data = json.load(f)
            
        # Validate data integrity
        if not auth_data.get('userId') or not auth_data.get('apiKey'):
            return None
            
        return {
            "user_id": auth_data.get('userId'),
            "api_key": auth_data.get('apiKey')
        }
        
    except Exception as e:
        print(f"[Auth Server] Error reading authentication data: {str(e)}")
        return None

def authenticate(lang='en-US'):
    """Main authentication function, returns authentication data with multi-language support"""
    # First check if saved authentication data exists
    existing_auth = get_auth_data()
    if existing_auth:
        print("[Auth Server] Using existing authentication data")
        return existing_auth
    
    # Check if remote server URL is set
    remote_server_url = os.environ.get('EASYAPPLY_AUTH_SERVER') or "https://account.nuomi.ai/authorize"
    
    # Start authentication process, pass lang parameter
    auth_result = start_auth_process(server_url=remote_server_url, lang=lang)
    
    # If authentication successful, save data
    if auth_result:
        save_auth_data(auth_result)
    
    return auth_result