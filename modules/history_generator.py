import logging
import random
from typing import Dict, Any, Optional
from modules import tables
from modules.output_writer import write_markdown
from ollama_manager import generate_with_retry  # Changed import

logger = logging.getLogger(__name__)


def generate_history(model: str) -> Dict[str, Any]:  # Removed interactive params
    """Generate dungeon history using configured model"""
    try:
        logger.info("📜 Starting history generation...")

        history_components = _select_history_components()
        builder_info = _select_faction_details()
        content = _generate_history_content(model, builder_info, history_components)

        final_history = "\n\n".join(content.values())
        metadata = _build_metadata(builder_info, history_components)

        logger.info("✅ History generation complete!")
        return {
            "content": final_history,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"History generation failed: {str(e)}")
        return {"error": str(e)}


def _select_history_components() -> Dict[str, str]:
    """Select random elements from history tables"""
    return {
        "History Base": random.choice(tables.DUNGEON_TABLES["history"]),
        "Modifier": random.choice(tables.DUNGEON_TABLES["modifier"]),
        "Purpose": random.choice(tables.DUNGEON_TABLES["purpose"]),
        "Cause of Ruin": random.choice(tables.DUNGEON_TABLES["ruin"]),
        "Present Purpose": random.choice(tables.DUNGEON_TABLES["present"])
    }


def _select_faction_details() -> Dict[str, str]:
    """Select faction characteristics"""
    return {
        "Creature Type": random.choice(tables.FACTION_TABLES["creature_type"]),
        "Impulse": random.choice(tables.FACTION_TABLES["impulse"])
    }


def _generate_history_content(model: str, builder_info: Dict, history_components: Dict) -> Dict:
    """Generate content using the new ollama manager"""
    agents = [
        _create_builder_agent(builder_info),
        _create_history_agent(history_components),
        _create_ruin_agent(history_components),
        _create_present_agent(history_components)
    ]

    content = {}
    for idx, agent in enumerate(agents):
        response = generate_with_retry(agent["prompt"], model)
        if not response:
            raise RuntimeError(f"Agent {idx} failed to generate content")
        content[agent["key"]] = response.get("response", "").strip()

    return content


def _create_builder_agent(builder_info: Dict) -> Dict:
    return {
        "key": "Builders",
        "prompt": f"""Create original builders description:
- Creature Type: {builder_info['Creature Type']}
- Impulse: {builder_info['Impulse']}
Provide concise background in one paragraph."""
    }


def _create_history_agent(components: Dict) -> Dict:
    return {
        "key": "Ancient History",
        "prompt": f"""Factual ancient history including:
- Builders: {components['History Base']}
- Purpose: {components['Modifier']} {components['Purpose']}
One paragraph with key events."""
    }


def _create_ruin_agent(components: Dict) -> Dict:
    return {
        "key": "Ruin",
        "prompt": f"""Describe fall into ruin:
- Cause: {components['Cause of Ruin']}
One paragraph with key details."""
    }


def _create_present_agent(components: Dict) -> Dict:
    return {
        "key": "Present State",
        "prompt": f"""Current state description:
- Purpose: {components['Present Purpose']}
One paragraph with current occupants."""
    }


def _build_metadata(builder_info: Dict, components: Dict) -> Dict:
    """Build standardized metadata format"""
    return {
        "builders": builder_info["Creature Type"],
        "original_purpose": f"{components['Modifier']} {components['Purpose']}",
        "ruin_cause": components["Cause of Ruin"],
        "current_state": components["Present Purpose"]
    }