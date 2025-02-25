# exterior_generator.py
import re
import logging
from datetime import datetime
from typing import Dict, Any
from modules import tables
from utils.doc_writer import DocumentationBuilder
from utils.ollama_manager import generate_with_retry
from modules.prompts import EXTERIOR_PROMPTS

logger = logging.getLogger(__name__)


def extract_solution_content(response: str) -> str:
    """Extract content between 'Solution Section' and end_of_solution tags."""
    try:
        # Find start of solution
        solution_start = response.find("Solution Section")
        if solution_start == -1:
            raise ValueError("No 'Solution Section' found in response")
            
        # Move past the "Solution Section" header
        content_start = solution_start + len("Solution Section")
        
        # Find end of solution
        solution_end = response.find("<|end_of_solution|>")
        if solution_end == -1:
            raise ValueError("No end_of_solution tag found in response")
            
        # Extract and clean the solution content
        return response[content_start:solution_end].strip()
        
    except Exception as e:
        logger.error(f"Failed to extract solution content: {e}")
        raise


def generate_exterior(model: str, history_content: str, faction_content: str) -> Dict[str, Any]:
    """Generates exterior content with direct solution extraction."""
    try:
        logger.info("🌅 Starting exterior generation...")

        # Construct the prompt using the history and faction content
        prompt = EXTERIOR_PROMPTS["main"].format(
            history_content=history_content,
            faction_content=faction_content
        )

        # Log the prompt being sent
        logger.debug("Sending prompt to LLM: %s", prompt)

        # Generate LLM response
        response = generate_with_retry(
            prompt=prompt,
            model=model,
            temperature=0.8,
            top_p=0.85
        )

        if not response or not response.get("response"):
            raise ValueError("Empty LLM response")

        # Log the raw response
        logger.debug("Received raw response: %s", response["response"])

        # Extract content between solution tags
        content = extract_solution_content(response["response"])
        if not content:
            raise ValueError("Empty content after extraction")

        # Write directly to docs
        result = {
            "content": content,
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "raw_response": response["response"]  # Keep for debugging
            }
        }

        DocumentationBuilder().write_section("exterior", content)
        logger.info("✅ Exterior generation complete!")
        return result

    except Exception as e:
        logger.error(f"Exterior generation failed: {str(e)}")
        return {"error": str(e)}
