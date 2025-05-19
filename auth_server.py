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

# 全局变量用于存储认证数据
auth_data = None
auth_complete = threading.Event()
server_running = threading.Event()

class AuthHTTPRequestHandler(BaseHTTPRequestHandler):
    """处理认证回调请求的HTTP处理器"""
    
    def do_OPTIONS(self):
        """处理预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Access-Control-Max-Age', '86400')  # 24小时
        self.end_headers()
    
    def do_POST(self):
        """处理POST请求，接收认证数据"""
        global auth_data
        
        # 设置CORS头，允许跨域请求
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        
        # 读取请求体
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        # 解析JSON数据
        try:
            auth_data = json.loads(post_data.decode('utf-8'))
            print("[认证服务器] 接收到认证数据")
            
            # 通知等待线程已收到认证数据
            auth_complete.set()
            
            # 发送成功响应
            response = {'success': True, 'message': '认证数据已成功接收'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
            
        except Exception as e:
            # 发送错误响应
            print(f"[认证服务器] 处理认证数据时出错: {str(e)}")
            response = {'success': False, 'message': f'处理认证数据时出错: {str(e)}'}
            self.wfile.write(json.dumps(response).encode('utf-8'))
    
    def log_message(self, format, *args):
        """自定义日志输出，可以屏蔽或定制"""
        # 可以注释掉下面这行以禁用日志
        print(f"[认证服务器] {self.address_string()} - {format%args}")

def is_port_available(port):
    """检查端口是否可用"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) != 0

def find_available_port(start_port=5000, max_tries=10):
    """查找可用端口"""
    for port in range(start_port, start_port + max_tries):
        if is_port_available(port):
            return port
    raise RuntimeError(f"无法找到 {start_port} 到 {start_port + max_tries - 1} 范围内的可用端口")

def run_server(port):
    """运行HTTP服务器"""
    global server_running
    
    # 创建HTTP服务器
    server = HTTPServer(('localhost', port), AuthHTTPRequestHandler)
    print(f"[认证服务器] 认证服务器启动在 http://localhost:{port}")
    server_running.set()
    
    # 启动服务器直到收到认证数据或超时
    max_wait_time = 300  # 最大等待时间(秒)
    start_time = time.time()
    
    while not auth_complete.is_set() and (time.time() - start_time) < max_wait_time:
        server.handle_request()
    
    print("[认证服务器] 认证服务器已关闭")

def open_auth_url(auth_server_url, redirect_url, lang='en-US'):
    """打开浏览器进行认证，支持多语言"""
    # 构建完整的认证URL
    query_params = urllib.parse.urlencode({
        'callback': redirect_url,
        'lang': lang
    })
    full_auth_url = f"{auth_server_url}?{query_params}"
    
    print(f"[认证服务器] 打开浏览器进行认证: {full_auth_url}")
    
    # 尝试打开浏览器
    try:
        webbrowser.open(full_auth_url)
    except Exception as e:
        print(f"[认证服务器] 无法打开浏览器: {str(e)}")
        print(f"[认证服务器] 请手动访问此URL进行认证: {full_auth_url}")

def start_auth_process(server_url="http://44.247.228.229:3001", lang='en-US'):
    """启动完整认证流程，支持多语言"""
    # 查找可用端口
    port = find_available_port()
    
    # 创建并启动服务器线程
    server_thread = threading.Thread(target=run_server, args=(port,))
    server_thread.daemon = True
    server_thread.start()
    
    # 等待服务器启动
    server_running.wait()
    
    # 认证服务器和回调URL
    auth_server_url = server_url  # 使用传入的参数，可能是远程服务器
    redirect_url = f"http://localhost:{port}/auth/callback"
    
    # 打开浏览器进行认证，传递lang参数
    open_auth_url(auth_server_url, redirect_url, lang=lang)
    
    # 等待认证完成或超时
    timeout = 300  # 秒
    auth_success = auth_complete.wait(timeout)
    
    if auth_success:
        print("[认证服务器] 认证成功！")
        return auth_data
    else:
        print("[认证服务器] 认证超时或失败")
        return None

def check_node_server():
    """检查Node.js认证服务器是否正在运行"""
    try:
        # 尝试连接到Node.js服务器
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex(('localhost', 3000))
            return result == 0
    except:
        return False

def start_node_server():
    """启动Node.js认证服务器"""
    try:
        # 检查当前目录下是否有node文件夹
        node_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'node')
        
        if not os.path.exists(node_dir):
            print("[认证服务器] 错误: 找不到Node.js服务器目录")
            return False
        
        # 切换到node目录
        os.chdir(node_dir)
        
        # 根据操作系统类型选择启动命令
        if platform.system() == 'Windows':
            subprocess.Popen('npm start', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            subprocess.Popen('npm start', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # 等待服务器启动
        for _ in range(10):
            if check_node_server():
                print("[认证服务器] Node.js认证服务器已成功启动")
                return True
            time.sleep(1)
        
        print("[认证服务器] 启动Node.js认证服务器超时")
        return False
    
    except Exception as e:
        print(f"[认证服务器] 启动Node.js认证服务器时发生错误: {str(e)}")
        return False

def save_auth_data(auth_data):
    """保存认证数据到本地JSON文件"""
    if not auth_data:
        return False
    
    try:
        # 确保有用户ID和API密钥
        user_id = auth_data.get('user_id')
        api_key = auth_data.get('api_key')
        
        if not user_id or not api_key:
            print("[认证服务器] 认证数据不完整，无法保存")
            return False
            
        # 创建认证数据JSON对象
        auth_json = {
            "userId": user_id,
            "apiKey": api_key,
            "authenticated": True,
            "timestamp": time.time()
        }
        
        # 保存到当前文件夹
        auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        
        # 写入JSON文件
        with open(auth_file_path, 'w', encoding='utf-8') as f:
            json.dump(auth_json, f, indent=2)
        return True
        
    except Exception as e:
        print(f"[认证服务器] 保存认证数据时出错: {str(e)}")
        return False

def get_auth_data():
    """从本地JSON文件获取认证数据"""
    try:
        auth_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'auth.json')
        
        if not os.path.exists(auth_file_path):
            return None
            
        with open(auth_file_path, 'r', encoding='utf-8') as f:
            auth_data = json.load(f)
            
        # 验证数据完整性
        if not auth_data.get('userId') or not auth_data.get('apiKey'):
            return None
            
        return {
            "user_id": auth_data.get('userId'),
            "api_key": auth_data.get('apiKey')
        }
        
    except Exception as e:
        print(f"[认证服务器] 读取认证数据时出错: {str(e)}")
        return None

def authenticate(lang='en-US'):
    """主认证函数，返回认证数据，支持多语言"""
    # 首先检查是否已有保存的认证数据
    existing_auth = get_auth_data()
    if existing_auth:
        print("[认证服务器] 使用现有认证数据")
        return existing_auth
    
    # 检查远程服务器URL是否设置
    remote_server_url = os.environ.get('EASYAPPLY_AUTH_SERVER') or "http://44.247.228.229:3001"
    
    # 启动认证流程，传递lang参数
    auth_result = start_auth_process(server_url=remote_server_url, lang=lang)
    
    # 如果认证成功，保存数据
    if auth_result:
        save_auth_data(auth_result)
    
    return auth_result