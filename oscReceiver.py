from datetime import datetime
from pythonosc import dispatcher
from pythonosc import osc_server
import threading
import time

class OSCReceiver:
    def __init__(self, ip="127.0.0.1", port=5000, timeout_threshold=0.050):
        """Initialize OSC receiver
        
        Args:
            ip: IP to listen on (0.0.0.0 for all interfaces, 127.0.0.1 for localhost only)
            port: UDP port to listen on
            timeout_threshold: Time in seconds before considering connection lost
        """
        self.ip = ip
        self.port = port
        self.timeout_threshold = timeout_threshold
        self.last_data_time = None
        self.is_running = False
        self.server = None
        self.server_thread = None
        
        # Set up OSC dispatcher
        self.dispatcher = dispatcher.Dispatcher()
        self.dispatcher.map("/muse/eeg", self.eeg_handler)
        
    def eeg_handler(self, address: str, *args):
        """Handle incoming EEG data from OSC messages"""
        self.last_data_time = time.time()
        
        try:
            # When using Muse Monitor/Mind Monitor, the args contain the actual EEG values
            # The first argument might be a timestamp or the data could be sent directly
            
            # Check if first arg is a formatted string (from your simulator)
            if len(args) == 1 and isinstance(args[0], str):
                # Handle simulator format: "timestamp, /muse/eeg, value1, value2, ..."
                raw_line = args[0]
                print(raw_line)
            else:
                # Handle standard OSC format where args are the EEG channel values
                # Typically 4-6 float values for TP9, AF7, AF8, TP10, (and sometimes Right AUX, Left AUX)
                timestamp = self.last_data_time
                eeg_values = [float(arg) for arg in args]
                
                # Format output to match expected format
                values_str = ', '.join(f'{v:.9f}' for v in eeg_values)
                output_line = f"{timestamp:.6f}, {address}, {values_str}"
                print(output_line)
                
        except Exception as e:
            print(f"Error parsing EEG data: {e}")
            # Log the raw args for debugging
            print(f"Debug - Address: {address}, Args: {args}")
    
    def generic_handler(self, address: str, *args):
        """Handle other OSC messages"""
        self.last_data_time = time.time()
        # You can process other sensor data here if needed
        # For now, just update the connection time
        
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
            try:
                self.server = osc_server.ThreadingOSCUDPServer(
                    (self.ip, self.port), self.dispatcher
                )
                self.server_thread = threading.Thread(target=self.server.serve_forever)
                self.server_thread.daemon = True
                self.server_thread.start()
                self.is_running = True
                print(f"OSC Receiver listening on {self.ip}:{self.port}")
                
                # Note about network configuration
                if self.ip == "0.0.0.0":
                    print("Listening on all network interfaces")
                    print("Make sure your firewall allows UDP port", self.port)
                    
            except Exception as e:
                print(f"Failed to start OSC server: {e}")
                self.is_running = False
    
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
    
    # Create receiver with command line arguments
    osc_receiver = OSCReceiver(ip='127.0.0.1', port=5000)
    osc_receiver.start()
    
    try:
        while True:
            time.sleep(1)
            if osc_receiver.is_connected():
                print("\r✓ EEG data stream active    ", end='', flush=True)
            else:
                print("\r✗ Waiting for EEG data...   ", end='', flush=True)
    except KeyboardInterrupt:
        print("\n")
        osc_receiver.stop()