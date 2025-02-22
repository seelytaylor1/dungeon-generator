# history_generator.py
from datetime import datetime
import logging
import random
import re
from typing import Dict, Any
from modules import tables
from utils.doc_writer import DocumentationBuilder
from utils.ollama_manager import generate_with_retry
from modules.prompts import get_combined_history_prompt
from modules.name_generator import generate_random_name

logger = logging.getLogger(__name__)


def sanitize(text: str) -> str:
    return text  # Sanitization now handled by DocumentationBuilder


def generate_history(model: str) -> Dict[str, Any]:
    try:
        logger.info("📜 Starting history generation...")
        doc_builder = DocumentationBuilder()

        builder_info = _select_faction_details()
        builder_info["builder_name"] = generate_random_name()
        builder_info["present_name"] = generate_random_name()

        history_components = _select_history_components()
        content_parts = _generate_history_content(model, builder_info, history_components)

        final_history = content_parts["History"]
        metadata = _build_metadata(builder_info, history_components)

        # Write only the narrative content to history.md (no metadata)
        doc_builder.write_section(
            section_name="history",
            content=sanitize(final_history).strip()
        )

        logger.info("✅ History generation complete!")
        return {
            "content": final_history,
            "metadata": metadata,
            "section_name": "history"  # Required for merge ordering
        }
    except Exception as e:
        logger.error(f"History generation failed: {str(e)}")
        return {"error": str(e)}


def _format_section_content(content: str, metadata: Dict[str, Any]) -> str:
    return (
        f"{sanitize(content).strip()}\n\n"
        "### Metadata\n\n"
        "\n".join(f"- **{key.replace('_', ' ').title()}**: {value}"
                  for key, value in metadata.items())
    )


def _select_history_components() -> Dict[str, str]:
    """Select random elements from history tables."""
    return {key: random.choice(tables.DUNGEON_TABLES[key]) for key in ["history",
                                                                       "modifier",
                                                                       "purpose",
                                                                       "ruin",
                                                                       "present"]}


def _select_faction_details() -> Dict[str, str]:
    """Select random faction characteristics."""
    return {key: random.choice(tables.FACTION_TABLES[key]) for key in ["creature_type", "impulse"]}


def _generate_history_content(model: str, builder_info: Dict[str, str], history_components: Dict[str, str]) -> Dict[str, str]:
    combined_agent = get_combined_history_prompt(history_components, builder_info)

    # Log the prompt message being sent
    logger.debug("Sending prompt to LLM: %s", combined_agent["prompt"])

    combined_response = generate_with_retry(combined_agent["prompt"], model)

    # Log the raw LLM response
    logger.debug("Received raw LLM response: %s", combined_response)

    if not combined_response or 'response' not in combined_response:
        raise RuntimeError(f"No valid response from agent {combined_agent['key']}")

    combined_text = combined_response['response'].strip()

    # Extract the solution section using the special tokens
    solution_match = re.search(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', combined_text, re.DOTALL)
    if not solution_match:
        raise RuntimeError("No solution section found in response")

    solution_content = solution_match.group(1).strip()
    # Log the extracted solution content before cleaning
    logger.debug("Extracted solution content: %s", solution_content)

    # Clean out any remaining special tokens
    clean_content = re.sub(r'<\|.*?\|>', '', solution_content, flags=re.DOTALL).strip()

    # Log the cleaned solution content
    logger.debug("Cleaned solution content: %s", clean_content)

    return {"History": clean_content}


def _build_metadata(builder_info: Dict[str, str], components: Dict[str, str]) -> Dict[str, Any]:
    """Build metadata for the history section."""
    return {
        "builders": builder_info["creature_type"],
        "original_purpose": f"{components['modifier']} {components['purpose']}",
        "ruin_cause": components["ruin"],
        "current_state": components["present"],
        "present_name": builder_info.get("present_name", "Unknown")
    }
