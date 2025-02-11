import random
import logging
import re
from typing import Dict, Any, Optional
from modules import tables
from modules.doc_writer import write_section  # Use the new writer
from ollama_manager import generate_with_retry

logger = logging.getLogger(__name__)

def sanitize(text: str) -> str:
    """
    Perform basic sanitization to remove internal <think>...</think> sections.
    This function preserves most text formatting.
    """
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    return cleaned.strip()

def generate_factions(model: str, history_content: str) -> Dict[str, Any]:
    """Generate dungeon factions using the configured model and write the output."""
    try:
        num_factions = random.randint(1, 3)
        logger.info(f"Generating {num_factions} faction(s)")

        factions = []
        for i in range(num_factions):
            faction = _generate_single_faction(model, history_content, i + 1)
            if faction:
                factions.append(faction)

        result = {
            "num_factions": len(factions),
            "factions": factions
        }
        # Build markdown content from faction data.
        markdown_content = _build_faction_markdown(result)
        # Write the markdown content to a file (e.g., faction.md in the docs/ folder).
        write_section("faction", markdown_content)

        return result

    except Exception as e:
        logger.error(f"Faction generation failed: {str(e)}")
        return {"error": str(e)}

def _generate_single_faction(model: str, history: str, index: int) -> Optional[Dict]:
    """Generate a single faction with retry logic."""
    try:
        details = _assemble_faction_details()
        prompt = _create_faction_prompt(details, history)

        logger.info(f"Generating faction {index} using model {model}")
        response = generate_with_retry(
            prompt=prompt,
            model=model,
            temperature=0.8,
            top_p=0.9
        )

        if not response:
            raise ValueError("Empty response from generation API")

        return {
            **details,
            "content": sanitize(response.get("response", ""))
        }

    except Exception as e:
        logger.error(f"Failed to generate faction {index}: {str(e)}")
        return None

def _assemble_faction_details() -> Dict[str, str]:
    """Assemble faction components from tables with validation."""
    required_tables = ["goal", "obstacle", "impulse", "size", "creature_type"]
    for table in required_tables:
        if not tables.FACTION_TABLES.get(table):
            raise ValueError(f"Missing required FACTION_TABLES entry: {table}")

    return {
        "goal": random.choice(tables.FACTION_TABLES["goal"]),
        "obstacle": random.choice(tables.FACTION_TABLES["obstacle"]),
        "impulse": random.choice(tables.FACTION_TABLES["impulse"]),
        "size": random.choice(tables.FACTION_TABLES["size"]),
        "creature_type": random.choice(tables.FACTION_TABLES["creature_type"])
    }

def _create_faction_prompt(details: Dict[str, str], history: str) -> str:
    """Create a structured generation prompt for a faction."""
    return f"""Create a dark fantasy faction description with these elements:

1. Faction Name (Original and thematic)
2. Core Goal: {details['goal']}
3. Primary Obstacle: {details['obstacle']}
4. Driving Impulse: {details['impulse']}
5. Organization Size: {details['size']}
6. Creature Type: {details['creature_type']}

Historical Context:
{history}

Include:
- Leadership structure
- Key locations they control
- Relationship to other factions
- Signature abilities/resources
- A 2-3 sentence description of their current activities.
"""

def _build_faction_markdown(faction_data: Dict[str, Any]) -> str:
    """Convert faction data into a well-formatted markdown string."""
    md_lines = []
    md_lines.append("# Faction Documentation")
    md_lines.append("")
    md_lines.append(f"**Number of factions:** {faction_data.get('num_factions', 0)}")
    md_lines.append("")

    for faction in faction_data.get("factions", []):
        md_lines.append("## Faction")
        # If your faction details include a faction name, display it.
        # Otherwise, display the goal as a title.
        faction_name = faction.get("name", faction.get("goal", "Unnamed Faction"))
        md_lines.append(f"**Faction Name:** {faction_name}")
        md_lines.append(f"**Core Goal:** {faction.get('goal', '')}")
        md_lines.append(f"**Primary Obstacle:** {faction.get('obstacle', '')}")
        md_lines.append(f"**Driving Impulse:** {faction.get('impulse', '')}")
        md_lines.append(f"**Organization Size:** {faction.get('size', '')}")
        md_lines.append(f"**Creature Type:** {faction.get('creature_type', '')}")
        md_lines.append("")
        md_lines.append("**Description:**")
        md_lines.append(faction.get("content", ""))
        md_lines.append("")
        md_lines.append("---")
        md_lines.append("")

    return "\n".join(md_lines)
