from flask import Flask, request, jsonify
import openai
import os
from io import BytesIO
import base64
import concurrent.futures

app = Flask(__name__)

# Load the environment variables early
model_whisper = "whisper-1"
model_chat = "gpt-4o"
model_tts = "tts-1"
voice_tts = "alloy"
max_image_size = 10 * 1024 * 1024  # 10 MB

def encode_image(image_file):
    return base64.b64encode(image_file.read()).decode('utf-8')

@app.route('/')
def index():
    return jsonify({"Server Running": "Welcome to your favourite server!"})

@app.route('/process', methods=['POST'])
def process_files():
    print("Request received")

    # Check if files are in the request
    if 'audio' not in request.files or 'image' not in request.files:
        return jsonify({'error': 'Audio or image file is missing'}), 400

    audio_file = request.files['audio']
    image_file = request.files['image']

    # Save the audio file
    audio_path = "audio_file.m4a"
    audio_file.save(audio_path)

    # Save the image file for size check
    image_path = "image_file.png"
    image_file.save(image_path)

    # Verify image format and size
    if os.path.getsize(image_path) > max_image_size:
        return jsonify({'error': 'Image file size exceeds 10 MB'}), 400

    def transcribe_audio(audio_path):
        with open(audio_path, "rb") as audio:
            transcript_response = openai.audio.transcriptions.create(
                model=model_whisper,
                file=audio
            )
        return transcript_response.text

    def generate_response(transcript, base64_image):
        print(f"Generating response for transcript: {transcript}")
        print(f"Using base64 image: {base64_image[:50]}...")  # Print a snippet of the base64 string
        response = openai.chat.completions.create(
            model=model_chat,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Here's the question: " + transcript + ". Make the response quick and concise. ONLY and ONLY tell what the main thing the image is or what I asked for. Make it human like and make it maximum 2-3 sentences of a response unless more is needed."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": "data:image/jpeg;base64," + base64_image,
                            }
                        }
                    ]
                }
            ],
            max_tokens=50
        )
        return response.choices[0].message.content

    def synthesize_speech(response_text):
        speech_file = BytesIO()
        tts_response = openai.audio.speech.create(
            model=model_tts,
            voice=voice_tts,
            input=response_text
        )
        tts_response.stream_to_file(speech_file)
        speech_file.seek(0)  # Rewind the buffer for reading
        return base64.b64encode(speech_file.read()).decode('utf-8')

    base64_image = encode_image(request.files['image'])

    # Use threading to run non-dependent tasks in parallel
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_transcript = executor.submit(transcribe_audio, audio_path)
        transcript = future_transcript.result()
        response_text = generate_response(transcript, base64_image)
        speech_base64 = synthesize_speech(response_text)

    # Return both the response text and the speech MP3 file
    return jsonify({
        'response_text': response_text,
        'speech_mp3': speech_base64
    })

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
