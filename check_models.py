# check_models.py
from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ GOOGLE_API_KEY not found in .env file")
else:
    client = genai.Client(api_key=api_key)
    print("Available models:\n")
    for model in client.models.list():
        print(f"  {model.name}")