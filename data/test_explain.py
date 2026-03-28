import json
from google import genai
import os

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

with open("algorithms.json", "r") as f:
    data = json.load(f)

algo = data[0]  # school_assignment

prompt = f"""
Explain this government algorithm in plain language.

Make it:
- simple
- personal ("this may affect you")
- short (3-5 sentences)

Data:
{json.dumps(algo, indent=2)}

User context:
I live in Brooklyn and want to understand school assignment.
"""

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
)

print(response.text)
