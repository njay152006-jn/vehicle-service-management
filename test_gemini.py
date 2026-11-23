import os
from dotenv import load_dotenv
from google import genai

# Load environment variables
load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

if not API_KEY:
    raise SystemExit("ERROR: GEMINI_API_KEY not found in .env file")

client = genai.Client(api_key=API_KEY)

try:
    print("Connecting to Gemini...")

    response = client.models.generate_content(
        model=MODEL,
        contents="Reply with exactly: VehicleCare AI connection successful."
    )

    print("\nModel:", MODEL)
    print("Gemini response:")
    print(response.text)

except Exception as error:
    print("\nGemini connection failed.")
    print("Error:", error)

finally:
    client.close()