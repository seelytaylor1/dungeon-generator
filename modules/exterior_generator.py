# exterior_generator.py
import random
import logging
import re
from datetime import datetime
from typing import Dict, Any
from modules import tables
from utils.doc_writer import DocumentationBuilder
from utils.ollama_manager import generate_with_retry
from modules.prompts import EXTERIOR_PROMPTS

logger = logging.getLogger(__name__)


def extract_sections(text: str) -> Dict[str, str]:
    """Extracts sections based on Markdown headers from LLM response."""
    sections = {}
    current_section = None
    section_content = []

    for line in text.split('\n'):
        header_match = re.match(r'^##\s+(.+)$', line.strip())
        if header_match:
            if current_section:
                sections[current_section] = '\n'.join(section_content).strip()
            current_section = header_match.group(1)
            section_content = []
        elif current_section:
            section_content.append(line.strip())

    if current_section:
        sections[current_section] = '\n'.join(section_content).strip()

    return sections


def _validate_exterior_tables() -> None:
    """Ensure required tables exist and are populated."""
    required_tables = {
        "environment": 3,
        "path": 2,
        "landmark": 2,
        "secondary_entrance_location": 2,
        "secondary_entrance_destination": 2,
        "antechamber": 2
    }
    for table, min_entries in required_tables.items():
        if table not in tables.EXTERIOR_TABLES:
            raise ValueError(f"Missing EXTERIOR_TABLES entry: {table}")
        if len(tables.EXTERIOR_TABLES[table]) < min_entries:
            raise ValueError(f"EXTERIOR_TABLES[{table}] needs at least {min_entries} entries")


def _create_components(history: str, factions: str) -> Dict[str, tuple]:
    """Create exterior components with smart selection logic."""
    components = {}

    # Environment
    env = random.choice(tables.EXTERIOR_TABLES["environment"])
    if env == "Re-roll twice and combine":
        env1 = random.choice([e for e in tables.EXTERIOR_TABLES["environment"] if e != env])
        env2 = random.choice([e for e in tables.EXTERIOR_TABLES["environment"] if e not in [env, env1]])
        env = f"{env1}/{env2}"
    components["environment"] = ("Environment", env)

    # Path - Incorporate extra details for "Patrolled" type
    path = random.choice(tables.EXTERIOR_TABLES["path"])
    if path.startswith("Patrolled"):
        patrol_detail = random.choice(tables.EXTERIOR_TABLES["path_patrolled"])
        path = f"{path} {patrol_detail}"
    components["path"] = ("Path", path)

    # Landmark
    components["landmark"] = ("Landmark", random.choice(tables.EXTERIOR_TABLES["landmark"]))

    # Secondary Entrance
    loc = random.choice(tables.EXTERIOR_TABLES["secondary_entrance_location"])
    dest = random.choice(tables.EXTERIOR_TABLES["secondary_entrance_destination"])
    components["secondary_entrance"] = ("Secondary Entrance", f"{loc} leading to {dest}")

    # Antechamber
    components["antechamber"] = ("Antechamber", random.choice(tables.EXTERIOR_TABLES["antechamber"]))

    return components


def generate_exterior(model: str, history_content: str, faction_content: str) -> Dict[str, Any]:
    """Generate dungeon exterior with single LLM call."""
    try:
        logger.info("🌅 Starting exterior generation...")
        _validate_exterior_tables()
        components = _create_components(history_content, faction_content)

        # Build consolidated prompt
        prompt = EXTERIOR_PROMPTS["CONSOLIDATED"].format(
            components={k: v[1] for k, v in components.items()},
            history=history_content,
            factions=faction_content
        )

        # Single LLM call
        response = generate_with_retry(
            prompt=prompt,
            model=model,
            temperature=0.8,
            top_p=0.85
        )

        if not response or not response.get("response"):
            raise ValueError("Empty response from LLM")

        # Parse sections from response
        descriptions = extract_sections(response["response"])
        required_sections = ["Environment", "Path", "Landmark", "Secondary Entrance", "Antechamber"]

        # Validate all sections present
        for section in required_sections:
            if section not in descriptions:
                raise ValueError(f"Missing section in response: {section}")

        result = {
            "content": "\n\n".join([f"## {k}\n{v}" for k, v in descriptions.items()]),
            "metadata": {
                "components": {k: v[1] for k, v in components.items()},
                "generated_at": datetime.now().isoformat()
            }
        }

        doc_builder = DocumentationBuilder()
        doc_builder.write_section("exterior", result["content"])
        logger.info("✅ Exterior generation complete!")
        return result

    except Exception as e:
        logger.error(f"Exterior generation failed: {str(e)}")
        return {"error": str(e)}
