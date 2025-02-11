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
    get_history_prompt,
    get_ruin_prompt,
    get_present_prompt
    # get_builder_prompt
)
from modules.name_generator import generate_random_name


logger = logging.getLogger(__name__)


def sanitize(text: str) -> str:
    """Robust content cleaning that preserves markdown syntax."""
    # Remove internal <think>...</think> sections
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Allow markdown characters (# and *) in addition to the other punctuation.
    cleaned = re.sub(r'[^\w\s.,!?\-:\'\"#*]', '', cleaned)
    # Normalize newlines: collapse three or more newlines into two newlines.
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def generate_history(model: str) -> Dict[str, Any]:
    """
    Generate the dungeon history using the configured model and write the
    formatted, sanitized markdown content immediately to the history section.
    """
    try:
        logger.info("📜 Starting history generation...")

        builder_info = _select_faction_details()
        # Generate a unique builder name
        builder_info["builder_name"] = generate_random_name()

        # Generate a unique present occupant name
        builder_info["present_name"] = generate_random_name()

        history_components = _select_history_components()
        content_parts = _generate_history_content(model, builder_info, history_components)

        # Concatenate content parts with spacing.
        final_history = "\n\n".join(content_parts.values())
        metadata = _build_metadata(builder_info, history_components)

        # Build and sanitize markdown content.
        markdown_content = sanitize(_build_markdown(final_history, metadata))

        # Write to history section file.
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
    Generate history content sequentially.
    First, generate the ancient history text.
    Then, feed that output into the ruin prompt.
    Finally, generate the present state description.
    """
    content = {}

    # 1. Generate history text.
    history_agent = get_history_prompt(history_components, builder_info)
    history_response = generate_with_retry(history_agent["prompt"], model)
    if not history_response or 'response' not in history_response:
        raise RuntimeError(f"No valid response from agent {history_agent['key']}")
    history_text = history_response['response'].strip()
    content[history_agent["key"]] = history_text

    # 2. Generate ruin text using the previously generated history_text.
    ruin_agent = get_ruin_prompt(history_components, builder_info, history_text)
    ruin_response = generate_with_retry(ruin_agent["prompt"], model)
    if not ruin_response or 'response' not in ruin_response:
        raise RuntimeError(f"No valid response from agent {ruin_agent['key']}")
    ruin_text = ruin_response['response'].strip()
    content[ruin_agent["key"]] = ruin_text

    # 3. Generate present text.
    present_agent = get_present_prompt(history_components, builder_info)
    present_response = generate_with_retry(present_agent["prompt"], model)
    if not present_response or 'response' not in present_response:
        raise RuntimeError(f"No valid response from agent {present_agent['key']}")
    present_text = present_response['response'].strip()
    content[present_agent["key"]] = present_text

    return content



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
