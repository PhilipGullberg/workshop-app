import requests
import json
import os

def generate_music(prompt: str, session_id: str, style: str = None):
    """Generates music using the Suno API."""

    url = "https://apibox.erweima.ai/api/v1/generate"

    # It's recommended to store your API key securely, e.g., in environment variables
    SUNO_API_KEY = os.getenv("SUNO", "YOUR_SUNO_API_KEY") # Replace with your preferred method

    payload = json.dumps({
      "prompt": prompt,
      "customMode": False,
      "instrumental": False,
      "model": "V3_5",
      "negativeTags": "",
      "callBackUrl": f"https://workshop-app-still-cherry-5077.fly.dev/suno_callback?session_id={session_id}"
    })

    headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
      'Authorization': f'Bearer {SUNO_API_KEY}'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status() # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error calling Suno API: {e}")
        return None
