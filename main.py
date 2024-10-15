from kivy.app import App
from kivy.uix.image import Image as KivyImage
from kivy.uix.boxlayout import BoxLayout
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.graphics import Color, Rectangle
import numpy as np
import os
from datetime import datetime
import pytz
import random
import platform
from oscServer import OscServer
from pythonosc import udp_client
import time

class EmoScenes(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        print("Initializing EmoScenes")
        self.scene_time = None
        self.cross_time = None
        self.int_DurationPic = 0.600000
        self.current_trial = 0
        self.client = udp_client.SimpleUDPClient('127.0.0.1', 1337)
        self.last_trial_end_time = None
        self.last_scene_time = None
        self.trial_start_time = None
        self.intended_iti = None
        self.next_trial_scheduled = False
        self.estimated_processing_time = 0.020000
        self.scene_stimuli = []
        self.preloaded_images = {}
        self.osc_server = OscServer()
        self.current_block = 0
        self.datafilepointer = None
        self.layout = BoxLayout(orientation="horizontal")
        self.fixation_path = "sprites/fixation_cross.png"
        self.image = KivyImage(size_hint=(1, 1), allow_stretch=True, keep_ratio=False)
        self.layout.add_widget(self.image)
        self.load_vector_file("veclength300.txt")
        self.load_stimuli_from_folder()
        self.randomize_stimuli()
        self.setup_logging()
        Window.bind(on_key_down=self.on_key_down)
        self.ITIs = self.generate_random_ITIs(500)
        
    def start_osc_server(self):
        print("Starting OSC server")
        self.osc_server.start()

    def generate_random_ITIs(self, num_ITIs):
        print(f"Generating {num_ITIs} random ITIs")
        return np.random.uniform(1.000000, 3.000000, num_ITIs)

    def load_vector_file(self, vector_file):
        print(f"Loading vector file: {vector_file}")
        vector_path = os.path.join(os.path.dirname(__file__), vector_file)
        if os.path.exists(vector_path):
            self.RandVec = np.loadtxt(vector_path, dtype=int).flatten()
            print(f"Loaded {len(self.RandVec)} values from vector file")
        else:
            print(f"Error: Vector file not found at {vector_path}")
            
    def randomize_stimuli(self):
        random.shuffle(self.scene_stimuli)
        print("Stimuli randomized for new block")
        print(f"First 5 stimuli after randomization: {self.scene_stimuli[:5]}")

    def load_stimuli_from_folder(self, folder_name="stimuli"):
        print(f"Loading stimuli from folder: {folder_name}")
        self.scene_stimuli = []
        folder_path = os.path.join(os.path.dirname(__file__), folder_name)
        print(f"Full path to stimuli folder: {folder_path}")
        if not os.path.exists(folder_path):
            print(f"Error: Folder '{folder_path}' does not exist.")
            return
        try:
            all_files = os.listdir(folder_path)
            print(f"Total files in directory: {len(all_files)}")
            print(f"First 5 files in directory: {all_files[:5]}")
            for filename in all_files:
                if filename.lower().endswith(('.jpg', '.jpeg', '.png')):  # Check for multiple image formats
                    self.scene_stimuli.append(filename)
            print(f"Found {len(self.scene_stimuli)} stimuli in {folder_name}")
            if len(self.scene_stimuli) > 0:
                print(f"First 5 stimuli: {self.scene_stimuli[:5]}")
            else:
                print("No stimuli found. Check file extensions and permissions.")
        except Exception as e:
            print(f"Error reading directory: {e}")
        self.preload_images()

    def preload_images(self):
        print("Preloading images")
        for filename in self.scene_stimuli:
            image_path = os.path.join(os.path.dirname(__file__), "stimuli", filename)
            if os.path.exists(image_path):
                self.preloaded_images[filename] = KivyImage(source=image_path)
                print(f"Preloaded: {filename}")
            else:
                print(f"Error: Image file not found: {image_path}")
        print(f"Preloaded {len(self.preloaded_images)} images")

    def setup_logging(self):
        print("Setting up logging")
        if platform.system() == "Windows":
            log_dir = os.path.join(os.getcwd(), "logs")
        else:
            log_dir = os.path.join("/storage/emulated/0/Download", "logs")

        if not os.path.exists(log_dir):
            os.makedirs(log_dir)

        timestamp = datetime.now(pytz.timezone("Europe/Berlin")).strftime("%Y%m%d_%H%M%S")
        log_filename = os.path.join(
            log_dir, f"FFP-{self.current_block}_{timestamp}.txt"
        )

        print(f"Log file created: {log_filename}")
        try:
            self.datafilepointer = open(log_filename, "w")
        except Exception as e:
            print(f"Error opening log file: {e}")

        self.datafilepointer.write(
            "CrossTime,SceneTime,PicDuration,Target_ITI,Actual_ITI,ITI_Error,Block,Trial,Stimulus\n"
        )

    def handle_osc_message(self, address, *args):
        print(f"Received OSC message: {address} {args}")

    def on_start(self):
        print("Application starting")
        Window.fullscreen = "auto"
        self.start_osc_server()
        self.show_instructions()

    def show_instructions(self):
        print(f"Showing instructions for block {self.current_block}")
        if self.current_block == 0:
            self.instruction_images = [
                "Instruktion_prebaseline1.jpg",
                "Instruktion_prebaseline2.jpg",
            ]
        elif self.current_block == 1:
            self.instruction_images = ["Instruktion1.jpg", "Instruktion2.jpg"]
        elif self.current_block == 2:
            self.instruction_images = ["Instruktion2.jpg"]
        elif self.current_block == 3:
            self.instruction_images = ["Instruktion2.jpg"]
        elif self.current_block == 4:
            self.instruction_images = ["Instruktion3.jpg"]
        self.instruction_index = 0
        self.show_next_instruction()

    def show_next_instruction(self):
        print(f"Showing instruction {self.instruction_index + 1} of {len(self.instruction_images)}")
        if self.instruction_index < len(self.instruction_images):
            instr_path = os.path.join(
                os.path.dirname(__file__),
                "instructionsDE",
                self.instruction_images[self.instruction_index],
            )
            print(f"Instruction image path: {instr_path}")
            if os.path.exists(instr_path):
                self.image.source = instr_path
                self.image.reload()
                print(f"Loaded instruction image: {self.instruction_images[self.instruction_index]}")
            else:
                print(f"Error: Instruction image not found: {instr_path}")
            self.instruction_index += 1
        else:
            print("All instructions shown, starting trials")
            self.current_trial = 0
            self.schedule_next_trial()

    def on_key_down(self, window, key, *args):
        print(f"Key pressed: {key}")
        if self.instruction_index < len(self.instruction_images):
            self.show_next_instruction()
        elif self.current_block == 4:
            self.end_experiment()
        else:
            if not self.next_trial_scheduled:
                self.schedule_next_trial()

    def schedule_next_trial(self, dt=None):
        if self.next_trial_scheduled:
            return

        print(f"Scheduling trial {self.current_trial} in block {self.current_block}")
        print(f"Total stimuli: {len(self.scene_stimuli)}")

        current_time = time.time()
        if self.last_trial_end_time is not None:
            actual_iti = current_time - self.last_trial_end_time
            print(f"Actual ITI: {actual_iti:.6f} seconds")
        else:
            actual_iti = 0

        if self.current_trial >= 125:
            self.current_block += 1
            if self.current_block < 4:
                self.randomize_stimuli()  # Randomize stimuli at the start of each new block
                self.show_instructions()
                self.current_trial = 0
            else:
                self.end_experiment()
                return

        if self.current_trial < len(self.scene_stimuli):
            self.intended_iti = self.ITIs[self.current_trial]
            print(f"Intended ITI for next trial: {self.intended_iti:.6f} seconds")
            
            fixation_duration = max(0.100000, self.intended_iti - self.int_DurationPic - self.estimated_processing_time)
            
            print(f"Adjusted fixation duration: {fixation_duration:.6f} seconds")
            
            Clock.schedule_once(lambda dt: self.show_fixation_cross(fixation_duration), 0)
            self.next_trial_scheduled = True
        else:
            print("Error: Ran out of stimuli before block completion")
            self.end_experiment()

        self.last_trial_end_time = current_time

    def show_fixation_cross(self, duration):
        print(f"Showing fixation cross for {duration:.6f} seconds")
        with self.layout.canvas.before:
            Color(119 / 255, 119 / 255, 119 / 255)
            self.rect = Rectangle(size=self.layout.size, pos=self.layout.pos)
        self.image.source = self.fixation_path
        self.image.allow_stretch = False
        self.image.keep_ratio = True
        self.image.reload()
        
        now = datetime.now(pytz.timezone("Europe/Berlin"))
        self.cross_time = now.timestamp()

        Clock.schedule_once(self.show_trial, duration)

    def show_trial(self, dt):
        print(f"Showing trial stimulus for trial {self.current_trial}")
        print(f"Total stimuli: {len(self.scene_stimuli)}")
        self.trial_start_time = time.time()
        if self.current_trial >= len(self.scene_stimuli):
            print(f"Error: Trial index {self.current_trial} exceeds the number of stimuli ({len(self.scene_stimuli)}).")
            self.end_experiment()
            return

        self.timestamp = datetime.now(pytz.timezone("Europe/Berlin"))
        stim_file = self.scene_stimuli[self.current_trial]
        print(f"Current stimulus: {stim_file}")

        if stim_file in self.preloaded_images:
            self.image = self.preloaded_images[stim_file]
            self.image.allow_stretch = True
            self.image.keep_ratio = False
            self.image.size_hint = (1, 1)
            self.layout.clear_widgets()
            self.layout.add_widget(self.image)
            print(f"Loaded stimulus image: {stim_file}")
        else:
            print(f"Error: Image {stim_file} not found in preloaded images.")
            full_path = os.path.join(os.path.dirname(__file__), "stimuli", stim_file)
            print(f"Attempted to load from: {full_path}")
            self.end_trial(0)
            return
        
        now = datetime.now(pytz.timezone("Europe/Berlin"))
        self.scene_time = now.timestamp()
        target_iti = self.ITIs[self.current_trial]

        actual_iti = self.scene_time - self.last_scene_time if self.last_scene_time is not None else 0
        self.last_scene_time = self.scene_time

        iti_error = actual_iti - target_iti

        log_entry = f"{self.cross_time:.6f},{self.scene_time:.6f},{self.int_DurationPic:.6f},{target_iti:.6f},{actual_iti:.6f},{iti_error:.6f},{self.current_block},{self.current_trial},{stim_file}\n"
        self.datafilepointer.write(log_entry)

        print(f"Logged: {log_entry.strip()}")

        Clock.schedule_once(self.end_trial, self.int_DurationPic)
        
    def end_trial(self, dt):
        print("Ending trial and scheduling next")
        self.datafilepointer.flush()
        self.next_trial_scheduled = False
        self.current_trial += 1
        self.schedule_next_trial()

    def end_experiment(self):
        print("Ending experiment")
        if self.datafilepointer is not None:
            self.datafilepointer.close()
        self.stop()
        print("Experiment finished. Goodbye!")

    def on_stop(self):
        print("Stopping application")
        if self.osc_server:
            self.osc_server.server.shutdown()
            self.osc_server.server.server_close()
            print("OSC server stopped.")

    def build(self):
        return self.layout

if __name__ == "__main__":
    EmoScenes().run()