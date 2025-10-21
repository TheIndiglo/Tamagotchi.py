#!/usr/bin/python3
# pitamgotchi_sim.py

import sys
import os
import time
import random
from PIL import Image, ImageDraw, ImageFont

# --- Hardware / Simulation Setup ---
try:
    # --- REAL HARDWARE MODE ---
    # Try to import the real Raspberry Pi libraries
    import RPi.GPIO as GPIO
    from waveshare_epd import epd2in13_V4
    
    print("Hardware detected. Running in normal mode.")
    IS_SIMULATION = False

except (ImportError, RuntimeError):
    # --- SIMULATION MODE ---
    # Fallback to mock libraries for PC testing
    print("Hardware not found. Running in SIMULATION MODE.")
    print("Press '1', '2', or '3' then Enter to simulate buttons.")
    IS_SIMULATION = True

    # Mock RPi.GPIO library
    class MockGPIO:
        BCM = "BCM"
        IN = "IN"
        PUD_UP = "PUD_UP"
        LOW = 0
        HIGH = 1
        
        # Store our virtual "pressed" button
        _pressed_key = None

        def setmode(self, *args):
            print("[SIM_GPIO] Set BCM mode")

        def setup(self, *args, **kwargs):
            pin = args[0]
            print(f"[SIM_GPIO] Setup pin {pin} as IN, PULL_UP")

        def input(self, pin):
            # Check if the requested pin matches our virtual "pressed" key
            if self._pressed_key is not None:
                if pin == KEY_1_PIN and self._pressed_key == '1':
                    return self.LOW  # Button 1 pressed
                if pin == KEY_2_PIN and self._pressed_key == '2':
                    return self.LOW  # Button 2 pressed
                if pin == KEY_3_PIN and self._pressed_key == '3':
                    return self.LOW  # Button 3 pressed
            
            return self.HIGH # Not pressed
        
        def cleanup(self):
            print("[SIM_GPIO] Cleanup complete.")
            
        # Helper function for our simulator
        def _get_sim_input(self):
            """
            This is NOT part of the real GPIO library.
            It's a helper to get keyboard input for the sim.
            """
            try:
                # Use a non-blocking read if possible
                # This is a bit complex, so we'll use a simple blocking input()
                # This means the game loop will PAUSE waiting for input.
                # For this game, that's acceptable.
                
                # A better (but more complex) way would be to use threading
                # or a library like 'keyboard'.
                pass
            except ImportError:
                pass
            
            # Simple blocking input
            self._pressed_key = input("Enter button (1, 2, 3) or 't' for tick: ")


    # Mock waveshare_epd library
    class MockEPD:
        def init(self):
            print("[SIM_EPD] Display Initialized")

        def Clear(self, color):
            print("[SIM_EPD] Display Cleared")

        def getbuffer(self, image):
            # Just return the image itself
            return image

        def display(self, image_buffer):
            print("[SIM_EPD] Displaying image in new window...")
            # 'image_buffer' is just the PIL image
            # We will show it on the PC screen
            image_buffer.show()

        def sleep(self):
            print("[SIM_EPD] Display sleeping")

    # Overwrite the real libraries with our mock ones
    GPIO = MockGPIO()
    
    # We need to create a mock 'epd2in13_V4' module
    class MockEPDModule:
        def EPD(self):
            return MockEPD()
            
    epd2in13_V4 = MockEPDModule()


# --- Hardware Pin Definitions (for Waveshare 2.13" V3/V4 HAT) ---
KEY_1_PIN = 5   # "Feed"
KEY_2_PIN = 6   # "Play"
KEY_3_PIN = 13  # "Sleep"
KEY_4_PIN = 19  # "Status" (unused in this simple version)

# --- Game Configuration ---
# We use a shorter tick for simulation to make it easier to test
TICK_INTERVAL_SEC = 10 if not IS_SIMULATION else 5

DEBOUNCE_TIME = 0.2     # Button debounce time

# --- Display Dimensions ---
EPD_WIDTH = 122
EPD_HEIGHT = 250  # Note: Display is rotated in this script

# --- Asset Paths ---
try:
    FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    FONT_LARGE = ImageFont.truetype(FONT_PATH, 24)
    FONT_MEDIUM = ImageFont.truetype(FONT_PATH, 16)
    FONT_SMALL = ImageFont.truetype(FONT_PATH, 12)
except IOError:
    # Fallback for Windows/Mac
    try:
        FONT_PATH = 'cour.ttf' # Courier New
        FONT_LARGE = ImageFont.truetype(FONT_PATH, 24)
        FONT_MEDIUM = ImageFont.truetype(FONT_PATH, 16)
        FONT_SMALL = ImageFont.truetype(FONT_PATH, 12)
    except IOError:
        print("Monospace font not found. Using default.")
        FONT_LARGE = ImageFont.load_default()
        FONT_MEDIUM = ImageFont.load_default()
        FONT_SMALL = ImageFont.load_default()

# --- ASCII Art Sprites (Same as before) ---
SPRITES = {
    "neutral": ("\n (._.) \n ( (\") \n /    \ \n"),
    "happy": ("\n (^_^) \n ( (\") \n /    \ \n"),
    "sad": ("\n (T_T) \n ( (\") \n /    \ \n"),
    "hungry": ("\n (>_<) \n ( (\") \n /    \ \n"),
    "asleep": ("\n (z_z) \n ( (\") \n /    \ \n"),
    "dead": ("\n (x_x) \n ( (\") \n /    \ \n")
}

# --- Pet Class (Same as before, using the re-balanced tick) ---
class PiTamagotchi:
    def __init__(self):
        self.hunger = 50
        self.happiness = 50
        self.age = 0
        self.is_asleep = False
        self.state = "neutral"
        self.last_tick = time.time()

    def update_tick(self):
        if self.state == "dead":
            return
        self.age += 1
        
        if self.is_asleep:
            # Slower decay while asleep (1-in-6 chance per tick)
            if random.randint(1, 6) == 1:
                self.hunger += random.randint(0, 1)
                self.happiness = min(100, self.happiness + 1)
        else:
            # Faster decay while awake (1-in-2 chance per tick)
            if random.randint(1, 2) == 1:
                self.hunger += random.randint(1, 2)
                self.happiness -= random.randint(1, 2)

        self.hunger = max(0, min(100, self.hunger))
        self.happiness = max(0, min(100, self.happiness))
        self.update_state()

    def update_state(self):
        if self.is_asleep:
            self.state = "asleep"
        elif self.hunger > 85 or self.happiness < 15:
            self.state = "dead"
        elif self.hunger > 70:
            self.state = "hungry"
        elif self.happiness < 30:
            self.state = "sad"
        elif self.happiness > 80:
            self.state = "happy"
        else:
            self.state = "neutral"

    def feed(self):
        if self.is_asleep or self.state == "dead": return False
        self.hunger = max(0, self.hunger - 25)
        self.happiness = min(100, self.happiness + 5)
        self.update_state()
        return True

    def play(self):
        if self.is_asleep or self.state == "dead": return False
        self.happiness = min(100, self.happiness + 20)
        self.hunger = min(100, self.hunger + 10)
        self.update_state()
        return True

    def toggle_sleep(self):
        if self.state == "dead": return False
        self.is_asleep = not self.is_asleep
        self.update_state()
        return True

    def get_sprite(self):
        return SPRITES.get(self.state, SPRITES["neutral"])

# --- GPIO Setup (Same as before) ---
def setup_buttons():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(KEY_1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_4_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# --- Drawing Function (Same as before) ---
def draw_display(epd, pet, message=""):
    image = Image.new('1', (EPD_HEIGHT, EPD_WIDTH), 255) # 255 = White
    draw = ImageDraw.Draw(image)
    
    sprite = pet.get_sprite()
    draw.text((30, 20), sprite, font=FONT_LARGE, fill=0) # 0 = Black

    if pet.state != "dead":
        draw.text((10, 130), f"Hunger: {pet.hunger}/100", font=FONT_MEDIUM, fill=0)
        draw.text((10, 150), f"Happy:  {pet.happiness}/100", font=FONT_MEDIUM, fill=0)
        draw.text((10, 170), f"Age: {pet.age}", font=FONT_MEDIUM, fill=0)
    else:
        draw.text((30, 140), "GAME OVER", font=FONT_LARGE, fill=0)

    draw.text((160, 20), "Feed (1)", font=FONT_SMALL, fill=0)
    draw.text((160, 40), "Play (2)", font=FONT_SMALL, fill=0)
    draw.text((160, 60), "Sleep (3)", font=FONT_SMALL, fill=0)

    if message:
        draw.text((10, 200), message, font=FONT_MEDIUM, fill=0)

    # In sim mode, this calls MockEPD.display()
    # In hardware mode, this calls real epd.display()
    epd.display(epd.getbuffer(image))

# --- Main Game Loop (MODIFIED for Sim) ---
def main():
    epd = None
    try:
        print("Initializing PiTamagotchi...")
        epd = epd2in13_V4.EPD()
        epd.init()
        epd.Clear(0xFF)
        
        setup_buttons()
        pet = PiTamagotchi()
        
        message = "Hello!"
        last_button_press = time.time()
        needs_draw = True

        while True:
            current_time = time.time()
            action_taken = False
            
            # --- 1. Get Simulated Input (if in sim mode) ---
            if IS_SIMULATION:
                GPIO._get_sim_input()
                if GPIO._pressed_key == 't':
                    # Special sim command: force a game tick
                    print("[SIM] Forcing game tick...")
                    pet.update_tick()
                    pet.last_tick = current_time
                    message = "Tick!"
                    needs_draw = True
                    GPIO._pressed_key = None # Clear key
            
            # --- 2. Check for Game Tick ---
            if current_time - pet.last_tick > TICK_INTERVAL_SEC:
                pet.update_tick()
                pet.last_tick = current_time
                if pet.state != "asleep":
                    message = "Time passes..."
                needs_draw = True

            # --- 3. Check for Input (Polling) ---
            if current_time - last_button_press > DEBOUNCE_TIME:
                if GPIO.input(KEY_1_PIN) == GPIO.LOW: # Feed
                    if pet.feed():
                        message = "Yum!"
                        action_taken = True
                    last_button_press = current_time
                
                elif GPIO.input(KEY_2_PIN) == GPIO.LOW: # Play
                    if pet.play():
                        message = "Whee!"
                        action_taken = True
                    last_button_press = current_time

                elif GPIO.input(KEY_3_PIN) == GPIO.LOW: # Sleep
                    if pet.toggle_sleep():
                        message = "Zzz..." if pet.is_asleep else "I'm awake!"
                        action_taken = True
                    last_button_press = current_time

            if action_taken:
                needs_draw = True
                
            # --- 4. Clear Sim Input ---
            if IS_SIMULATION:
                GPIO._pressed_key = None # Clear the key press

            # --- 5. Update Display (if needed) ---
            if needs_draw:
                print(f"Drawing... (State: {pet.state}, Msg: {message})")
                draw_display(epd, pet, message)
                
                # In sim mode, don't pause with time.sleep()
                # because the e-ink window is fast.
                if action_taken and not IS_SIMULATION:
                    time.sleep(2.0)
                    message = ""
                    draw_display(epd, pet, message)
                
                needs_draw = False
                message = ""
            
            # Prevent busy-looping on hardware
            if not IS_SIMULATION:
                time.sleep(0.05)

    except IOError as e:
        print(e)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        if epd:
            print("Cleaning up...")
            if not IS_SIMULATION:
                epd.Clear(0xFF)
                epd.sleep()
        GPIO.cleanup()
        print("Goodbye!")

if __name__ == '__main__':
    main()