import os
from pathlib import Path
from kivy.logger import Logger
from kivy.utils import platform as kivy_platform


class VectorSequenceController:
    """Reads and manages a pre-generated stim sequence vector"""

    def __init__(self, config):
        self.config = config

        # Use the root directory (where main.py is)
        script_dir = Path(__file__).parent.resolve()  # Directory of this file
        self.vector_file = script_dir / "vector.txt"  # Direct file path, no subdir
        
        self.category_sequence = []
        self.current_vector_file = None

    def load_vector(self, filename="vector.txt"):
        """Load vector file from root directory"""
        filepath = self.vector_file
        
        if not filepath.exists():
            Logger.error(f"Vector file not found at: {filepath}")
            raise FileNotFoundError(f"Vector file not found: {filepath}")
        
        Logger.info(f"Loading vector from: {filepath}")
        
        try:
            self.category_sequence = self._read_vector_file(filepath)
            self.current_vector_file = filepath
            
            if len(self.category_sequence) > 0:
                Logger.info(f"Successfully loaded {len(self.category_sequence)} categories from vector")
                Logger.info(f"First 10 categories: {self.category_sequence[:10]}")
                return self.category_sequence
            else:
                raise ValueError("Vector file exists but sequence is empty!")
                
        except Exception as e:
            Logger.error(f"Error loading vector: {e}")
            import traceback
            Logger.error(traceback.format_exc())
            raise

    def _read_vector_file(self, filepath):
        """Read vector sequence from file"""
        sequence = []
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
            
        # Find where sequence starts (after empty line following counts)
        sequence_start = False
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Skip header and count lines
            if line.startswith('Created:') or line.startswith('n '):
                continue
            
            # Empty line after counts section
            if not line and i > 0:
                sequence_start = True
                continue
            
            # Read sequence entries
            if sequence_start and line in self.config.CATEGORIES:
                sequence.append(line)
        
        return sequence

    def get_category_at_index(self, index):
        """Get category at specific index in the sequence"""
        if 0 <= index < len(self.category_sequence):
            return self.category_sequence[index]
        else:
            Logger.warning(f"Index {index} out of range for sequence length {len(self.category_sequence)}")
            return None

    def get_sequence_length(self):
        """Get total length of loaded sequence"""
        return len(self.category_sequence)
