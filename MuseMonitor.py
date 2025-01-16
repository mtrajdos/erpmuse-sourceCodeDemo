from pythonosc import dispatcher
from pythonosc import osc_server
from pythonosc import udp_client
import threading
import time
import sys
import signal
import numpy as np
import argparse

# Kivy imports
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.logger import Logger

class MuseSimulator:
    def __init__(self, port=5001):
        """Initialize the Muse simulator"""
        try:
            self.client = udp_client.SimpleUDPClient("127.0.0.1", port)
            self.should_run = True
            Logger.info(f"Simulator sending data to 127.0.0.1:{port}")
        except Exception as e:
            Logger.error(f"Failed to initialize simulator: {str(e)}")
            sys.exit(1)
        
    def generate_eeg_data(self):
        """Generate realistic-looking EEG data"""
        base = np.random.uniform(600, 1000, 4)
        noise = np.random.normal(0, 20, 4)
        return base + noise
    
    def run(self):
        """Run the simulator in loop"""
        sample_count = 0
        Logger.info("Starting simulation...")
        while self.should_run:
            try:
                eeg_data = self.generate_eeg_data()
                self.client.send_message("/muse/eeg", eeg_data)
                sample_count += 1
                if sample_count % 10 == 0:
                    Logger.info(f"Simulated data: {[f'{x:.2f}' for x in eeg_data]}")
                time.sleep(1/10)  # 10Hz for testing
            except Exception as e:
                Logger.error(f"Simulation error: {str(e)}")
                self.should_run = False
                break
    
    def stop(self):
        """Stop the simulator"""
        self.should_run = False

class MuseMonitorForwarder:
    def __init__(self, listen_port=5001, forward_port=5000):
        """Initialize the Muse Monitor server with forwarding capability"""
        self.server = None
        self.client = None
        self.should_run = True
        self.last_data_time = time.time()
        self.connected = False
        self.is_connected = False
        
        try:
            # Set up forwarding client (always to localhost)
            self.client = udp_client.SimpleUDPClient("127.0.0.1", forward_port)
            Logger.info(f"Forward client setup for 127.0.0.1:{forward_port}")
            
            # Set up server (listening on localhost)
            disp = dispatcher.Dispatcher()
            disp.map("/muse/eeg", self.eeg_handler)
            self.server = osc_server.ThreadingOSCUDPServer(
                ("127.0.0.1", listen_port), disp)
            Logger.info(f"Monitor listening on 127.0.0.1:{listen_port}")
            
        except Exception as e:
            Logger.error(f"Failed to initialize monitor: {str(e)}")
            sys.exit(1)
        
        # Placeholder for status callback (you might want to implement this)
        self.status_callback = type('StatusCallback', (), {
            'update_status': lambda x: None,
            'log_break': lambda x, y: None,
            'update_eeg_data': lambda x, y: None
        })()
        
    def eeg_handler(self, address: str, *args):
        current_time = time.time()
        
        # Handle connection events
        if address == "/muse/event/connected":
            self.is_connected = True
            self.status_callback.update_status(True)
            self.status_callback.log_break("CONNECTED", f"Device: {args[0] if args else 'unknown'}")
        elif address == "/muse/event/disconnected":
            self.is_connected = False
            self.status_callback.update_status(False)
            self.status_callback.log_break("DISCONNECTED", f"Device: {args[0] if args else 'unknown'}")
        elif address == "/muse/eeg":
            self.last_data_time = current_time
            if not self.is_connected:
                self.is_connected = True
                self.status_callback.update_status(True)
            
            try:
                eeg_values = [float(arg) for arg in args]
                self.status_callback.update_eeg_data(current_time, eeg_values)
                Logger.debug(f"EEG Data: {current_time:.6f}, {address}, {', '.join([f'{v:.6f}' for v in eeg_values])}")
            except Exception as e:
                Logger.error(f"Error processing EEG data: {str(e)}")
        
    def check_connection(self):
        """Check if we're still receiving data"""
        while self.should_run:
            current_time = time.time()
            if self.connected and (current_time - self.last_data_time) > 2.0:
                self.connected = False
                Logger.warning("\nConnection lost!")
            time.sleep(0.5)
            
    def start(self):
        """Start the monitor server"""
        try:
            # Start server thread
            server_thread = threading.Thread(target=self.server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            # Start connection checker
            checker_thread = threading.Thread(target=self.check_connection)
            checker_thread.daemon = True
            checker_thread.start()
            
            Logger.info("Press Ctrl+C to exit")
            
            # Keep main thread alive
            while self.should_run:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.stop()
        except Exception as e:
            Logger.error(f"Error: {str(e)}")
            self.stop()
            
    def stop(self):
        """Stop the monitor server"""
        self.should_run = False
        if self.server:
            self.server.shutdown()
            Logger.info("\nMonitor stopped")

class MuseMonitorApp(App):
    def __init__(self, mode='monitor', listen_port=5001, forward_port=5000, **kwargs):
        super().__init__(**kwargs)
        self.mode = mode
        self.listen_port = listen_port
        self.forward_port = forward_port
        self.runner = None

    def build(self):
        # Create a simple layout to show status
        layout = BoxLayout(orientation='vertical')
        self.status_label = Label(text='Initializing...')
        layout.add_widget(self.status_label)

        # Run based on mode
        if self.mode == 'simulate':
            # Run simulator
            self.runner = MuseSimulator(self.listen_port)
            sim_thread = threading.Thread(target=self.runner.run)
            sim_thread.daemon = True
            sim_thread.start()
            self.status_label.text = 'Simulation Running'
        elif self.mode == 'monitor':
            # Run monitor
            self.runner = MuseMonitorForwarder(
                listen_port=self.listen_port, 
                forward_port=self.forward_port
            )
            monitor_thread = threading.Thread(target=self.runner.start)
            monitor_thread.daemon = True
            monitor_thread.start()
            self.status_label.text = 'Monitoring EEG Data'

        return layout

    def on_stop(self):
        # Clean up resources
        if self.runner:
            if hasattr(self.runner, 'stop'):
                self.runner.stop()

def main():
    # Create argument parser
    parser = argparse.ArgumentParser(description='Muse EEG Data Monitor and Simulator')
    parser.add_argument('--listen-port', type=int, default=5001, help='Port to listen on')
    parser.add_argument('--forward-port', type=int, default=5000, help='Port to forward to')
    parser.add_argument('--simulate', action='store_true', help='Run in simulation mode')
    args = parser.parse_args()
    
    # Determine mode
    mode = 'simulate' if args.simulate else 'monitor'
    
    try:
        # Create and run the Kivy app
        app = MuseMonitorApp(
            mode=mode, 
            listen_port=args.listen_port, 
            forward_port=args.forward_port
        )
        
        # Set up signal handling
        def signal_handler(sig, frame):
            Logger.info("\nShutting down...")
            app.stop()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Run the app
        app.run()
        
    except Exception as e:
        Logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()