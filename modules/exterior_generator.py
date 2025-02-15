import random
import logging
import re
from typing import Dict, Any, Optional
from modules import tables
from modules.doc_writer import write_section  # Updated import
from ollama_manager import generate_with_retry  # Updated import

logger = logging.getLogger(__name__)


def sanitize(text: str) -> str:
    """Robust content cleaning that preserves Markdown syntax."""
    # Remove internal <think>...</think> sections
    cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
    # Allow markdown characters (# and *) in addition to the other punctuation.
    cleaned = re.sub(r'[^\w\s.,!?\-:\'\"#*]', '', cleaned)
    # Normalize newlines: collapse three or more newlines into two newlines.
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()


def generate_exterior(model: str, history_content: str, faction_content: str) -> Dict[str, Any]:
    """Generate dungeon exterior description with integrated validation."""
    try:
        logger.info("Starting exterior generation")

        # Validate required tables
        _validate_exterior_tables()

        # Create components (faction_content is used only in metadata)
        components = _create_components(history_content, faction_content)
        descriptions = _generate_component_descriptions(model, components, history_content)

        result = {
            "content": "\n\n".join(descriptions.values()),
            "metadata": {
                "components": {k: v[1] for k, v in components.items()},
                "sources": {
                    "history": history_content[:200] + "..." if len(history_content) > 200 else history_content,
                    "factions": faction_content[:200] + "..." if len(faction_content) > 200 else faction_content
                }
            }
        }

        # Write the exterior section to an exterior.md file.
        write_section("exterior", result["content"])

        return result

    except Exception as e:
        logger.error(f"Exterior generation failed: {str(e)}")
        return {"error": str(e)}


def _validate_exterior_tables() -> None:
    """Ensure required tables exist and are populated."""
    required_tables = {
        "environment": 3,  # Minimum 3 options
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

    # Path
    path = random.choice(tables.EXTERIOR_TABLES["path"])
    if path == "River":
        detail = random.choice(tables.EXTERIOR_TABLES.get("river_details", ["murmuring waters"]))
        path = f"{path} ({detail})"
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


def _generate_component_descriptions(model: str, components: Dict, history: str) -> Dict[str, str]:
    """Generate descriptions using Ollama service."""
    descriptions = {}

    for key, (name, value) in components.items():
        try:
            prompt = _build_component_prompt(name, value, history)
            response = generate_with_retry(
                prompt=prompt,
                model=model,
                temperature=0.85,
                top_p=0.9
            )

            if not response or not response.get("response"):
                raise ValueError(f"Empty response for {name}")

            descriptions[name] = sanitize(response["response"])
            logger.info(f"Generated {name} description")

        except Exception as e:
            logger.warning(f"Failed to generate {name}: {str(e)}")
            descriptions[name] = f"{name} description unavailable"

    return descriptions


def _build_component_prompt(component_name: str, component_value: str, history: str) -> str:
    """Construct context-aware prompts."""
    prompts = {
        "Environment": f"""Describe a {component_value} environment surrounding a dark fantasy dungeon. 

Context: {history}""",

        "Path": f"""Detail a {component_value} leading to a dungeon. 

Context: {history}""",

        "Landmark": f"""Describe a landmark near the dungeon marked by {component_value}.

Context: {history}""",

        "Secondary Entrance": f"""Describe a secret entrance: {component_value}.

Historical context: {history}""",

        "Antechamber": f"""Describe an antechamber: {component_value}. 

Dungeon history: {history}"""
    }

    return prompts.get(component_name, f"Describe the {component_name}: {component_value}")
