"""
=============================================================
  ADVANCED Smart AI Voice Assistant v3.0
  - Voice + Typing input
  - Say "option one" → Emergency Call 108
  - Say "option two" → Cancel Alert
  - Smart keywords with sequential actions
  - English + Tamil support
  - Groq AI for real conversations
  - Better voice recognition (Google Speech)
=============================================================
  INSTALL (inside .venv):
      pip install SpeechRecognition pyaudio pyttsx3 requests
=============================================================
"""

import speech_recognition as sr
import pyttsx3
import requests
import time
import sys
import threading
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────
#  SETTINGS
# ─────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
LANGUAGE     = "en-IN"
GPS_LOCATION = "13.0827 N, 80.2707 E, Chennai, Tamil Nadu"

# ─────────────────────────────────────────
#  MENU OPTIONS (spoken or typed)
# ─────────────────────────────────────────
MENU = """
╔══════════════════════════════════════════╗
║      SMART ACCIDENT VOICE ASSISTANT      ║
╠══════════════════════════════════════════╣
║  Say or Type:                            ║
║  "option one"   → 🚨 Emergency Call 108  ║
║  "option two"   → ❌ Cancel Alert        ║
║  "where"        → 📍 Get Location        ║
║  "injured"      → 🤕 Injury Help         ║
║  "accident"     → 🚗 Accident Mode       ║
║  "help"         → 🆘 Call for Help       ║
║  "goodbye"      → 👋 Exit                ║
║  Anything else  → 🤖 AI answers you      ║
╚══════════════════════════════════════════╝
"""

# ─────────────────────────────────────────
#  SCRIPTS
# ─────────────────────────────────────────
ACCIDENT_WARNING = (
    "Accident detected. "
    "Say or type option one to call emergency services. "
    "Say or type option two to cancel this alert. "
    "You have 10 seconds."
)

OPERATOR_108_SCRIPT = [
    "Hello. This is an automated emergency alert from a Smart Accident Detection System.",
    f"A road accident has been detected at the following location: {GPS_LOCATION}.",
    "The vehicle sensors have confirmed a collision event.",
    "Immediate medical assistance is required at this location.",
    "Please dispatch an ambulance to the mentioned GPS coordinates immediately.",
    f"Repeating location: {GPS_LOCATION}. Please send help immediately."
]

LOCATION_RESPONSE  = f"The current accident location is {GPS_LOCATION}. This has been sent to emergency services."
INJURED_RESPONSE   = "Injury reported. Please stay calm and do not move. Emergency services have been informed. Help is on the way."
CANCEL_RESPONSE    = "Alert cancelled. No emergency services will be contacted. System is back to normal monitoring. Stay safe."
CALL_CONFIRMED     = "Confirmed. Connecting to 108 emergency services now. Please stay on the line."

# ─────────────────────────────────────────
#  SPEAKER
# ─────────────────────────────────────────
def speak(text, rate=155):
    print(f"\n🤖 [ASSISTANT] {text}\n")
    try:
        eng = pyttsx3.init()
        eng.setProperty('rate', rate)
        eng.setProperty('volume', 1.0)
        voices = eng.getProperty('voices')
        if voices:
            eng.setProperty('voice', voices[0].id)
        eng.say(text)
        eng.runAndWait()
        eng.stop()
        del eng
    except Exception as e:
        print(f"[TTS ERROR] {e}")
    time.sleep(0.3)

def speak_slow(text):
    speak(text, rate=130)

# ─────────────────────────────────────────
#  LISTENER (Google Speech — better accuracy)
# ─────────────────────────────────────────
recognizer = sr.Recognizer()
recognizer.energy_threshold       = 250   # Lower = more sensitive mic
recognizer.pause_threshold        = 0.8   # Pause between words
recognizer.dynamic_energy_threshold = True

def listen_voice(timeout=8):
    """Listen via microphone and return text."""
    try:
        with sr.Microphone() as source:
            print("\n🎤 [MIC] Adjusting for background noise...")
            recognizer.adjust_for_ambient_noise(source, duration=0.8)
            print("🎤 [MIC] Listening... speak clearly now!")
            audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=12)

        # Google Speech Recognition — best for Indian English
        text = recognizer.recognize_google(audio, language=LANGUAGE)
        print(f"🎤 [YOU SAID] {text}")
        return text.lower()

    except sr.WaitTimeoutError:
        print("🎤 [MIC] No voice detected.")
        return ""
    except sr.UnknownValueError:
        print("🎤 [MIC] Could not understand. Please speak clearly.")
        return ""
    except sr.RequestError:
        print("🎤 [MIC] Internet error for speech recognition.")
        return ""
    except Exception as e:
        print(f"🎤 [MIC ERROR] {e}")
        return ""

def get_input(prompt="", timeout=8):
    """
    Get input from BOTH voice and typing simultaneously.
    Whichever comes first wins.
    """
    print(f"\n{'─'*45}")
    print("🎤 SPEAK  or  ⌨️  TYPE your response below:")
    print(f"{'─'*45}")

    result = {"text": ""}
    voice_done = threading.Event()

    def voice_thread():
        heard = listen_voice(timeout=timeout)
        if heard and not voice_done.is_set():
            result["text"] = heard
            voice_done.set()

    # Start voice listener in background
    t = threading.Thread(target=voice_thread, daemon=True)
    t.start()

    # Meanwhile allow typing
    try:
        typed = input("⌨️  Type here (or wait to speak): ").strip().lower()
        if typed:
            result["text"] = typed
            voice_done.set()
    except EOFError:
        pass

    voice_done.wait(timeout=timeout + 2)

    if result["text"]:
        print(f"✅ [INPUT] {result['text']}")
    return result["text"]

# ─────────────────────────────────────────
#  GROQ AI
# ─────────────────────────────────────────
def ask_groq(question):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 100,
            "messages": [
                {"role": "system", "content": (
                    "You are a voice assistant inside a Smart Accident Detection vehicle system. "
                    "Answer in 1 to 2 short sentences only. Be calm and reassuring. "
                    "Never use bullet points, numbers, or special characters."
                )},
                {"role": "user", "content": question}
            ]
        }
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers, json=body, timeout=10
        )
        data = r.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"].strip()
        return "I am here to help. Please stay calm."
    except requests.exceptions.ConnectionError:
        return "No internet connection detected."
    except Exception as e:
        print(f"[AI ERROR] {e}")
        return "I am here to help you."

# ─────────────────────────────────────────
#  KEYWORD DETECTOR
# ─────────────────────────────────────────
def detect_action(text):
    text = text.lower()

    # ── OPTION ONE → Emergency ──
    if any(p in text for p in ["option one", "option 1", "one", "call emergency", "call 108"]):
        return "OPTION_ONE"

    # ── OPTION TWO → Cancel ──
    if any(p in text for p in ["option two", "option 2", "two", "cancel", "stop", "false alarm"]):
        return "OPTION_TWO"

    # ── Other keywords ──
    if any(w in text for w in ["accident", "crash", "emergency", "help me", "help"]):
        return "EMERGENCY"
    if any(w in text for w in ["where", "location", "address", "gps"]):
        return "LOCATION"
    if any(w in text for w in ["injured", "bleeding", "pain", "hurt", "unconscious"]):
        return "INJURED"
    if any(w in text for w in ["ambulance", "108"]):
        return "CALL_108"

    return "AI"

# ─────────────────────────────────────────
#  SEQUENTIAL ACTIONS
# ─────────────────────────────────────────
def action_emergency():
    """Full sequential emergency flow."""
    print("\n" + "🚨" * 22)
    print("   EMERGENCY MODE — ACCIDENT DETECTED")
    print("🚨" * 22)

    # Warn occupants + show options
    speak(ACCIDENT_WARNING)

    # Wait for option one or two
    response = get_input(timeout=10)
    action   = detect_action(response)

    if action == "OPTION_TWO":
        action_cancel()
        return

    # Default → option one (emergency call)
    action_call_108()

def action_call_108():
    """Trigger 108 emergency call sequence."""
    speak(CALL_CONFIRMED)
    time.sleep(1)

    print("\n📞 [CALLING 108] Emergency call active...\n")
    speak("Emergency call to 108 is now active. Speaking to operator.")
    time.sleep(0.5)

    for line in OPERATOR_108_SCRIPT:
        speak_slow(line)
        time.sleep(0.6)

    speak("Emergency information has been transmitted. Help is on the way. Please stay calm.")
    print("\n✅ [108 CALL] Complete.")

def action_location():
    speak(LOCATION_RESPONSE)

def action_injured():
    speak(INJURED_RESPONSE)
    speak("Can you tell me where you feel pain? Speak or type your answer.")
    details = get_input(timeout=8)
    if details:
        advice = ask_groq(f"Person in accident says: {details}. Give 1 sentence first aid advice.")
        speak(advice)

def action_cancel():
    speak(CANCEL_RESPONSE)
    print("✅ [ACTION] Alert cancelled.")

def action_option_one():
    speak("Option one selected. Calling emergency services now.")
    action_call_108()

def action_option_two():
    speak("Option two selected. Cancelling alert.")
    action_cancel()

# ─────────────────────────────────────────
#  ACTION ROUTER
# ─────────────────────────────────────────
def route(action, text=""):
    if action == "OPTION_ONE":   action_option_one()
    elif action == "OPTION_TWO": action_option_two()
    elif action == "EMERGENCY":  action_emergency()
    elif action == "CALL_108":   action_call_108()
    elif action == "LOCATION":   action_location()
    elif action == "INJURED":    action_injured()
    elif action == "AI":
        print("🤖 [THINKING] Asking Groq AI...")
        answer = ask_groq(text)
        speak(answer)

# ─────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────
def main():
    print(MENU)
    speak(
        "Hello! Advanced Smart Voice Assistant version 3 is ready. "
        "You can speak or type your command. "
        "Say option one for emergency, or option two to cancel."
    )

    try:
        while True:
            text = get_input(timeout=10)

            if not text:
                continue

            if any(w in text for w in ["goodbye", "bye", "exit", "quit"]):
                speak("Goodbye! Drive safe and stay alert.")
                break

            action = detect_action(text)
            route(action, text)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopped.")
        speak("System shutting down. Goodbye!")

if __name__ == "__main__":
    main()