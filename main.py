from kivy.app import App
from kivy.uix.image import Image as KivyImage
from kivy.uix.floatlayout import FloatLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
from kivy.logger import Logger
import numpy as np
import random
import os
from datetime import datetime
import pytz
import platform
import time

class SimplifiedEmoScenes(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_variables()
        self.initialize_timing_validation()
        self.setup_ui()
        self.setup_logging()
        Window.bind(on_key_down=self.on_key_down)
        Window.bind(on_resize=self.on_window_resize)
        
    def initialize_timing_validation(self):
        self.timing_debug = True
        self.min_allowed_iti = 1.000000
        log_dir = os.path.join(os.getcwd(), "logs") if platform.system() == "Windows" else os.path.join("/storage/emulated/0/Download", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y%m%d_%H%M%S")
        self.timing_log_filename = os.path.join(log_dir, f"TimingLog_{timestamp}.txt")
        self.timing_filepointer = open(self.timing_log_filename, "w")
        self.timing_filepointer.write("Trial,Timestamp,Intended_ITI,Actual_ITI,Stim_Duration,Trial_Start,Stim_On,Stim_Off,Violation\n")
        
    def initialize_variables(self):
        self.stim_duration = 0.600000
        self.current_trial = 1
        self.last_stim_off_time = None
        self.current_stim_on_time = None
        self.scene_stimuli = [f'checkerboard{brightness}.png' for brightness in [255, 225, 195, 175, 155]] * 125
        random.shuffle(self.scene_stimuli)
        self.showing_background = True
        self.ITIs = np.random.uniform(1.000000, 3.000000, 625)
        self.next_trial_scheduled = False
        self.trial_running = False

    def validate_timing(self, trial_num):
        if not self.timing_debug:
            return
            
        current_time = time.time()
        intended_iti = self.ITIs[trial_num - 1] if trial_num > 0 else 0
        
        actual_iti = 0
        if self.last_stim_off_time and self.current_stim_on_time:
            actual_iti = self.current_stim_on_time - self.last_stim_off_time
            
        stim_duration = 0
        if hasattr(self, 'current_stim_off_time') and self.current_stim_on_time:
            stim_duration = self.current_stim_off_time - self.current_stim_on_time
            
        violation = 1 if (actual_iti < self.min_allowed_iti and actual_iti > 0) else 0
        
        log_line = (f"{trial_num},"
                   f"{current_time:.6f},"
                   f"{intended_iti:.6f},"
                   f"{actual_iti:.6f},"
                   f"{stim_duration:.6f},"
                   f"{self.trial_start_time if hasattr(self, 'trial_start_time') else 0:.6f},"
                   f"{self.current_stim_on_time if self.current_stim_on_time else 0:.6f},"
                   f"{self.current_stim_off_time if hasattr(self, 'current_stim_off_time') else 0:.6f},"
                   f"{violation}\n")
        
        self.timing_filepointer.write(log_line)
        self.timing_filepointer.flush()
        
        if violation:
            Logger.warning(f'Timing violation in trial {trial_num}: ITI = {actual_iti:.6f}s')

    def start_experiment(self):
        """Initial experiment start after first keypress"""
        self.showing_background = False
        self.fixation_cross.opacity = 1
        # Show fixation for first ITI duration before first trial
        Clock.schedule_once(self.show_trial, self.ITIs[0])

    def show_trial(self, dt):
        if self.trial_running:
            return
            
        self.trial_running = True
        self.trial_start_time = time.time()
        self.current_stim_on_time = time.time()
        
        # Show stimulus with fixation cross
        self.background_image.opacity = 1
        self.background_image.source = os.path.join(os.path.dirname(__file__), "sprites", self.scene_stimuli[self.current_trial - 1])
        self.background_image.reload()
        self.white_square.opacity = 1
        self.white_square.pos = (Window.width - self.white_square.width, 0)
        
        Clock.schedule_once(self.end_trial, self.stim_duration)

    def log_trial_data(self):
        now = datetime.now(pytz.timezone("Europe/Berlin"))
        stim_on = self.current_stim_on_time
        stim_off = self.current_stim_off_time
        target_iti = self.ITIs[self.current_trial - 1]
        
        actual_iti = 0
        if self.last_stim_off_time:
            actual_iti = stim_on - self.last_stim_off_time
        
        iti_error = actual_iti - target_iti
        stim_file = self.scene_stimuli[self.current_trial - 1]
        
        log_entry = (f"{stim_on:.6f},"
                    f"{stim_off:.6f},"
                    f"{self.stim_duration:.6f},"
                    f"{target_iti:.6f},"
                    f"{actual_iti:.6f},"
                    f"{iti_error:.6f},"
                    f"{self.current_trial},"
                    f"{stim_file}\n")
                    
        self.datafilepointer.write(log_entry)
        self.datafilepointer.flush()

    def end_trial(self, dt):
        self.current_stim_off_time = time.time()
        self.validate_timing(self.current_trial)
        self.log_trial_data()  # Log in original format
        
        self.background_image.opacity = 0
        self.white_square.opacity = 0
        
        self.last_stim_off_time = self.current_stim_off_time
        self.trial_running = False
        
        if self.current_trial == len(self.scene_stimuli):
            self.fixation_cross.opacity = 0
            Clock.schedule_once(lambda dt: self.end_experiment(), 0)
        else:
            self.current_trial += 1
            Clock.schedule_once(self.show_trial, self.ITIs[self.current_trial - 1])

    def on_key_down(self, window, key, *args):
        if self.showing_background:
            self.start_experiment()

    def setup_ui(self):
        self.layout = FloatLayout()
        with self.layout.canvas.before:
            Color(119/255, 119/255, 119/255)
            self.rect = Rectangle(size=Window.size, pos=(0, 0))

        self.background_image = KivyImage(
            size_hint=(1, 1),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=True,
            keep_ratio=False,
            opacity=0
        )

        self.fixation_cross = KivyImage(
            source="sprites/fixation_cross.png",
            size_hint=(None, None),
            size=(Window.width * 0.05, Window.height * 0.05),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
            allow_stretch=False,
            keep_ratio=True,
            opacity=0
        )

        self.white_square = KivyImage(
            source="sprites/white_square.png",
            size_hint=(None, None),
            size=(55, 55),
            pos=(Window.width - 55, 0),
            allow_stretch=False,
            keep_ratio=True,
            opacity=0
        )

        self.layout.add_widget(self.background_image)
        self.layout.add_widget(self.white_square)
        self.layout.add_widget(self.fixation_cross)

    def setup_logging(self):
        log_dir = os.path.join(os.getcwd(), "logs") if platform.system() == "Windows" else os.path.join("/storage/emulated/0/Download", "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"ShamScenes_{timestamp}.txt")
        self.datafilepointer = open(log_filename, "w")
        self.datafilepointer.write("StimON,StimOFF,StimDuration,Target_ITI,Actual_ITI,ITI_Error,Trial,StimFile\n")

    def end_experiment(self):
        if hasattr(self, 'datafilepointer'):
            self.datafilepointer.close()
        if hasattr(self, 'timing_filepointer'):
            self.timing_filepointer.close()
        self.stop()

    def on_start(self):
        Window.fullscreen = "auto"
        self.background_image.opacity = 0
        self.fixation_cross.opacity = 0
        self.white_square.opacity = 0

    def on_window_resize(self, window, width, height):
        self.rect.size = (width, height)
        self.fixation_cross.size = (width * 0.05, height * 0.05)
        self.background_image.size = (width, height)
        self.white_square.pos = (width - self.white_square.width, 0)

    def build(self):
        return self.layout

if __name__ == "__main__":
    try:
        SimplifiedEmoScenes().run()
    except Exception as e:
        Logger.error(f'Application Error: {str(e)}')