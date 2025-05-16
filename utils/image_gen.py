import os
import json
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import uuid
from flask import session
import base64

# Configure your image generation API key
# It's recommended to store your API key securely in environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY")
client = genai.Client(api_key=GOOGLE_API_KEY)

def generate_image(prompt):

    try:
        print(f"Generating image with prompt: {prompt}")
        image_url = "https://via.placeholder.com/512" # Placeholder image URL
        response = client.models.generate_content(
            model="gemini-2.0-flash-preview-image-generation",
            contents=[prompt],
            config=types.GenerateContentConfig(
              response_modalities=['TEXT','IMAGE']
            )
        )

        for part in response.candidates[0].content.parts:
            if part.text is not None:
                print(part.text)
            elif part.inline_data is not None:
                unique_id = uuid.uuid4().hex
                session_id=session.get('user_session_id')
                image_filename = f"{session_id}_{unique_id}.png"
                image = Image.open(BytesIO((part.inline_data.data)))
            
                image_dir = os.path.join("static", 'generated_images')
                os.makedirs(image_dir, exist_ok=True)
                image_path = os.path.join(image_dir, image_filename)
                image.save(image_path)
                
                session['step2_image_filename'] = image_filename
                image.show()
                with BytesIO() as buffer:
                        image.save(buffer, format="PNG")
                        image_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        return image_filename
    except Exception as e:
        print(f"Error generating image: {e}")
        return None
