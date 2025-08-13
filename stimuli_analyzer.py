"""Stimuli complexity and brightness analyzer"""
import os
import statistics
from pathlib import Path
from kivy.logger import Logger
from PIL import Image
import numpy as np

class StimuliAnalyzer:
    """Analyzes stimuli complexity (filesize) and brightness across categories"""
    
    def __init__(self, stimuli_dir="stimuli"):
        self.stimuli_dir = Path(stimuli_dir)
        self.categories = ['lowpos', 'highpos', 'neutral', 'lowneg', 'highneg']
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp'}
        
        # Category mapping based on exact filename patterns
        self.category_patterns = {
            'lowpos': ['lowpos'],
            'highpos': ['highpos'],
            'neutral': ['neutral'],
            'lowneg': ['lowneg'],
            'highneg': ['highneg']
        }
        
    def analyze_all_categories(self):
        """Analyze all stimuli categories and print results to console"""
        Logger.info("=" * 60)
        Logger.info("STIMULI COMPLEXITY & BRIGHTNESS ANALYSIS")
        Logger.info("=" * 60)
        
        # First, detect what categories actually exist in the files
        detected_categories = self._detect_categories()
        Logger.info(f"Detected categories from filenames: {detected_categories}")
        
        overall_stats = {
            'filesize': [],
            'brightness': []
        }
        
        # Use detected categories or fallback to predefined ones
        categories_to_analyze = detected_categories if detected_categories else self.categories
        
        for category in categories_to_analyze:
            category_stats = self._analyze_category(category)
            
            if category_stats:
                self._print_category_results(category, category_stats)
                
                # Add to overall stats
                overall_stats['filesize'].extend(category_stats['filesize'])
                overall_stats['brightness'].extend(category_stats['brightness'])
            else:
                Logger.warning(f"No valid images found in category: {category}")
        
        # Print overall statistics
        if overall_stats['filesize'] and overall_stats['brightness']:
            self._print_overall_results(overall_stats)
        
        Logger.info("=" * 60)
    
    def _detect_categories(self):
        """Detect categories from actual filenames"""
        if not self.stimuli_dir.exists():
            return []
        
        detected = set()
        
        for image_path in self.stimuli_dir.glob("*"):
            if (image_path.suffix.lower() in self.supported_formats and 
                image_path.is_file()):
                
                filename = image_path.stem.lower()
                
                # Check against known patterns
                for category, patterns in self.category_patterns.items():
                    if any(pattern.lower() in filename for pattern in patterns):
                        detected.add(category)
        
        return sorted(list(detected))
    
    def _analyze_category(self, category):
        """Analyze a single category and return statistics"""
        if not self.stimuli_dir.exists():
            Logger.warning(f"Stimuli directory not found: {self.stimuli_dir}")
            return None
        
        filesizes = []
        brightness_values = []
        
        # Get all image files that match this category's patterns
        image_files = []
        patterns = self.category_patterns.get(category, [category])
        
        for image_path in self.stimuli_dir.glob("*"):
            if (image_path.suffix.lower() in self.supported_formats and 
                image_path.is_file()):
                
                # Check if filename matches any pattern for this category
                filename_lower = image_path.stem.lower()
                if any(pattern.lower() in filename_lower for pattern in patterns):
                    image_files.append(image_path)
        
        if not image_files:
            return None
        
        for image_path in image_files:
            try:
                # Get filesize (complexity measure)
                filesize_kb = image_path.stat().st_size / 1024
                filesizes.append(filesize_kb)
                
                # Calculate brightness
                brightness = self._calculate_brightness(image_path)
                if brightness is not None:
                    brightness_values.append(brightness)
                    
            except Exception as e:
                Logger.warning(f"Error analyzing {image_path}: {e}")
        
        if not filesizes or not brightness_values:
            return None
        
        return {
            'count': len(image_files),
            'filesize': filesizes,
            'brightness': brightness_values
        }
    
    def _calculate_brightness(self, image_path):
        """Calculate average brightness of an image"""
        try:
            with Image.open(image_path) as img:
                # Convert to grayscale for brightness calculation
                if img.mode != 'L':
                    img = img.convert('L')
                
                # Calculate mean brightness (0-255 scale)
                img_array = np.array(img)
                brightness = np.mean(img_array)
                
                return brightness
                
        except Exception as e:
            Logger.warning(f"Error calculating brightness for {image_path}: {e}")
            return None
    
    def _calculate_stats(self, values):
        """Calculate mean, median, and standard deviation"""
        if not values:
            return None
        
        try:
            return {
                'mean': statistics.mean(values),
                'median': statistics.median(values),
                'std': statistics.stdev(values) if len(values) > 1 else 0,
                'min': min(values),
                'max': max(values)
            }
        except Exception as e:
            Logger.warning(f"Error calculating statistics: {e}")
            return None
    
    def _print_category_results(self, category, stats):
        """Print analysis results for a single category"""
        Logger.info(f"\n📁 Category: {category.upper()}")
        Logger.info(f"   Images found: {stats['count']}")
        
        # Filesize statistics
        filesize_stats = self._calculate_stats(stats['filesize'])
        if filesize_stats:
            Logger.info(f"   📊 COMPLEXITY (Filesize in KB):")
            Logger.info(f"      Mean: {filesize_stats['mean']:.2f} KB")
            Logger.info(f"      Median: {filesize_stats['median']:.2f} KB")
            Logger.info(f"      Std Dev: {filesize_stats['std']:.2f} KB")
            Logger.info(f"      Range: {filesize_stats['min']:.2f} - {filesize_stats['max']:.2f} KB")
        
        # Brightness statistics
        brightness_stats = self._calculate_stats(stats['brightness'])
        if brightness_stats:
            Logger.info(f"   💡 BRIGHTNESS (0-255 scale):")
            Logger.info(f"      Mean: {brightness_stats['mean']:.2f}")
            Logger.info(f"      Median: {brightness_stats['median']:.2f}")
            Logger.info(f"      Std Dev: {brightness_stats['std']:.2f}")
            Logger.info(f"      Range: {brightness_stats['min']:.2f} - {brightness_stats['max']:.2f}")
    
    def _print_overall_results(self, overall_stats):
        """Print overall statistics across all categories"""
        Logger.info(f"\n🌍 OVERALL STATISTICS (All Categories)")
        Logger.info(f"   Total images analyzed: {len(overall_stats['filesize'])}")
        
        # Overall filesize statistics
        filesize_stats = self._calculate_stats(overall_stats['filesize'])
        if filesize_stats:
            Logger.info(f"   📊 OVERALL COMPLEXITY (Filesize in KB):")
            Logger.info(f"      Mean: {filesize_stats['mean']:.2f} KB")
            Logger.info(f"      Median: {filesize_stats['median']:.2f} KB")
            Logger.info(f"      Std Dev: {filesize_stats['std']:.2f} KB")
            Logger.info(f"      Range: {filesize_stats['min']:.2f} - {filesize_stats['max']:.2f} KB")
        
        # Overall brightness statistics
        brightness_stats = self._calculate_stats(overall_stats['brightness'])
        if brightness_stats:
            Logger.info(f"   💡 OVERALL BRIGHTNESS (0-255 scale):")
            Logger.info(f"      Mean: {brightness_stats['mean']:.2f}")
            Logger.info(f"      Median: {brightness_stats['median']:.2f}")
            Logger.info(f"      Std Dev: {brightness_stats['std']:.2f}")
            Logger.info(f"      Range: {brightness_stats['min']:.2f} - {brightness_stats['max']:.2f}")
    
    def get_category_stats(self, category):
        """Get statistics for a specific category (for programmatic access)"""
        return self._analyze_category(category)