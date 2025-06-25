from kivy.config import Config
from kivy.core.window import Window
from kivy.uix.label import Label
from kivy.app import App
from kivy.uix.image import Image as KivyImage
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle
from kivy.logger import Logger
from kivy.utils import platform as kivy_platform
from oscReceiver import osc_receiver
import numpy as np
import os
from datetime import datetime
import pytz
import platform
import time
import random

# Window configuration
Window.borderless = True
Config.set('graphics', 'fullscreen', 'auto')
Config.set('graphics', 'vsync', '1')  # Enable VSync
Config.set('graphics', 'maxfps', '0')  # Uncap FPS - let device run at native refresh
Config.write()

class TouchableFloatLayout(FloatLayout):
    """Float layout that handles touch events for experiment navigation"""
    def on_touch_down(self, touch):
        app = App.get_running_app()
        if app:
            app.handle_experiment_navigation()
        return super().on_touch_down(touch)

class EmoScenes(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_variables()
        self.setup_platform_specifics()
        self.setup_ui()
        self.setup_logging()
        Window.bind(on_resize=self.on_window_resize)
        
        # Connection monitoring variables
        self.paused = False
        self.connection_check_event = None
        self.pause_start_time = None

    def initialize_variables(self):
        """Initialize all experiment variables and load stimuli"""
        # Timing configuration
        self.stim_duration = 0.600000  # 600ms stimulus duration
        self.current_trial = 1
        self.last_stim_off_time = None
        self.current_stim_on_time = None
        self.in_instruction_phase = True
        self.connection_lost_screen_active = False
        
        # Generate random ISIs between 1-3 seconds for 50,000 trials
        self.ISIs = np.random.uniform(1.000000, 3.000000, 50000)
        
        # Trial scheduling variables
        self.next_trial_scheduled = None
        self.stimulus_currently_displayed = False
        self.showing_instructions = True
        
        # Stimulus configuration
        self.stimuli = {
            'categories': ['highneg', 'lowneg', 'neutral', 'lowpos', 'highpos'],
            'per_category': 25,
            'files_per_category': {},
            'sequence': [],
            'all_files': [],
            'folder': os.path.join(os.path.dirname(__file__), "stimuli")
        }
        
        # Map categories to brightness squares
        self.category_to_square = {
            'highpos': 'square_255',
            'lowpos': 'square_255',
            'neutral': 'square_255',
            'lowneg': 'square_255',
            'highneg': 'square_255'
        }
        
        # Load and prepare stimuli
        self.load_and_categorize_stimulus_files()
        self.create_randomized_stimulus_sequence()
        self.preload_images()
        
        # Start OSC receiver for EEG connection
        osc_receiver.start()

    def setup_platform_specifics(self):
        """Configure platform-specific settings"""
        # Always use POSIX timestamps
        self.get_time = time.time
        
        # Check if we are on a mobile platform
        if kivy_platform in ('android', 'ios'):
            Logger.info(f"Mobile platform detected: {kivy_platform}")
            self.is_mobile = True
            
            # Set the log directory for Android
            self.log_dir = "/storage/emulated/0/Download/logs"

            # Apply Android-specific process priority
            if kivy_platform == 'android':
                try:
                    from jnius import autoclass
                    Process = autoclass('android.os.Process')
                    Process.setThreadPriority(Process.THREAD_PRIORITY_URGENT_DISPLAY)
                    Logger.info("Set Android thread priority to URGENT_DISPLAY")
                except Exception as e:
                    Logger.warning(f"Could not set Android priority: {e}")

        else:
            Logger.info(f"PC platform detected: {kivy_platform}")
            self.is_mobile = False
            self.log_dir = os.path.join(os.getcwd(), "logs")

    def setup_ui(self):
        """Create all UI elements"""
        self.layout = TouchableFloatLayout()

        # Gray background
        with self.layout.canvas.before:
            Color(119/255, 119/255, 119/255)
            self.rect = Rectangle(size=Window.size, pos=(0, 0))

        # Main stimulus image
        self.background_image = KivyImage(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True,
            keep_ratio=False,
            opacity=0
        )

        # Fixation cross
        self.fixation_cross = KivyImage(
            source="sprites/fixation_cross.png",
            size_hint=(None, None),
            size=(Window.width * 0.05, Window.height * 0.05),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=False,
            keep_ratio=True,
            opacity=0
        )

        # Define the square brightness values
        square_values = [0, 63, 126, 189, 255]

        # Create brightness squares dictionary
        self.squares = {}
        for value in square_values:
            square_name = f'square_{value}'
            widget = KivyImage(
                source=f"sprites/{value}_square.png",
                size_hint=(None, None),
                size=(110, 110),
                pos=(Window.width - 110, 0),
                allow_stretch=False,
                keep_ratio=True,
                opacity=0
            )
            
            # Add to dictionary and create attribute
            self.squares[square_name] = widget
            setattr(self, square_name, widget)
        
        # Connection interruption label
        self.interruption_label = Label(
            text='Connection Interrupted\n\nWaiting for EEG signal...\n\nThe experiment will resume automatically\nwhen connection is restored.',
            font_size='24sp',
            text_size=(Window.width * 0.8, None),
            halign='center',
            valign='middle',
            color=(1, 1, 1, 1),
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            opacity=0
        )

        # Add widgets to layout
        self.layout.add_widget(self.background_image)
        for square in self.squares.values():
            self.layout.add_widget(square)
        self.layout.add_widget(self.fixation_cross)
        self.layout.add_widget(self.interruption_label)

    def setup_logging(self):
        """Initialize logging system with POSIX timestamps"""
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Create log file with timestamp
        timestamp = datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y%m%d_%H%M%S")
        self.log_file_path = os.path.join(self.log_dir, f"EmoScenes_{timestamp}.txt")
        self.datafilepointer = open(self.log_file_path, "w")
        
        # Record experiment start time
        experiment_start_time = self.get_time()
        
        # Write header with experiment information
        header = (
            f"# Experiment Info:\n"
            f"# POSIX_Start: {experiment_start_time:.6f}\n"
            f"# System_Time: {timestamp}\n"
            f"# Platform: {platform.system()}\n"
            f"# Mobile_Platform: {self.is_mobile}\n"
            f"# ISI_Range: {np.min(self.ISIs):.6f} - {np.max(self.ISIs):.6f}\n"
            f"# Images_N: {len(self.preloaded_images)}\n"
            f"# Log_Path: {self.log_file_path}\n"
            f"# VSync: Enabled\n"
            f"# Target_Stim_Duration: {self.stim_duration:.6f}\n"
            f"#\n"
            f"# Format for break lines:\n"
            f"# BREAK,<POSIX_time>,<reason>,<details>\n"
            f"#\n"
        )
        self.datafilepointer.write(header)
        self.datafilepointer.write("Timestamp,BlockTrial,StimFile,StimON,StimOFF,Stim_Duration,Target_ISI,Actual_ISI,ISI_Error\n")
        self.datafilepointer.flush()
        
        self.experiment_start_time = experiment_start_time

    def load_and_categorize_stimulus_files(self):
        """Load and categorize all stimulus files"""
        # Initialize category lists
        for category in self.stimuli['categories']:
            self.stimuli['files_per_category'][category] = []
        
        # Check stimuli folder exists
        if not os.path.exists(self.stimuli['folder']):
            Logger.error(f"Stimuli folder not found: {self.stimuli['folder']}")
            return
        
        # Load all jpg files
        all_files = os.listdir(self.stimuli['folder'])
        self.stimuli['all_files'] = [f for f in all_files if f.endswith('.jpg')]
        
        # Categorize files based on filename
        for file in self.stimuli['all_files']:
            categorized = False
            for category in self.stimuli['categories']:
                if category in file.lower():
                    self.stimuli['files_per_category'][category].append(file)
                    categorized = True
                    break
            
            if not categorized:
                Logger.warning(f"File {file} could not be categorized")
        
        # Log loaded stimuli counts
        for category in self.stimuli['categories']:
            count = len(self.stimuli['files_per_category'][category])
            Logger.info(f"Loaded {count} stimuli for category: {category}")

    def create_randomized_stimulus_sequence(self):
        """Create randomized sequence of stimulus blocks"""
        self.stimuli['sequence'] = []
        
        # Create 400 unique randomized blocks
        for _ in range(400):
            block_stimuli = []
            
            # Sample from each category
            for category in self.stimuli['categories']:
                available = self.stimuli['files_per_category'][category]
                needed = self.stimuli['per_category']
                
                if len(available) >= needed:
                    selected = random.sample(available, needed)
                    block_stimuli.extend(selected)
                else:
                    Logger.warning(f"Category {category} has only {len(available)} stimuli, needed {needed}")
                    block_stimuli.extend(available)
            
            # Shuffle this block
            random.shuffle(block_stimuli)
            
            # Add to sequence
            self.stimuli['sequence'].extend(block_stimuli)
        
        Logger.info(f"Created stimulus sequence with {len(self.stimuli['sequence'])} total stimuli")

    def preload_images(self):
        """Preload all images into memory"""
        self.preloaded_images = {}
        
        # Load instruction image
        instruction_path = os.path.join(os.path.dirname(__file__), "instructionsDE", "Instruktion1.jpg")
        if os.path.exists(instruction_path):
            self.preloaded_images["instruction1"] = KivyImage(
                source=instruction_path,
                allow_stretch=True,
                keep_ratio=False
            )
        
        # Load all stimulus images
        for stim_file in set(self.stimuli['sequence']):
            image_path = os.path.join(self.stimuli['folder'], stim_file)
            if os.path.exists(image_path):
                self.preloaded_images[stim_file] = KivyImage(
                    source=image_path,
                    allow_stretch=True,
                    keep_ratio=False
                )

    def get_stimulus_category(self, stimulus_file):
        """Extract category from stimulus filename"""
        for category in self.stimuli['categories']:
            if category in stimulus_file.lower():
                return category
        return 'neutral'

    def get_square_for_category(self, category):
        """Get the brightness square widget for a category"""
        square_name = self.category_to_square.get(category)
        return self.squares.get(square_name)
                
    def handle_experiment_navigation(self):
        """Handle touch events for experiment flow"""
        if self.connection_lost_screen_active:
            # Ignore touches during connection interruption
            return
        elif self.in_instruction_phase:
            self.start_experiment()
        elif not self.in_instruction_phase:
            self.end_experiment()

    def monitor_eeg_connection(self, *args):
        """Check EEG connection status and pause/resume as needed"""
        is_connected = osc_receiver.is_connected()
        
        if not is_connected and not self.paused:
            # Connection lost - pause experiment
            self.pause_experiment()
        elif is_connected and self.paused:
            # Connection restored - resume experiment
            self.resume_experiment()

    def pause_experiment(self):
        """Pause experiment due to lost EEG connection"""
        if self.paused:
            return
            
        self.paused = True
        self.pause_start_time = self.get_time()
        
        # Cancel any scheduled trial
        if self.next_trial_scheduled:
            self.next_trial_scheduled.cancel()
            self.next_trial_scheduled = None
        
        # Hide all experiment elements
        self.background_image.opacity = 0
        for square in self.squares.values():
            square.opacity = 0
        self.fixation_cross.opacity = 0
        
        # Show interruption screen
        self.interruption_label.opacity = 1
        self.connection_lost_screen_active = True
        self.stimulus_currently_displayed = False
        
        # Log pause event
        pause_time = self.get_time()
        log_entry = f"BREAK,{pause_time:.6f},CONNECTION_LOST,EEG_stream_interrupted\n"
        self.datafilepointer.write(log_entry)
        self.datafilepointer.flush()
        
        Logger.warning("EEG connection lost - experiment paused")

    def resume_experiment(self):
        """Resume experiment after EEG connection restored"""
        if not self.paused:
            return
            
        pause_duration = self.get_time() - self.pause_start_time
        self.paused = False
        self.connection_lost_screen_active = False
        
        # Hide interruption screen and show fixation
        self.interruption_label.opacity = 0
        self.fixation_cross.opacity = 1
        
        # Log resume event
        log_entry = f"BREAK,{self.get_time():.6f},CONNECTION_RESTORED,pause_duration={pause_duration:.6f}\n"
        self.datafilepointer.write(log_entry)
        self.datafilepointer.flush()
        
        Logger.info(f"EEG connection restored - resuming after {pause_duration:.2f}s pause")
        
        # Resume with next trial after short delay
        if not self.stimulus_currently_displayed and self.current_trial <= len(self.stimuli['sequence']):
            self.next_trial_scheduled = Clock.schedule_once(self.prepare_trial, 0.5)

    def prepare_trial(self, dt):
        """Prepare and display stimulus for current trial"""
        # Check connection status
        self.monitor_eeg_connection()
        
        # Don't start if paused or already displaying
        if self.paused or self.stimulus_currently_displayed:
            return
                
        self.stimulus_currently_displayed = True
        self.next_trial_scheduled = None

        # Load current stimulus
        current_stim = self.stimuli['sequence'][self.current_trial - 1]
        if current_stim in self.preloaded_images:
            self.background_image.texture = self.preloaded_images[current_stim].texture
        else:
            Logger.error(f"Image not preloaded: {current_stim}")
            return

        # Get appropriate brightness square
        category = self.get_stimulus_category(current_stim)
        self.current_square = self.get_square_for_category(category)
        
        def display_stimulus(dt):
            # Final check before display
            if self.paused:
                self.stimulus_currently_displayed = False
                return
                
            # Show stimulus and square
            self.background_image.opacity = 1
            self.current_square.opacity = 1
            self.current_square.pos = (Window.width - self.current_square.width, 0)
            self.current_stim_on_time = self.get_time()
            
            # Schedule stimulus end
            Clock.schedule_once(self.complete_trial, self.stim_duration)
            
            self.monitor_eeg_connection()
        
        # Display stimulus on next frame
        Clock.schedule_once(display_stimulus, 0)

    def complete_trial(self, dt):
        """Hide stimulus and schedule next trial"""
        # Check connection status
        self.monitor_eeg_connection()
        
        if self.paused:
            return
        
        # Record stimulus off time and log
        self.current_stim_off_time = self.get_time()
        self.log_trial_data()
        
        # Hide stimulus and square
        self.background_image.opacity = 0
        self.current_square.opacity = 0
        
        self.last_stim_off_time = self.current_stim_off_time
        self.stimulus_currently_displayed = False
        
        # Check if experiment complete
        if self.current_trial == len(self.stimuli['sequence']):
            self.fixation_cross.opacity = 0
            Clock.schedule_once(lambda dt: self.end_experiment(), 0)
        else:
            # Calculate next ISI with drift compensation
            next_isi = self.ISIs[self.current_trial]
            if self.last_stim_off_time and self.current_stim_on_time:
                actual_duration = self.current_stim_off_time - self.current_stim_on_time
                duration_drift = actual_duration - self.stim_duration
                adjusted_isi = max(0.100000, next_isi - duration_drift)
            else:
                adjusted_isi = next_isi
                
            self.current_trial += 1
            
            # Schedule next trial
            self.next_trial_scheduled = Clock.schedule_once(self.prepare_trial, adjusted_isi)

    def on_window_resize(self, window, width, height):
        """Handle window resize events"""
        self.rect.size = (width, height)
        self.fixation_cross.size = (width * 0.05, height * 0.05)
        self.background_image.size = (width, height)
        # Update square positions
        for square in self.squares.values():
            square.pos = (width - square.width, 0)
        self.interruption_label.text_size = (width * 0.8, None)

    def build(self):
        """Build the app UI"""
        return self.layout
    
    def show_instructions(self):
        """Display instruction screen"""
        self.showing_instructions = True
        self.background_image.opacity = 1
        if "instruction1" in self.preloaded_images:
            self.background_image.texture = self.preloaded_images["instruction1"].texture
        else:
            self.background_image.source = os.path.join(os.path.dirname(__file__), "instructionsDE", "Instruktion1.jpg")
            self.background_image.reload()

    def start_experiment(self):
        """Start the experiment after instruction phase"""
        self.in_instruction_phase = False
        self.fixation_cross.opacity = 1
        
        # Start connection monitoring (125Hz check rate)
        self.connection_check_event = Clock.schedule_interval(self.monitor_eeg_connection, 0.008)
        
        # Schedule first trial
        Clock.schedule_once(self.prepare_trial, self.ISIs[0])
        Logger.info(f"Experiment started, first ISI: {self.ISIs[0]:.6f}")

    def log_trial_data(self):
        """Log trial data to file"""
        # Skip logging if connection lost
        if not osc_receiver.is_connected():
            Logger.warning(f"Skipping log for trial {self.current_trial} - connection lost")
            return
        
        # Calculate timing metrics
        now = self.get_time()
        stim_on = self.current_stim_on_time
        stim_off = self.current_stim_off_time
        target_isi = self.ISIs[self.current_trial - 1]
        
        actual_isi = 0
        if self.last_stim_off_time:
            actual_isi = stim_on - self.last_stim_off_time
        
        isi_error = actual_isi - target_isi
        stim_file = self.stimuli['sequence'][self.current_trial - 1]
        actual_stim_duration = stim_off - stim_on
        
        block_trial = f"t{self.current_trial:03d}"
        
        # Write log entry
        log_entry = (f"{now:.6f},"               # Timestamp
                    f"{block_trial},"            # Trial
                    f"{stim_file},"              # StimFile
                    f"{stim_on:.6f},"            # StimON
                    f"{stim_off:.6f},"           # StimOFF
                    f"{actual_stim_duration:.6f}," # Stim_Duration
                    f"{target_isi:.6f},"         # Target_ISI
                    f"{actual_isi:.6f},"         # Actual_ISI
                    f"{isi_error:.6f}\n")        # ISI_Error
                    
        self.datafilepointer.write(log_entry)
        self.datafilepointer.flush()

    def end_experiment(self):
        """Clean up and end the experiment"""
        Logger.info("Experiment ending")
        
        # Stop connection monitoring
        if self.connection_check_event:
            self.connection_check_event.cancel()
        
        # Stop OSC receiver
        osc_receiver.stop()
        
        # Close log file
        if hasattr(self, 'datafilepointer'):
            self.datafilepointer.close()
        
        # Exit app
        self.stop()

    def on_start(self):
        """Called when app starts"""
        Window.fullscreen = "auto"
        # Hide all elements initially
        self.background_image.opacity = 0
        self.fixation_cross.opacity = 0
        for square in self.squares.values():
            square.opacity = 0
        # Show instructions
        self.show_instructions()

if __name__ == "__main__":
    try:
        EmoScenes().run()
    except Exception as e:
        Logger.error(f'Application Error: {str(e)}')