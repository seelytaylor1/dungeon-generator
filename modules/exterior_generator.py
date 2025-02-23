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


def extract_solution_content(text: str) -> str:
    """Extract solution content between markers or return full text if no markers found."""
    # First try to find content between solution markers
    match = re.search(
        r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>',
        text,
        re.DOTALL
    )
    
    if match:
        return match.group(1).strip()
    
    # If no markers found, check if the text contains markdown sections
    if '##' in text:
        logger.warning("No solution markers found, but markdown sections present. Using full response.")
        return text.strip()
    
    logger.error("No solution markers or markdown sections found in response")
    logger.debug("Raw response: %s", text)
    raise ValueError("Response does not contain required formatting")


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
