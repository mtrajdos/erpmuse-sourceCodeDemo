from kivy.config import Config

# Example settings
Config.set('graphics', 'multisampling', '0')  # Disable multisampling for testing
Config.set('graphics', 'width', '800')  # Set window width
Config.set('graphics', 'height', '600')  # Set window height
Config.set('graphics', 'fullscreen', '0')  # Disable fullscreen for testing

# After setting configuration, run the app
from kivy.app import App
from kivy.uix.label import Label

class TestApp(App):
    def build(self):
        return Label(text='Hello, Kivy!')

if __name__ == '__main__':
    TestApp().run()
