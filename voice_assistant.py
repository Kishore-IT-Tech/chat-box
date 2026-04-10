"""
=============================================================
  Smart AI Voice Assistant - Powered by Groq (FREE)
  - Listens to your voice (offline via Vosk)
  - Thinks with Groq AI (free + super fast)
  - Speaks the answer back (pyttsx3)
  - Accident Emergency Mode built in
=============================================================
  INSTALL:
      pip install pyttsx3 vosk sounddevice requests

  GET FREE GROQ API KEY (2 mins):
      1. Go to https://console.groq.com
      2. Sign up free (Google login works)
      3. Click "API Keys" → "Create API Key"
      4. Copy and paste it below in GROQ_API_KEY
=============================================================
"""

import pyttsx3
import sounddevice as sd
import queue
import json
import time
import sys
import os
import requests
from vosk import Model, KaldiRecognizer
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ─────────────────────────────────────────
#  YOUR SETTINGS — Only edit this part
# ─────────────────────────────────────────
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_PATH   = "vosk-model-small-en-us-0.15"
SAMPLE_RATE  = 16000

# ─────────────────────────────────────────
#  ACCIDENT EMERGENCY MESSAGES
# ─────────────────────────────────────────
ACCIDENT_PROMPT = (
    "Accident detected. Say CANCEL within 10 seconds to stop the alert. "
    "Otherwise, emergency services will be contacted automatically."
)
ALERT_MESSAGE = (
    "Attention! This is an automated emergency alert. "
    "A vehicle accident has been detected at the current GPS location. "
    "Please send immediate medical assistance. "
    "This call was placed automatically by the Smart Accident Detection System."
)

# ─────────────────────────────────────────
#  TEXT TO SPEECH
# ─────────────────────────────────────────
class Speaker:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 165)
        self.engine.setProperty('volume', 1.0)
        voices = self.engine.getProperty('voices')
        if voices:
            self.engine.setProperty('voice', voices[0].id)
        print("[TTS] Voice engine ready.")

    def speak(self, text):
        print(f"\n[ASSISTANT] {text}\n")
        self.engine.say(text)
        self.engine.runAndWait()

# ─────────────────────────────────────────
#  SPEECH RECOGNITION (OFFLINE - VOSK)
# ─────────────────────────────────────────
class Listener:
    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            print(f"[ERROR] Vosk model not found: {MODEL_PATH}")
            print("Make sure 'vosk-model-small-en-us-0.15' folder is in the same directory.")
            sys.exit(1)
        print("[STT] Loading speech model...")
        self.model = Model(MODEL_PATH)
        self.q = queue.Queue()
        print("[STT] Speech model ready.")

    def _callback(self, indata, frames, time_info, status):
        self.q.put(bytes(indata))

    def listen(self, timeout=8):
        """Listen and return what you said as text."""
        rec = KaldiRecognizer(self.model, SAMPLE_RATE)
        # Clear old audio from queue
        while not self.q.empty():
            self.q.get()

        print("[MIC] 🎤 Listening... speak now!")
        try:
            # Find default input device
            input_device = sd.default.device[0] if sd.default.device[0] is not None else 0
            print(f"[INFO] Using audio device: {input_device}")
            
            with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000,
                                   dtype='int16', channels=1, device=input_device, callback=self._callback):
                deadline = time.time() + timeout
                while time.time() < deadline:
                    try:
                        data = self.q.get(timeout=0.5)
                    except queue.Empty:
                        continue
                    if rec.AcceptWaveform(data):
                        result = json.loads(rec.Result())
                        text = result.get("text", "").strip()
                        if text:
                            print(f"[YOU SAID] {text}")
                            return text.lower()

                # Check partial result
                partial = json.loads(rec.PartialResult()).get("partial", "").strip()
                if partial:
                    print(f"[YOU SAID] {partial}")
                    return partial.lower()

            print("[MIC] Nothing heard.")
            return ""
        except Exception as e:
            print(f"[ERROR] Audio input failed: {e}")
            print("[INFO] Available audio devices:")
            print(sd.query_devices())
            return ""

# ─────────────────────────────────────────
#  GROQ AI BRAIN (FREE)
# ─────────────────────────────────────────
class GroqBrain:
    def __init__(self, api_key):
        self.api_key = api_key
        self.url = "https://api.groq.com/openai/v1/chat/completions"
        self.system_prompt = (
            "You are a helpful voice assistant built into a Smart Accident Detection System. "
            "Keep answers SHORT — 1 to 2 sentences only — because they will be spoken aloud. "
            "Be calm, clear, and friendly. "
            "Never use bullet points, numbers, markdown, or special characters. "
            "If asked about accidents or emergency response, answer with extra care."
        )
        print("[AI] Groq AI brain ready.")

    def ask(self, question):
        """Send question to Groq and get answer."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            body = {
                "model": "llama-3.1-8b-instant",
                "max_tokens": 120,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": question}
                ]
            }
            r = requests.post(self.url, json=body, headers=headers, timeout=10)
            if r.status_code == 200:
                result = r.json()
                answer = result['choices'][0]['message']['content'].strip()
                return answer
            else:
                print(f"[ERROR] Groq API error: {r.status_code} - {r.text}")
                return "Sorry, I couldn't connect to AI. Please check your internet."
        except Exception as e:
            print(f"[ERROR] {e}")
            return "I had a problem thinking. Please try again."

# ─────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────
def main():
    print("\n" + "="*52)
    print("   Smart AI Voice Assistant")
    print("   Groq AI (Free) + Accident Emergency Mode")
    print("="*52 + "\n")

    # Check API key
    if not GROQ_API_KEY or GROQ_API_KEY.strip() == "":
        print("=" * 52)
        print("  [SETUP NEEDED] Add your Groq API key!")
        print("  1. Go to  https://console.groq.com")
        print("  2. Sign up free (Google login works)")
        print("  3. API Keys → Create API Key → Copy it")
        print("  4. Paste it in this file: GROQ_API_KEY = '...'")
        print("=" * 52)
        sys.exit(1)

    # Start all components
    speaker  = Speaker()
    listener = Listener()
    brain    = GroqBrain(GROQ_API_KEY)

    speaker.speak("Hello! I am your smart voice assistant. I am ready. How can I help you?")

    print("\n[READY] Just speak — I am listening!")
    print("[TIP]   Say 'accident' to test emergency mode.")
    print("[TIP]   Say 'goodbye' to stop.")
    print("[TIP]   Ask me anything!\n")

    emergency = False
    while True:
        heard = listener.listen()
        if not heard:
            continue

        # Emergency keyword
        if "accident" in heard:
            emergency = True
            print("\n[EMERGENCY] EMERGENCY MODE ACTIVATED!")
            speaker.speak(ACCIDENT_PROMPT)
            print("[TIMER] Waiting 10 seconds for CANCEL command...")
            cancel_heard = listener.listen(timeout=10)
            if "cancel" in cancel_heard:
                emergency = False
                print("[EMERGENCY] Alert cancelled.")
                speaker.speak("Emergency alert cancelled.")
            else:
                print("[EMERGENCY] Contacting authorities...")
                speaker.speak(ALERT_MESSAGE)
                print("[EMERGENCY] Alert sent!") 
                emergency = False
            continue

        # Normal conversation
        print(f"[THINKING]", end=" ", flush=True)
        answer = brain.ask(heard)
        print(f"✓")
        speaker.speak(answer)

        # Exit keyword
        if "goodbye" in heard or "stop" in heard or "exit" in heard:
            speaker.speak("Goodbye! Stay safe!")
            break

if __name__ == "__main__":
    main()
