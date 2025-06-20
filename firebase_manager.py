import os
import yaml
import threading
import pyrebase

class FirebaseManager:
    """
    Use pyrebase4 client SDK to handle Firebase Realtime Database real-time listening
    Lower latency, more stable connection!
    """
    def __init__(self, user_id, update_callback, initial_sync_done_callback):
        """
        Initialize Firebase client manager
        :param user_id: User's unique ID
        :param update_callback: Function called when cloud updates are received, signature: func(config_data)
        :param initial_sync_done_callback: Function called after initial sync is completed, signature: func()
        """
        if not user_id:
            raise ValueError("FirebaseManager requires a valid user_id")
        
        self.user_id = user_id
        self.update_callback = update_callback
        self.initial_sync_done_callback = initial_sync_done_callback
        self.stream = None
        
        # Firebase configuration
        config = {
            "apiKey": "AIzaSyAeHptX0vuZVy1Oos_LyOSjtoVTU4b6m9s",
            "authDomain": "easy-apply-bot.firebaseapp.com",
            "databaseURL": "https://easy-apply-bot-default-rtdb.firebaseio.com",
            "storageBucket": "easy-apply-bot.firebasestorage.app"
        }
        
        # Initialize Firebase
        self.firebase = pyrebase.initialize_app(config)
        self.db = self.firebase.database()
        
        print(f"[Firebase] Client initialized successfully, user: {user_id[:8]}...")

    def initial_sync_and_listen(self):
        """Start sync and listening in separate thread"""
        thread = threading.Thread(target=self._sync_and_listen_worker, daemon=True)
        thread.start()

    def _sync_and_listen_worker(self):
        """Worker thread: perform initial sync, then start real-time listening"""
        try:
            # 1. First try to get existing config from Firebase
            print(f"[Firebase] Syncing user config: {self.user_id}")
            firebase_config = self.db.child("configs").child(self.user_id).get().val()
            
            if firebase_config:
                print("[Firebase] Found cloud config, loading...")
                self.update_callback(firebase_config)
            else:
                print("[Firebase] No cloud config, uploading local config...")
                # If Firebase has no config, upload local config
                local_config = self._load_local_config()
                if local_config:
                    self.save_config(local_config)
            
        except Exception as e:
            print(f"[Firebase] Initial sync error: {e}")
        
        # Notify sync completion
        self.initial_sync_done_callback()
        
        # 2. Start real-time listening
        print(f"[Firebase] 🔥 Starting real-time config listening...")
        try:
            self.stream = self.db.child("configs").child(self.user_id).stream(self._on_config_change)
        except Exception as e:
            print(f"[Firebase] Failed to start listening: {e}")

    def _on_config_change(self, message):
        """Firebase real-time listening callback - truly real-time!"""
        try:
            if message["event"] == "put":
                config_data = message["data"]
                if config_data:
                    print("[Firebase] 🔄 Config change detected, syncing...")
                    self.update_callback(config_data)
                    
        except Exception as e:
            print(f"[Firebase] Error processing config change: {e}")

    def save_config(self, config_data):
        """Save config to Firebase"""
        try:
            print("[Firebase] 💾 Saving config to cloud...")
            self.db.child("configs").child(self.user_id).set(config_data)
            print("[Firebase] ✅ Config saved successfully")
        except Exception as e:
            print(f"[Firebase] Failed to save config: {e}")

    def _load_local_config(self):
        """Load local config.yaml"""
        try:
            if os.path.exists("config.yaml"):
                with open("config.yaml", "r", encoding="utf-8") as f:
                    return yaml.safe_load(f)
        except Exception as e:
            print(f"[Firebase] Failed to read local config: {e}")
        return None

    def stop_listening(self):
        """Stop listening"""
        if self.stream:
            self.stream.close()
            print("[Firebase] Stopped listening") 