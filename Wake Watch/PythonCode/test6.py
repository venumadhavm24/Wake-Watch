import pygame
import serial
import time
import dlib
import cv2
import requests
from pygame import mixer
from scipy.spatial import distance
from imutils import face_utils
from twilio.rest import Client  # Twilio for SMS

# Twilio Configuration (Use your credentials)
TWILIO_SID = ""
TWILIO_AUTH_TOKEN = ""
TWILIO_PHONE_NUMBER = "+17752389331"
EMERGENCY_CONTACT = "+919912329444"  # Change this to your number

# Initialize alarm sound
def initialize_alarm(sound_file):
    """Initialize the alarm sound."""
    try:
        mixer.init()
        mixer.music.load(sound_file)
        print(f"Sound file '{sound_file}' loaded successfully.")
    except Exception as e:
        print(f"Error initializing sound: {e}")

# Play alarm sound
def play_alarm():
    """Play the alarm sound."""
    try:
        mixer.music.play()
        print("Alarm playing...")
    except Exception as e:
        print(f"Error playing sound: {e}")

# Calculate Eye Aspect Ratio (EAR)
def calculate_ear(eye):
    """Calculate Eye Aspect Ratio (EAR)."""
    A = distance.euclidean(eye[1], eye[5])
    B = distance.euclidean(eye[2], eye[4])
    C = distance.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    return ear

# Get approximate GPS location (without GPS module)
def get_location():
    """Fetch approximate location using IP-based geolocation."""
    try:
        response = requests.get("http://ip-api.com/json/")
        data = response.json()

        if data["status"] == "success":
            lat = data["lat"]
            lon = data["lon"]
            maps_link = f"https://www.google.com/maps?q={lat},{lon}"

            print(f"Latitude: {lat}, Longitude: {lon}")
            print(f"Google Maps Link: {maps_link}")
            return maps_link
        else:
            print("Could not retrieve location.")
            return None
    except Exception as e:
        print(f"Error fetching location: {e}")
        return None

# Send SMS alert with GPS location
def send_sms(message):
    """Send an SMS using Twilio."""
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=EMERGENCY_CONTACT
        )
        print(f"SMS sent successfully: {message.sid}")
    except Exception as e:
        print(f"Error sending SMS: {e}")

# Process frame to detect drowsiness
def process_frame(frame, detector, predictor, l_start, l_end, r_start, r_end, thresh):
    """Detect drowsiness from a video frame."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    subjects = detector(gray, 0)
    
    for subject in subjects:
        shape = predictor(gray, subject)
        shape = face_utils.shape_to_np(shape)

        left_eye = shape[l_start:l_end]
        right_eye = shape[r_start:r_end]
        left_ear = calculate_ear(left_eye)
        right_ear = calculate_ear(right_eye)
        ear = (left_ear + right_ear) / 2.0

        print(f"EAR: {ear}")  # Debug EAR value
        
        # Draw eye contours
        left_eye_hull = cv2.convexHull(left_eye)
        right_eye_hull = cv2.convexHull(right_eye)
        cv2.drawContours(frame, [left_eye_hull], -1, (0, 255, 0), 1)
        cv2.drawContours(frame, [right_eye_hull], -1, (0, 255, 0), 1)

        if ear < thresh:
            return True, frame  # Drowsiness detected
            
    return False, frame  # No drowsiness detected

def main():
    # Configuration
    config = {
        'sound_file': "videoddd.wav",  # Ensure the file is present in the same directory
        'model_path': "shape_predictor_68_face_landmarks.dat",
        'arduino_port': 'COM3',  # Change based on your system
        'thresh': 0.25,  # EAR threshold for drowsiness
        'frame_check': 20,  # Number of frames required for confirmation
    }

    # Initialize alarm sound
    initialize_alarm(config['sound_file'])

    # Load face detector & shape predictor
    detector = dlib.get_frontal_face_detector()
    try:
        predictor = dlib.shape_predictor(config['model_path'])
    except RuntimeError as e:
        print(f"Error loading model: {e}")
        return

    (l_start, l_end) = face_utils.FACIAL_LANDMARKS_68_IDXS["left_eye"]
    (r_start, r_end) = face_utils.FACIAL_LANDMARKS_68_IDXS["right_eye"]

    # Connect to Arduino via Serial
    try:
        arduino = serial.Serial(config['arduino_port'], 9600, timeout=1)
        time.sleep(2)  # Allow time for Arduino to initialize
        print("Attempting to start motor...")
        arduino.write(b'0\n')  # Send command to start motor immediately
        time.sleep(2)  # Give it time to start
        print("Motor started at full speed")
    except serial.SerialException as e:
        print(f"Error connecting to Arduino: {e}")
        return

    cap = cv2.VideoCapture(0)  # Use default webcam
    
    if not cap.isOpened():
        print("Error: Could not open video.")
        return

    flag = 0
    while True:
        ret, frame = cap.read()
        
        if not ret:
            print("Error: Could not read frame.")
            break
        
        frame = cv2.resize(frame, (450, 300))
        
        drowsy, processed_frame = process_frame(frame, detector, predictor,
                                                l_start, l_end,
                                                r_start, r_end,
                                                config['thresh'])
        
        if drowsy:
            flag += 1
            if flag >= config['frame_check']:
                print("Drowsiness detected!")
                play_alarm()  # Play sound
                arduino.write(b'1\n')  # Send command to stop motor and blink LED
                
                time.sleep(0.75)  # Let the motor stop and LED blink for a while
                arduino.write(b'0\n')  # Stop blinking LED and motor
                arduino.write(b'1\n')
                maps_link = get_location()
                if maps_link:
                    send_sms(f"Drowsiness Alert! Location: {maps_link}")
        else:
            flag = 0
            arduino.write(b'0\n')  # Keep motor running

        cv2.imshow("Frame", processed_frame)

        # Exit on 'q' key press
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    # Cleanup
    cap.release()
    cv2.destroyAllWindows()
    arduino.write(b'0\n')  # Stop the motor when program ends
    arduino.close()
# "ACfe13402f685ae91326f77c098bc55df5"
# "0908ede318959f00f5f84293b3db8cc6"
if __name__ == "__main__":
    main()
