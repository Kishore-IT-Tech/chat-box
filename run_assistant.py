import sounddevice as sd
import queue
import json
import time
import sys
import os
import requests
import subprocess
from vosk import Model, KaldiRecognizer

GROQ_API_KEY = ""  # Add your Groq API key here
MODEL_PATH   = "vosk-model-small-en-us-0.15"
SAMPLE_RATE  = 16000

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

# ── SPEAKER — reinit every call to avoid pyttsx3 freeze ──
def speak(text):
    import pyttsx3
    print(f"\n[ASSISTANT] {text}\n")
    try:
        eng = pyttsx3.init()
        eng.setProperty('rate', 155)
        eng.setProperty('volume', 1.0)
        eng.say(text)
        eng.runAndWait()
        eng.stop()
        del eng
    except Exception as e:
        print(f"[TTS ERROR] {e}")
    time.sleep(0.4)

# ── LISTENER ──
audio_q = queue.Queue()

def audio_callback(indata, frames, time_info, status):
    audio_q.put(bytes(indata))

def listen(model_obj, timeout=8):
    rec = KaldiRecognizer(model_obj, SAMPLE_RATE)
    while not audio_q.empty():
        audio_q.get()

    print("[MIC] Listening... speak now!")
    try:
        # Find default input device
        input_device = sd.default.device[0] if sd.default.device[0] is not None else 0
        print(f"[INFO] Using audio device: {input_device}")
        
        stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=8000,
            dtype='int16',
            channels=1,
            device=input_device,
            callback=audio_callback
        )
        stream.start()
    except Exception as e:
        print(f"[ERROR] Failed to start audio stream: {e}")
        print("[INFO] Available audio devices:")
        print(sd.query_devices())
        return None
        
    heard = ""
    deadline = time.time() + timeout
    try:
        while time.time() < deadline:
            try:
                data = audio_q.get(timeout=0.5)
            except queue.Empty:
                continue
            if rec.AcceptWaveform(data):
                result = json.loads(rec.Result())
                text = result.get("text", "").strip()
                if text:
                    print(f"[YOU SAID] {text}")
                    heard = text.lower()
                    break
        if not heard:
            partial = json.loads(rec.PartialResult()).get("partial", "").strip()
            if partial:
                print(f"[YOU SAID] {partial}")
                heard = partial.lower()
    finally:
        stream.stop()
        stream.close()

    if not heard:
        print("[MIC] Nothing heard.")
    return heard

# ── GROQ AI ──
def ask_groq(question):
    try:
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        body = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 120,
            "messages": [
                {"role": "system", "content": (
                    "You are a helpful voice assistant in a Smart Accident Detection System. "
                    "Keep answers to 1-2 sentences only — they will be spoken aloud. "
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
        else:
            print(f"[AI ERROR] {data}")
            return "Sorry, I could not get an answer right now."
    except requests.exceptions.ConnectionError:
        return "No internet connection. Please check your Wi-Fi."
    except Exception as e:
        print(f"[ERROR] {e}")
        return "Sorry, something went wrong."

# ── ACCIDENT MODE ──
def handle_accident(model_obj):
    print("\n" + "!"*50)
    print("  ACCIDENT EMERGENCY MODE ACTIVATED")
    print("!"*50)
    speak(ACCIDENT_PROMPT)
    heard = listen(model_obj, timeout=10)
    if any(w in heard for w in ["cancel", "stop", "false", "no"]):
        speak("Alert cancelled. System is back to monitoring. Stay safe.")
    else:
        speak("No response. Alert confirmed. Contacting emergency services now.")
        time.sleep(0.5)
        speak(ALERT_MESSAGE)
        print("[EMERGENCY] Emergency alert triggered!")

# ── MAIN ──
def main():
    print("\n" + "="*50)
    print("   Smart AI Voice Assistant")
    print("   Groq AI (Free) + Accident Emergency Mode")
    print("="*50 + "\n")

    if not os.path.exists(MODEL_PATH):
        print(f"[ERROR] Vosk model not found: {MODEL_PATH}")
        sys.exit(1)

    print("[STT] Loading speech model...")
    model_obj = Model(MODEL_PATH)
    print("[STT] Speech model ready.")

    speak("Hello! I am your smart voice assistant. I am ready. How can I help you?")

    print("\n[READY] Just speak — I am listening!")
    print("[TIP]   Say 'accident' to test emergency mode.")
    print("[TIP]   Say 'goodbye' to stop.\n")

    try:
        while True:
            heard = listen(model_obj, timeout=8)
            if not heard:
                continue

            if any(w in heard for w in ["accident", "emergency", "crash", "help me"]):
                handle_accident(model_obj)

            elif any(w in heard for w in ["stop", "exit", "quit", "goodbye", "bye"]):
                speak("Goodbye! Stay safe.")
                break

            else:
                print("[THINKING] Asking Groq AI...")
                answer = ask_groq(heard)
                speak(answer)

    except KeyboardInterrupt:
        print("\n[EXIT] Stopped.")
        speak("Goodbye!")

if __name__ == "__main__":
    main()