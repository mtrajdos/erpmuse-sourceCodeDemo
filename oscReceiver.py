from datetime import datetime
from pythonosc import dispatcher
from pythonosc import osc_server
import threading
import time

class OSCReceiver:
    def __init__(self, ip="127.0.0.1", port=5000, timeout_threshold=0.050):
        self.ip = ip
        self.port = port
        self.timeout_threshold = timeout_threshold
        self.last_data_time = None
        self.is_running = False
        self.server = None
        self.server_thread = None
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/muse/eeg", self.eeg_handler)
        
    def eeg_handler(self, address: str, *args):
        """Handle incoming EEG data and update last received time"""
        self.last_data_time = time.time()

        try:
            raw_line = args[0]  # E.g., "1748953246.274425, /muse/eeg, 763.583565393, ..."
            
            # Print the original line to preserve timestamp
            print(raw_line)

        except Exception as e:
            print(f"Error parsing EEG data: {e}")

    def is_connected(self):
        """Check if data is being received (connection is active)"""
        if self.last_data_time is None:
            return False
        
        current_time = time.time()
        time_since_last_data = current_time - self.last_data_time
        
        return time_since_last_data < self.timeout_threshold
    
    def start(self):
        """Start the OSC server in a separate thread"""
        if not self.is_running:
            self.server = osc_server.ThreadingOSCUDPServer(
                (self.ip, self.port), self.dispatcher
            )
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            self.is_running = True
            print(f"OSC Receiver listening on UDP port {self.port}")
    
    def stop(self):
        """Stop the OSC server"""
        if self.is_running and self.server:
            self.server.shutdown()
            self.is_running = False
            print("OSC Receiver stopped")

# Global instance for easy access
osc_receiver = OSCReceiver()

# Backwards compatibility - start server if run directly
if __name__ == "__main__":
    osc_receiver.start()
    try:
        while True:
            time.sleep(1)
            if osc_receiver.is_connected():
                print("✓ EEG data stream active")
            else:
                print("✗ No EEG data received")
    except KeyboardInterrupt:
        osc_receiver.stop()