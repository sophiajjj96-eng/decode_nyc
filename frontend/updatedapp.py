from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.cloud import speech
import os

app = Flask(__name__)
CORS(app)

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")
speech_client = speech.SpeechClient()

SYSTEM_PROMPT = """
You are a poetic personal journal writer...
"""

@app.route("/journal", methods=["POST"])
def journal():
    try:
        # Check if request contains audio or text
        if "audio" in request.files:
            # Step 1 - transcribe audio
            audio_file = request.files["audio"].read()
            
            audio = speech.RecognitionAudio(content=audio_file)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
                sample_rate_hertz=48000,
                language_code="en-US"
            )
            
            stt_response = speech_client.recognize(config=config, audio=audio)
            transcript = " ".join([
                result.alternatives[0].transcript 
                for result in stt_response.results
            ])

        else:
            # Fall back to plain text if no audio
            transcript = request.get_json().get("transcript", "").strip()

        if not transcript:
            return jsonify({"error": "No input provided"}), 400

        # Step 2 - generate journal entry
        response = model.generate_content([
            SYSTEM_PROMPT,
            f"Here is my day: {transcript}"
        ])

        return jsonify({
            "entry": response.text,
            "transcript": transcript  # send back so user can see what was heard
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)