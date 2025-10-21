#!/usr/bin/python3
# pitamagotchi.py

# _____________________ Make sure to make this file executable: sudo chmod +x tamagotchi.py _____________________
# _____________________ To run file: ./tamagotchi.py    alternative: navigate to directory location and type "python3 tamagotchi.py" no quotes

# _____________________ TICK_TIME was 60 seconds, I thought this was too slow, so updated to 10 and stats adjusted, can be changed if desired _____________________

import sys
import os
import time
import random
import RPi.GPIO as GPIO

# Display imports
from waveshare_epd import epd2in13_v4
from PIL import Image, ImageDraw, ImageFont

# Display Pin Definitions
KEY_1_PIN = 5   # Feed
KEY_2_PIN = 6   # Play
KEY_3_PIN = 13  # Sleep
KEY_4_PIN = 19  # Status?

# _____________________ Game Config _____________________
TICK_INTERVAL_SEC = 10  # Pet update time, may need adjustment based on display
DEBOUNCE_TIME = 0.2     # For buttons

# _____________________ Display Dimensions _____________________
EPD_WIDTH = 122
EPD_HEIGHT = 250    # May need to be rotated

# _____________________ Asset Paths _____________________
# Need to have DejaVuSans font
# On RasPi: /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf
# Apparently monospace font is better for sprites

try:
    FONT_PATH = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    FONT_LARGE = ImageFont.truetype(FONT_PATH, 24)
    FONT_MEDIUM = ImageFont.truetype(FONT_PATH, 16)
    FONT_SMALL = ImageFont.truetype(FONT_PATH, 12)
except IOError:
    print("Font not found, using default.")
    FONT_LARGE = ImageFont.load_default()
    FONT_MEDIUM = ImageFont.load_default()
    FONT_SMALL = ImageFont.load_default()

# _____________________ ASCII art sprites (Cranberry) _____________________
SPRITES = {
    "neutral": (
        "\n"
        " (._.) \n"
        " ( (\") \n"
        " /    \ \n"
    ),
    "happy": (
        "\n"
        " (^_^) \n"
        " ( (\") \n"
        " /    \ \n"
    ),
    "sad": (
        "\n"
        " (T_T) \n"
        " ( (\") \n"
        " /    \ \n"
    ),
    "hungry": (
        "\n"
        " (>_<) \n"
        " ( (\") \n"
        " /    \ \n"
    ),
    "asleep": (
        "\n"
        " (z_z) \n"
        " ( (\") \n"
        " /    \ \n"
    ),
    "dead": (
        "\n"
        " (x_x) \n"
        " ( (\") \n"
        " /    \ \n"
    )
}

# _____________________ Pet Class _____________________
class PiTamagotchi:
    def __init__(self):
        self.hunger = 50
        self.happiness = 50
        self.age = 0
        self.is_asleep = False
        self.state = "neutral"      # 'neutral', 'happy', 'sad', 'hungry', 'asleep', 'dead'
        self.last_tick = time.time()

    def update_tick(self):
        """Called every TICK_INTERVAL to update pet stats."""
        if self.state == "dead":
            return

        # We still age every tick
        self.age += 1
        
        if self.is_asleep:
            # While asleep, stats change very slowly
            # This runs every 10 sec, so let's make it a 1-in-6 chance
            if random.randint(1, 6) == 1:
                self.hunger += random.randint(0, 1)
                self.happiness = min(100, self.happiness + 1) # Rest
        else:
            # While awake, stats decay faster
            # This runs every 10 sec, so a 1-in-2 chance
            # This makes it decay ~3x faster
            if random.randint(1, 2) == 1:
                self.hunger += random.randint(1, 2) # Reduced from (1, 3)
                self.happiness -= random.randint(1, 2) # Kept the same

        # Clamp values
        self.hunger = max(0, min(100, self.hunger))
        self.happiness = max(0, min(100, self.happiness))

        self.update_state()

    def update_state(self):
        """Update emotional state based off stats"""
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
        if self.is_asleep or self.state == "dead":
            return False
        self.hunger -= 25
        self.happiness += 5
        self.hunger = max(0, min(100, self.hunger))
        self.happiness = max(0, min(100, self.happiness))
        self.update_state()
        return True
    
    def play(self):
        if self.is_asleep or self.state == "dead":
            return False
        self.happiness += 20
        self.hunger += 10   # Playing should speed up hunger
        self.hunger = max(0, min(100, self.hunger))
        self.happiness = max(0, min(100, self.happiness))
        self.update_state()
        return True
    
    def toggle_sleep(self):
        if self.state == "dead":
            return False
        self.is_asleep = not self.is_asleep
        self.update_state()
        return True
    
    def get_sprite(self):
        return SPRITES.get(self.state, SPRITES["neutral"])
    
# _____________________ GPIO setup _____________________
def setup_buttons():
    GPIO.setmode(GPIO.BCM)
    # Setup buttons as inputs (pull-up), button press connects pin to GND
    GPIO.setup(KEY_1_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_2_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_3_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.setup(KEY_4_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# _____________________ Drawing function _____________________
def draw_display(epd, pet, message=""):
    """Draw the current game state to the e-Paper display."""
    
    # Create a new blank image. '1' means 1-bit color (black/white)
    # Using a 250x122 display in portrait mode
    image = Image.new('1', (EPD_HEIGHT, EPD_WIDTH), 255) # 255 = White
    draw = ImageDraw.Draw(image)

    # Draw the Pet Sprite
    sprite = pet.get_sprite()
    draw.text((30, 20), sprite, font=FONT_LARGE, fill=0) # 0 = Black

    # Draw Stats
    if pet.state != "dead":
        draw.text((10, 130), f"Hunger: {pet.hunger}/100", font=FONT_MEDIUM, fill=0)
        draw.text((10, 150), f"Happy:  {pet.happiness}/100", font=FONT_MEDIUM, fill=0)
        draw.text((10, 170), f"Age: {pet.age}", font=FONT_MEDIUM, fill=0)
    else:
        # Game Over
        draw.text((30, 140), "GAME OVER", font=FONT_LARGE, fill=0)

    # Draw Button Labels
    draw.text((160, 20), "Feed (1)", font=FONT_SMALL, fill=0)
    draw.text((160, 40), "Play (2)", font=FONT_SMALL, fill=0)
    draw.text((160, 60), "Sleep (3)", font=FONT_SMALL, fill=0)

    # Draw the one-time message
    if message:
        draw.text((10, 200), message, font=FONT_MEDIUM, fill=0)

    # Send the image to the display
    # The EPD library handles rotation
    epd.display(epd.getbuffer(image))

# _____________________It's (main) loopin' time _____________________
def main():
    epd = None
    try:
        # Init
        print("Initializing PiTamagotchi...")
        epd = epd2in13_V4.EPD()
        epd.init()
        epd.Clear(0xFF)     # Clears screen to white

        setup_buttons()
        pet = PiTamagotchi()

        message = "Hello Traveler!"
        last_button_press = time.time()
        needs_draw = True

        # Game Loop
        while True:
            current_time = time.time()
            action_taken = False

            # 1: Check for game tick
            if current_time - pet.last_tick > TICK_INTERVAL_SEC:
                pet.update_tick()
                pet.last_tick = current_time
                if pet.state != "asleep":
                    message = "Time passes..."
                needs_draw = True

            # 2: Check for Input (Polling)
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

            # 3: Update Display (may be needed)
            if needs_draw:
                if pet.state == "dead" and not action_taken:
                    # If dead, don't keep redrawing
                    time.sleep(1.0)
                    continue

                print(f"Drawing... (State: {pet.state}, Msg: {message})")
                draw_display(epd, pet, message)
                print("...Draw complete.")
                
                # If the update was from an action, hold the message
                if action_taken:
                    time.sleep(2.0) # E-Ink is slow
                    message = "" # Clear the one-time message
                    draw_display(epd, pet, message) # Redraw without message
                
                needs_draw = False
                message = "" # Clear message after it's been shown

            # Prevent busy-looping
            time.sleep(0.05) 

    except IOError as e:
        print(e)
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        # --- Cleanup ---
        if epd:
            print("Clearing display and sleeping...")
            epd.Clear(0xFF)
            epd.sleep()
        GPIO.cleanup()
        print("Goodbye!")

if __name__ == '__main__':
    main()