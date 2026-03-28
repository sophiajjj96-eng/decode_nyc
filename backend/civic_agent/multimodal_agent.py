"""Multimodal agent for generating text + images simultaneously."""

import base64
import os
from typing import Any

from google import genai
from google.adk.tools import FunctionTool


async def generate_algorithm_visualization(
    algorithm_id: str,
    user_situation: str = "",
) -> dict[str, Any]:
    """Generate an interleaved text + image explanation of an algorithm.
    
    Uses Gemini 2.5 Flash with TEXT + IMAGE modalities to create
    visual flowcharts alongside narrative explanations.
    
    Args:
        algorithm_id: ID of the algorithm to visualize
        user_situation: Optional user context
        
    Returns:
        Dict with 'narration' text and 'image_data' base64 string
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        
        # Map algorithm IDs to descriptions
        algorithm_descriptions = {
            "homebase_raq": "Homebase Risk Assessment Questionnaire - a scoring system that decides who gets homelessness prevention services based on prior DHS contact, housing length, income, and family size",
            "myschools": "MySchools Gale-Shapley matching algorithm - matches students to schools based on ranked preferences and student profiles",
            "acs_repeat_maltreatment": "ACS Repeat Maltreatment Predictive Model - predicts likelihood of future child maltreatment to prioritize caseworker attention",
            "shotspotter": "ShotSpotter acoustic gunshot detection - triggers police dispatch based on audio signals from neighborhood microphones"
        }
        
        algo_desc = algorithm_descriptions.get(algorithm_id, "NYC government algorithm")
        
        prompt = f"""Create a simple, clear flowchart showing how the {algo_desc} makes decisions.

The flowchart should:
- Show the decision-making process step by step
- Use simple boxes and arrows
- Include key decision points (yes/no branches)
- Be easy for non-technical people to understand
- Use clear, plain language (no jargon)
- Show what inputs go in and what outputs come out

Style: Clean, minimal, high contrast, easy to read."""

        # Generate with interleaved modalities
        response = await client.aio.models.generate_content(
            model="gemini-2.0-flash-exp",  # Using flash model for speed
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"] if os.getenv("ENABLE_IMAGE_GEN") else ["TEXT"],
            )
        )
        
        # Extract text and image from response
        narration = ""
        image_data = None
        
        for part in response.candidates[0].content.parts:
            if hasattr(part, 'text') and part.text:
                narration += part.text
            elif hasattr(part, 'inline_data') and part.inline_data:
                # Image data in base64
                image_data = part.inline_data.data
        
        return {
            "narration": narration if narration else "Visualization generated.",
            "image_data": image_data,
            "algorithm_id": algorithm_id
        }
        
    except Exception as e:
        return {
            "narration": f"Could not generate visualization: {str(e)}",
            "image_data": None,
            "algorithm_id": algorithm_id
        }


# Create tool
algorithm_visualization_tool = FunctionTool(generate_algorithm_visualization)
