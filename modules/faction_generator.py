# faction_generator.py
import logging
import random
import re
from datetime import datetime
from typing import Dict, Any, List
from modules import tables
from modules.doc_writer import write_section
from modules.name_generator import generate_random_name
from ollama_manager import generate_with_retry
from modules.prompts import FACTION_PRESENT_DAY_PROMPT, FACTION_BACKGROUND_PROMPT

logger = logging.getLogger(__name__)


def extract_solution(text: str) -> str:
    """
    Extracts the final narrative (solution) from the LLM response,
    i.e. the text between <|begin_of_solution|> and <|end_of_solution|>.
    If not found, returns the entire text stripped.
    """
    match = re.search(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_factions(
        model: str,
        history_content: str,
        history_metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Main faction generation controller"""
    try:
        logger.info("🤼 Starting faction generation...")
        history_metadata = history_metadata or {}

        # Generate present-day faction
        present_day_faction = _extract_present_day_faction(
            history_content,
            history_metadata,
            model
        )

        # Generate additional factions
        additional_factions = _generate_additional_factions(model, history_content)
        factions = [present_day_faction] + additional_factions

        # Log raw responses
        logger.debug("Raw faction content:")
        for faction in factions:
            logger.debug(f"Faction {faction['name']}:\n{faction['content']}")

        # Build documentation
        metadata = _build_faction_metadata(factions)
        markdown_content = _build_faction_markdown(factions)
        write_section("faction", markdown_content)

        logger.info("✅ Faction generation complete!")
        return {"factions": factions, "metadata": metadata}

    except Exception as e:
        logger.error(f"Faction generation failed: {str(e)}")
        return {"error": str(e)}


def _extract_present_day_faction(
        history_content: str,
        metadata: Dict[str, Any],
        model: str
) -> Dict[str, Any]:
    """Create main faction from history data"""
    faction_name = metadata.get("present_name", "").strip()
    if not faction_name:
        raise ValueError("Missing present-day faction name in metadata")

    return {
        "name": faction_name,
        "goal": metadata.get("current_state", "Control").split('.')[0].strip(),
        "obstacle": metadata.get("ruin_cause", "Threat").split('.')[0].strip(),
        "impulse": "Survival",
        "size": "Established Collective",
        "creature_type": f"{metadata.get('builders', 'Ancient')} ",
        "content": _generate_present_day_content(metadata, faction_name, history_content, model)
    }


def _generate_present_day_content(
        metadata: Dict[str, Any],
        name: str,
        history: str,
        model: str
) -> str:
    """Generate detailed present-day faction using LLM"""
    prompt = FACTION_PRESENT_DAY_PROMPT.format(
        name=name,
        history=history,
        builders=metadata.get("builders", "Unknown"),
        original_purpose=metadata.get("original_purpose", "Unknown"),
        current_state=metadata.get("current_state", "Unknown"),
        ruin_cause=metadata.get("ruin_cause", "Unknown")
    )
    try:
        response = generate_with_retry(
            prompt=prompt,
            model=model,
            temperature=0.7,
            top_p=0.9
        )
        response_text = response.get("response", "") if response else ""
        return extract_solution(response_text)
    except Exception as e:
        logger.warning(f"Using fallback content for {name}: {str(e)}")
        return f"Raw generation failed for {name}"


def _generate_additional_factions(model: str, history: str) -> List[Dict[str, Any]]:
    """Generate 0-2 random background factions"""
    factions = []
    for i in range(random.randint(0, 2)):
        try:
            faction = _generate_single_faction(model, history, i + 1)
            if faction:
                factions.append(faction)
                logger.debug(f"Raw faction response:\n{faction['content']}")
        except Exception as e:
            logger.warning(f"Skipping additional faction: {str(e)}")
    return factions


def _generate_single_faction(model: str, history: str, index: int) -> Dict[str, Any]:
    """Generate individual background faction"""
    details = {
        "name": generate_random_name(),
        "goal": random.choice(tables.FACTION_TABLES["goal"]),
        "obstacle": random.choice(tables.FACTION_TABLES["obstacle"]),
        "impulse": random.choice(tables.FACTION_TABLES["impulse"]),
        "size": random.choice(tables.FACTION_TABLES["size"]),
        "creature_type": random.choice(tables.FACTION_TABLES["creature_type"])
    }

    prompt = FACTION_BACKGROUND_PROMPT.format(
        name=details['name'],
        history=history,
        traits=str(details)
    )
    response = generate_with_retry(prompt, model, temperature=0.7)
    response_text = response.get("response", "") if response else ""
    return {**details, "content": extract_solution(response_text)}


def _build_faction_metadata(factions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive metadata"""
    return {
        "generated_at": datetime.now().isoformat(),
        "num_factions": len(factions),
        "primary_goals": list(set(f["goal"] for f in factions)),
        "creature_types": list(set(f["creature_type"] for f in factions))
    }


def _build_faction_markdown(factions: List[Dict[str, Any]]) -> str:
    """Build complete faction documentation with processed content"""
    md = ["# Faction Documentation\n"]

    for faction in factions:
        md.append(f"## {faction['name']}")
        md.append(f"**Creature Type**: {faction['creature_type']}")
        md.append(f"**Primary Goal**: {faction['goal']}")
        md.append(f"**Key Obstacle**: {faction['obstacle']}")
        md.append("\n### Faction Content")
        md.append(f"{faction['content']}\n")
        md.append("---\n")

    return '\n'.join(md)
