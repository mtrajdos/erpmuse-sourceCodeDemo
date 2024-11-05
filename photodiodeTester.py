from kivy.app import App
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import numpy as np
import os
from datetime import datetime
import pytz
import time

class WhiteFlashExperiment(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.initialize_variables()
        self.setup_ui()
        self.setup_logging()
        Window.bind(on_key_down=self.on_key_down)
        
    def initialize_variables(self):
        self.cross_time = None
        self.flash_time = None
        self.flash_duration = 0.600000  # 600ms
        self.current_trial = 1
        self.max_trials = 125
        self.last_trial_end_time = None
        self.last_flash_time = None
        self.next_trial_scheduled = False
        self.estimated_processing_time = 0.020000
        self.ITIs = np.random.uniform(1.000000, 3.000000, self.max_trials)

    def setup_ui(self):
        self.layout = BoxLayout(orientation="horizontal")
        self.image = Image(size_hint=(1, 1), allow_stretch=True, keep_ratio=False)
        self.layout.add_widget(self.image)
        self.fixation_path = "sprites/fixation_cross.png"

    def setup_logging(self):
        log_dir = os.path.join(os.getcwd(), "logs")
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(log_dir, f"white-flash_{timestamp}.txt")
        self.datafilepointer = open(log_filename, "w")
        self.datafilepointer.write("CrossTime,FlashTime,FlashDuration,Target_ITI,Actual_ITI,ITI_Error,Trial\n")

    def on_start(self):
        Window.fullscreen = "auto"
        self.schedule_next_trial()

    def on_key_down(self, window, key, *args):
        if not self.next_trial_scheduled:
            self.schedule_next_trial()

    def schedule_next_trial(self, dt=None):
        if self.next_trial_scheduled:
            return

        current_time = time.time()
        
        if self.last_trial_end_time is not None:
            actual_iti = current_time - self.last_trial_end_time

        if self.current_trial > self.max_trials:
            self.end_experiment()
            return

        intended_iti = self.ITIs[self.current_trial - 1]
        fixation_duration = max(0.100000, intended_iti - self.flash_duration - self.estimated_processing_time)
        Clock.schedule_once(lambda dt: self.show_fixation_cross(fixation_duration), 0)
        self.next_trial_scheduled = True
        self.last_trial_end_time = current_time

    def show_fixation_cross(self, duration):
        # Set grey background
        with self.layout.canvas.before:
            Color(119/255, 119/255, 119/255)  # Grey color
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        
        self.image.source = self.fixation_path
        self.image.allow_stretch = False
        self.image.keep_ratio = True
        self.image.reload()
        
        self.cross_time = datetime.now(pytz.timezone("Europe/Berlin")).timestamp()
        Clock.schedule_once(self.show_white_screen, duration)

    def show_white_screen(self, dt):
        # Set white background
        with self.layout.canvas.before:
            Color(1, 1, 1)  # White color
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        
        # Clear the fixation cross
        self.image.source = ""
        
        self.log_trial_data()
        Clock.schedule_once(self.end_trial, self.flash_duration)

    def log_trial_data(self):
        now = datetime.now(pytz.timezone("Europe/Berlin"))
        self.flash_time = now.timestamp()
        target_iti = self.ITIs[self.current_trial - 1]
        actual_iti = self.flash_time - self.last_flash_time if self.last_flash_time is not None else 0
        self.last_flash_time = self.flash_time
        iti_error = actual_iti - target_iti
        
        log_entry = f"{self.cross_time:.6f},{self.flash_time:.6f},{self.flash_duration:.6f},"
        log_entry += f"{target_iti:.6f},{actual_iti:.6f},{iti_error:.6f},{self.current_trial}\n"
        self.datafilepointer.write(log_entry)
        self.datafilepointer.flush()

    def end_trial(self, dt):
        self.next_trial_scheduled = False
        self.current_trial += 1
        self.schedule_next_trial()

    def end_experiment(self):
        if self.datafilepointer:
            self.datafilepointer.close()
        self.stop()

    def build(self):
        return self.layout

if __name__ == "__main__":
    WhiteFlashExperiment().run()