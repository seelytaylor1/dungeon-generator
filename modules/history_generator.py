# history_generator.py
from datetime import datetime
import logging
import random
import re
from typing import Dict, Any
from modules import tables
from modules.doc_writer import write_section
from ollama_manager import generate_with_retry
from modules.prompts import (
    get_combined_history_prompt
)
from modules.name_generator import generate_random_name


logger = logging.getLogger(__name__)


def sanitize(text: str) -> str:
    # Temporarily disable sanitization.
    return text


def generate_history(model: str) -> Dict[str, Any]:
    """Generate history with simplified content handling"""
    try:
        logger.info("📜 Starting history generation...")

        builder_info = _select_faction_details()
        builder_info["builder_name"] = generate_random_name()
        builder_info["present_name"] = generate_random_name()

        history_components = _select_history_components()
        content_parts = _generate_history_content(model, builder_info, history_components)

        # Use single history content
        final_history = content_parts["History"]
        metadata = _build_metadata(builder_info, history_components)

        markdown_content = _build_markdown(final_history, metadata)
        write_section("history", markdown_content)

        logger.info("✅ History generation complete!")
        return {"content": final_history, "metadata": metadata}

    except Exception as e:
        logger.error(f"History generation failed: {str(e)}")
        return {"error": str(e)}


def _build_markdown(content: str, metadata: Dict[str, Any]) -> str:
    """Create a well-formatted markdown string from history content and metadata."""
    md = (
        "# Dungeon Documentation\n\n"
        f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n"
        "## History\n\n"
        f"{sanitize(content).strip()}\n\n"
        "## Metadata\n\n"
    )
    md += "\n".join(f"- **{key.replace('_', ' ').title()}**: {value}" for key, value in metadata.items())
    return md.strip() + "\n"


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
    """
    Directly extract and return the full solution content without section splitting
    """
    combined_agent = get_combined_history_prompt(history_components, builder_info)
    combined_response = generate_with_retry(combined_agent["prompt"], model)

    if not combined_response or 'response' not in combined_response:
        raise RuntimeError(f"No valid response from agent {combined_agent['key']}")

    combined_text = combined_response['response'].strip()

    # Extract solution section
    solution_match = re.search(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', combined_text, re.DOTALL)
    if not solution_match:
        raise RuntimeError("No solution section found in response")

    solution_content = solution_match.group(1).strip()

    # Remove any remaining special tokens
    clean_content = re.sub(r'<\|.*?\|>', '', solution_content, flags=re.DOTALL).strip()

    return {"History": clean_content}


def _build_metadata(builder_info: Dict[str, str], components: Dict[str, str]) -> Dict[str, Any]:
    """Build metadata with validation"""
    required_keys = {
        'builder': ['creature_type', 'impulse'],
        'components': ['modifier', 'purpose', 'ruin', 'present']
    }

    missing = [k for k in required_keys['builder'] if k not in builder_info]
    if missing:
        raise ValueError(f"Missing builder keys: {missing}")

    missing = [k for k in required_keys['components'] if k not in components]
    if missing:
        raise ValueError(f"Missing component keys: {missing}")

    return {
        "builders": builder_info["creature_type"],
        "original_purpose": f"{components['modifier']} {components['purpose']}",
        "ruin_cause": components["ruin"],
        "current_state": components["present"],
    }
