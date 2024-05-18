from flask import Flask, request, jsonify
import openai
import os
import time
import base64

app = Flask(__name__)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')
        
@app.route('/')
def index():
    return jsonify({"Server Running": "Welcome to your favourite server!"})


@app.route('/process', methods=['POST'])
def process_files():
    print("request received")
    #start_time = time.time()

    # Check if files are in the request
    if 'audio' not in request.files or 'image' not in request.files:
        return jsonify({'error': 'Audio or image file is missing'}), 400

    audio_file = request.files['audio']
    image_file = request.files['image']

    # Save the audio file
    audio_path = os.path.join(os.getcwd(), "audio_file.m4a")
    audio_file.save(audio_path)

    # Transcribe audio using OpenAI Whisper API
    with open(audio_path, "rb") as audio:
        transcript_response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio
        )

    transcript = transcript_response.text
    print(f"Transcript: {transcript}")

    image_path = os.path.join(os.getcwd(), "image_file.png")
    image_file.save(image_path)

    # Verify image format and size
    # if not image_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
        # return jsonify({'error': 'Unsupported image format'}), 400
    
    image_size = os.path.getsize(image_path)
    if image_size > 10 * 1024 * 1024:
        return jsonify({'error': 'Image file size exceeds 20 MB'}), 400
    
    # Encode image to base64
    base64_image = encode_image(image_path)

    response = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Heres the question: " + transcript + ". Make the response quick and consise. ONLY and ONLY tell what the main thing the image is or what I asked for. Make it human like and make it maximum 2-3 sentences of a response unless more is needed."},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": "data:image/jpeg;base64," + base64_image,
                        },
                    },
                ],
            }
        ],
        max_tokens=50,
    )

    response_text = response.choices[0].message.content
    print(f"Response: {response_text}")

    # total_time = time.time() - start_time
    # print(f"Total Time: {total_time:.2f} seconds")

    return response_text

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
