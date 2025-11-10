import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # loads .env in project root
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

print("Models that support generateContent:")
for m in genai.list_models():
    if "generateContent" in getattr(m, "supported_generation_methods", []):
        print("-", m.name)
