import os
import traceback
from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

print("API Key Loaded:", api_key is not None)
print("Model:", model)

try:
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model,
        contents="Say hello."
    )

    print("\nSUCCESS\n")
    print(response.text)

except Exception:
    print("\nFAILED\n")
    traceback.print_exc()