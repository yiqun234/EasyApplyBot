import os
import yaml
import threading
import empyrebase
import traceback
import time

class FirebaseManager:
    """
    Handles Firebase Firestore interaction using empyrebase.
    Simulates real-time listening via polling, reads from cloud, does not write.
    """
    def __init__(self, user_id, update_callback, initial_sync_done_callback):
        if not user_id:
            raise ValueError("FirebaseManager requires a valid user_id")
        
        self.user_id = user_id
        self.update_callback = update_callback
        self.initial_sync_done_callback = initial_sync_done_callback
        self.last_known_config = None
        self.is_running = True

        # Hardcoded Firebase config as requested
        firebase_config = {
            "apiKey": "AIzaSyAeHptX0vuZVy1Oos_LyOSjtoVTU4b6m9s",
            "authDomain": "easy-apply-bot.firebaseapp.com",
            "databaseURL": "https://easy-apply-bot-default-rtdb.firebaseio.com",
            "storageBucket": "easy-apply-bot.appspot.com",
            "projectId": "easy-apply-bot",
            "messagingSenderId": "40362191929",
            "appId": "1:40362191929:web:cbfec3cafe37f6e85f31e8"
        }
        
        try:
            firebase_app = empyrebase.initialize_app(firebase_config)
            self.db = firebase_app.firestore()
            # Get a reference to the collection, then the document
            self.doc_ref = self.db.collection("configs").document(self.user_id)
            print("✅ Firebase initialized successfully.")
            
            # Start the background polling thread
            self.polling_thread = threading.Thread(target=self._poll_for_changes, daemon=True)
            self.polling_thread.start()
            
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            traceback.print_exc()
            # Also notify UI on failure to prevent freezing
            self.initial_sync_done_callback()

    def _poll_for_changes(self):
        """Periodically polls Firestore to check for document changes."""
        # First, perform the initial sync
        try:
            print(f"☁️ Performing initial sync for document: configs/{self.user_id}...")
            initial_config = self.doc_ref.get_document()
            if initial_config:
                print("✅ Initial config loaded from Firestore.")
                self.last_known_config = initial_config
                self.update_callback(initial_config)
            else:
                print("ℹ️ No initial config found on Firestore.")
        except Exception as e:
            if "NOT_FOUND" in str(e):
                 print(f"ℹ️ Document 'configs/{self.user_id}' not found during initial sync.")
            else:
                print(f"❌ Initial sync failed: {e}")
        finally:
            self.initial_sync_done_callback()
            
        # Start the polling loop
        while self.is_running:
            try:
                time.sleep(5) # Poll every 5 seconds
                current_config = self.doc_ref.get_document()
                
                if current_config and current_config != self.last_known_config:
                    print("🔄 Config updated from cloud.")
                    self.last_known_config = current_config
                    self.update_callback(current_config)
                    
            except Exception as e:
                if "NOT_FOUND" not in str(e):
                    print(f"❌ Firestore polling error: {e}")
                time.sleep(15) # Wait longer after an error

    def stop_polling(self):
        """Stops the polling thread."""
        print("🛑 Stopping Firestore polling...")
        self.is_running = False 