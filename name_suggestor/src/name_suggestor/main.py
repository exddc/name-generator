import os
import json
from typing import List
from fastapi import FastAPI, Body
from pydantic import BaseModel

# import openai  # for demonstration, but you can replace with other LLM providers
import groq

# ------------------------------
# Configure your OpenAI API key
# (in production, it's best to keep this in an environment variable)
# ------------------------------
""" openai.api_key = os.getenv(
    "OPENAI_API_KEY", "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"
)
 """
client = groq.Groq(
    api_key=os.environ.get(
        "GROQ_API_KEY", "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"
    ),
)

app = FastAPI()


class SuggestRequest(BaseModel):
    query: str


# ------------------------------
# LLM Call (OpenAI by default, can be replaced with another LLM)
# ------------------------------
def get_suggestions_from_llm(user_input: str) -> List[str]:
    """
    Query an LLM to get domain name suggestions based on the user input.
    Currently using OpenAI ChatCompletion for demonstration.

    This function should return only a list of domain names (strings).
    Replace this with the relevant calls/settings for other LLM providers if needed.
    """
    # Prompt the model: instruct it to return a JSON array of strings (domain names).
    prompt = f"""
You are a domain name generator. The user provided the following input:
\"{user_input}\"

Read the users input and think about possible domain names for their idea.
Select 5 domain names that would be suitable for this user's idea and that are available for registration.
Don't worry about checking availability; just focus on generating ideas. Don't include any special characters or spaces.
Generate valid domain names that are memorable and easy to spell. The 5 domain names should be unique and distinct from each other.
Don't generate variations of the same domain name (e.g., "example.com" and "example.net").
Use suitable TLDs for each domain name, for example tech startups can use ".io" or ".ai", apps can use ".app", etc.
Try to use high-quality, professional-sounding domain names that are not too long.
You can also generate more abstract or creative domain names that are still relevant to the user's idea, but don't fully describe it.

Return ONLY a JSON array of domain names (strings), with no extra commentary.
Example output: ["mydomain.com", "anotheridea.io"]
    """.strip()

    try:
        """response = openai.chat.completions.create(
            model="gpt-4o-mini",  # or use another model
            messages=[{"role": "user", "content": prompt}],
        )"""

        response = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            model="llama-3.2-3b-preview",
        )

        # The model should return JSON array of strings.
        content = response.choices[0].message.content.strip()

        # Attempt to parse the JSON array from the model's response.
        suggestions = json.loads(content)

        # Validate that suggestions is a list of strings; if not, raise an error.
        if not isinstance(suggestions, list) or not all(
            isinstance(s, str) for s in suggestions
        ):
            raise ValueError("Model did not return a valid list of strings.")

        for suggestion in suggestions:
            # Remove any leading/trailing whitespace and lowercase the domain names
            suggestion = suggestion.strip().lower()

            # Remove any sspaces from the domain names
            suggestion = suggestion.replace(" ", "")

            # Save the updated suggestion back to the list
            suggestions[suggestions.index(suggestion)] = suggestion

        return suggestions

    except Exception as e:
        # In case of any error, you might want to return a fallback response or raise the error
        print(f"Error while fetching suggestions from LLM: {e}")
        return []


# ------------------------------
# Health Check Endpoint
# ------------------------------
@app.get("/health")
def health():
    return {"status": "ok", "message": "Name Suggestor is running"}


# ------------------------------
# Suggest Endpoint
# ------------------------------
@app.post("/suggest")
def suggest_domains(request: SuggestRequest):
    """
    Takes in a user query (e.g., list of domains, app description, company idea)
    and returns an array of possible domain name suggestions from the LLM.
    """
    user_input = request.query
    suggestions = []
    while suggestions == []:
        suggestions = get_suggestions_from_llm(user_input)
    return {"suggestions": suggestions}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
