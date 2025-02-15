import random
import logging
import re
from datetime import datetime
from typing import Dict, Any, List
from modules import tables
from modules.doc_writer import write_section
from modules.name_generator import generate_random_name
from ollama_manager import generate_with_retry

logger = logging.getLogger(__name__)


def sanitize(text: str) -> str:
    """Universal content cleaner"""
    cleaned = re.sub(r'<\|.*?\|>', '', text, flags=re.DOTALL)
    cleaned = re.sub(r'\n#{2,}', '\n##', cleaned)  # Normalize headers
    return cleaned.strip()


def generate_factions(model: str, history_content: str) -> Dict[str, Any]:
    """Main faction generation controller"""
    try:
        logger.info("🤼 Starting faction generation...")

        factions = _generate_faction_set(model, history_content)
        metadata = _build_faction_metadata(factions)

        markdown_content = _build_faction_markdown(factions, metadata)
        write_section("faction", markdown_content)

        logger.info("✅ Faction generation complete!")
        return {
            "factions": factions,
            "metadata": metadata
        }

    except Exception as e:
        logger.error(f"Faction generation failed: {str(e)}")
        return {"error": str(e)}


def _generate_faction_set(model: str, history: str) -> List[Dict[str, Any]]:
    """Generate validated faction set with error resilience"""
    faction_count = random.randint(1, 3)
    logger.debug(f"Attempting to generate {faction_count} factions")

    factions = []
    for i in range(faction_count):
        try:
            faction = _generate_single_faction(model, history, i + 1)
            if faction and faction.get('content'):
                factions.append(faction)
        except Exception as e:
            logger.warning(f"Faction {i + 1} failed: {str(e)}")

    if not factions:
        raise RuntimeError("All faction generation attempts failed")
    return factions


def _generate_single_faction(model: str, history: str, index: int) -> Dict[str, Any]:
    """Generate individual faction with enhanced error handling"""
    details = _assemble_faction_details()
    prompt = _create_faction_prompt(details, history)

    logger.debug(f"Generating faction {index} with prompt:\n{prompt[:500]}...")  # Truncate for logs
    response = generate_with_retry(
        prompt=prompt,
        model=model,
        temperature=0.5,
        top_p=0.9
    )

    if not response or not response.get('response'):
        raise ValueError("Empty model response")

    raw_content = response['response'].strip()

    # Flexible solution extraction
    solution_match = re.search(
        r'<\|begin_of_solution\|>(.*?)(<\|end_of_solution\|>|$)',
        raw_content,
        re.DOTALL
    )

    if solution_match:
        content = sanitize(solution_match.group(1))
    else:
        logger.warning("Using full response as fallback content")
        content = sanitize(raw_content)

    return {
        **details,
        "content": content
    }


def _assemble_faction_details() -> Dict[str, str]:
    """Build faction details with generated name"""
    return {
        "name": generate_random_name(),
        "goal": random.choice(tables.FACTION_TABLES["goal"]),
        "obstacle": random.choice(tables.FACTION_TABLES["obstacle"]),
        "impulse": random.choice(tables.FACTION_TABLES["impulse"]),
        "size": random.choice(tables.FACTION_TABLES["size"]),
        "creature_type": random.choice(tables.FACTION_TABLES["creature_type"])
    }


def _create_faction_prompt(details: Dict[str, str], history: str) -> str:
    """Structured prompt with name enforcement"""
    return f"""Create a detailed fantasy faction description using this EXACT name: {details['name']}

Dungeon History Context:
{history}

Faction Elements:
- Goal: {details['goal']}
- Primary Obstacle: {details['obstacle']}
- Driving Impulse: {details['impulse']}
- Organization Size: {details['size']}
- Creature Type: {details['creature_type']}

Required Sections:
## Faction History
## Faction Leadership
## Current Activities
"""


def _build_faction_metadata(factions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate comprehensive metadata"""
    return {
        "generated_at": datetime.now().isoformat(),
        "num_factions": len(factions),
        "names": [f["name"] for f in factions],
        "creature_types": list(set(f["creature_type"] for f in factions)),
        "size_distribution": [f["size"] for f in factions],
        "common_goals": list(set(f["goal"] for f in factions))
    }


def _build_faction_markdown(factions: List[Dict[str, Any]], metadata: Dict[str, Any]) -> str:
    """Build complete faction documentation"""
    md = [
        "# Faction Documentation",
        f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
        "\n## Overview",
        f"**Number of Factions**: {metadata['num_factions']}",
        f"**Generated Names**: {', '.join(metadata['names'])}",
        f"**Creature Types**: {', '.join(metadata['creature_types'])}",
        f"**Common Goals**: {', '.join(metadata['common_goals'])}",
        "\n## Faction Details"
    ]

    for faction in factions:
        md.extend([
            f"\n### {faction['name']}",
            f"**Creature Type**: {faction['creature_type']}",
            f"**Core Goal**: {faction['goal']}",
            f"**Primary Obstacle**: {faction['obstacle']}",
            f"**Organization Size**: {faction['size']}",
            "\n#### Description",
            faction['content'],
            "\n---"
        ])

    return '\n'.join(md)
