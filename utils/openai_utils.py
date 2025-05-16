from google import genai
import os
import json
from pydantic import BaseModel

# Configure the Gemini API key
# It's recommended to store your API key securely, e.g., in environment variables
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "YOUR_API_KEY") # Replace with your preferred method of getting the API key
client = genai.Client(api_key=GOOGLE_API_KEY)

class Product_idea(BaseModel):
    title: str
    description: str
    price: str
   

def generate_product_idea(prompt):
 """Generates a product idea (title, description, price) using the Gemini API."""
 try:

    
    # TODO: Craft the prompt for Gemini to get structured output (e.g., JSON)
    gemini_prompt = f"""
    Generate a product idea based on the following concept: {prompt}

    Provide the output in JSON format with the following keys: "title", "description", "price".
    """

    # TODO: Send the prompt to Gemini and get the response
    response = client.models.generate_content(model="gemini-2.0-flash", contents=gemini_prompt, config={
        "response_mime_type": "application/json",
        "response_schema": list[Product_idea],
    },)

    response_text = response.text
    # Assuming the response text is a valid JSON string
    try:
        product_list = json.loads(response_text)
        product_data = product_list[0]

        title = product_data.get("title", "")
        description = product_data.get("description", "")
        price = product_data.get("price", "")

        return {
            "title": title,
            "description": description,
            "price": price
        }
    except json.JSONDecodeError as json_e:
        print(f"Error decoding JSON from Gemini API response: {json_e}")
        print(f"API response text: {response_text}") # Print the response text to inspect it
        return {
            "title": "Error",
            "description": f"Could not generate product idea. Invalid JSON response from API. Response text: {response_text}",
            "price": "N/A"
        }

 except Exception as e:
    print(f"Error generating product idea with Gemini: {e}")
    return {
    "title": "Error",
    "description": "Could not generate product idea.",
    "price": "N/A"
    }