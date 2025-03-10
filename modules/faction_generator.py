#faction generator.py
import logging
import random
import re
from datetime import datetime
from typing import Dict, Any, List
from modules import tables
from utils.doc_writer import DocumentationBuilder
from modules.name_generator import generate_random_name
from utils.ollama_manager import generate_with_retry
from modules.prompts import FACTION_PRESENT_DAY_PROMPT, FACTION_BACKGROUND_PROMPT

logger = logging.getLogger(__name__)


def extract_solution(text: str) -> str:
    match = re.search(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def generate_factions(model: str, history_content: str, history_metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    try:
        logger.info("🤼 Starting faction generation...")
        history_metadata = history_metadata or {}

        present_day_faction = _extract_present_day_faction(history_content, history_metadata, model)
        additional_factions = _generate_additional_factions(model, history_content)
        factions = [present_day_faction] + additional_factions

        logger.debug("Raw faction content:")
        for faction in factions:
            logger.debug(f"Faction {faction['name']}:\n{faction['content']}")

        metadata = _build_faction_metadata(factions)
        doc_builder = DocumentationBuilder()
        faction_content = ""

        for faction in factions:
            faction_content += f"## {faction['name']}\n\n"
            faction_content += f"**Creature Type:** {faction['creature_type']}\n\n"
            faction_content += f"**Primary Goal:** {faction['goal']}\n\n"
            faction_content += f"**Key Obstacle:** {faction['obstacle']}\n\n"
            faction_content += f"**Faction Content:**\n{faction['content']}\n\n"
            if 'members' in faction:
                faction_content += "**Faction Members:**\n"
                for role, description in faction['members'].items():
                    faction_content += f"- **{role}:** {description}\n"
            if 'leader' in faction:
                faction_content += f"\n**Faction Leader/Goal:**\n{faction['leader']}\n\n"
            if 'challenges' in faction:
                faction_content += "**Faction Challenges:**\n"
                for challenge in faction['challenges']:
                    faction_content += f"- {challenge}\n"
            faction_content += "\n---\n\n"  # Adds a divider between factions

        # Write all factions to a single file
        doc_builder.write_section("factions", faction_content)

        logger.info("✅ Faction generation complete!")
        return {
            "content": faction_content,
            "metadata": metadata
        }
    except Exception as e:
        logger.error(f"Faction generation failed: {str(e)}")
        return {"error": str(e)}


def _extract_present_day_faction(history_content: str, metadata: Dict[str, Any], model: str) -> Dict[str, Any]:
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


def _generate_present_day_content(metadata: Dict[str, Any], name: str, history: str, model: str) -> str:
    prompt = FACTION_PRESENT_DAY_PROMPT.format(
        name=name, history=history,
        builders=metadata.get("builders", "Unknown"),
        original_purpose=metadata.get("original_purpose", "Unknown"),
        current_state=metadata.get("current_state", "Unknown"),
        ruin_cause=metadata.get("ruin_cause", "Unknown")
    )
    try:
        response = generate_with_retry(prompt=prompt, model=model, temperature=0.7, top_p=0.9)
        return extract_solution(response.get("response", ""))
    except Exception as e:
        logger.warning(f"Using fallback content for {name}: {str(e)}")
        return f"Raw generation failed for {name}"


def _generate_additional_factions(model: str, history: str) -> List[Dict[str, Any]]:
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
    details = {
        "name": generate_random_name(),
        "goal": random.choice(tables.FACTION_TABLES["goal"]),
        "obstacle": random.choice(tables.FACTION_TABLES["obstacle"]),
        "impulse": random.choice(tables.FACTION_TABLES["impulse"]),
        "size": random.choice(tables.FACTION_TABLES["size"]),
        "creature_type": random.choice(tables.FACTION_TABLES["creature_type"])
    }
    prompt = FACTION_BACKGROUND_PROMPT.format(name=details['name'], history=history, traits=str(details))
    response = generate_with_retry(prompt, model, temperature=0.7)
    return {**details, "content": extract_solution(response.get("response", ""))}


def _build_faction_metadata(factions: List[Dict[str, Any]]) -> Dict[str, Any]:
    return {
        "generated_at": datetime.now().isoformat(),
        "num_factions": len(factions),
        "primary_goals": list(set(f["goal"] for f in factions)),
        "creature_types": list(set(f["creature_type"] for f in factions))
    }
