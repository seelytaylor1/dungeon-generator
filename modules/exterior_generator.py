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


def extract_solution(text: str) -> str:
    """
    Extracts and returns the text between <|begin_of_solution|> and <|end_of_solution|>.
    If these markers are not present, returns the entire text.
    """
    match = re.search(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_exterior(model: str, history_content: str, faction_content: str) -> Dict[str, Any]:
    """Generate dungeon exterior with integrated validation."""
    try:
        logger.info("🌅 Starting exterior generation...")

        # Validate required exterior tables exist
        _validate_exterior_tables()

        # Create exterior components (e.g., environment, path, landmark, etc.)
        components = _create_components(history_content, faction_content)

        # Generate detailed descriptions for each component using the LLM
        descriptions = _generate_component_descriptions(model, components, history_content)

        # Build result content by joining each component's section with headers
        result = {
            "content": "\n\n".join([
                f"## {name}\n{desc}" for name, desc in descriptions.items()
            ]),
            "metadata": {
                "components": {k: v[1] for k, v in components.items()},
                "generated_at": datetime.now().isoformat()
            }
        }
        doc_builder = DocumentationBuilder()
        # Write the complete exterior description to the markdown section
        doc_builder.write_section("exterior", result["content"])
        logger.info("✅ Exterior generation complete!")
        return result

    except Exception as e:
        logger.error(f"Exterior generation failed: {str(e)}")
        return {"error": str(e)}


def _build_component_prompt(component_name: str, component_value: str, history: str,
                            environment_context: str = "") -> str:
    """Construct prompts using centralized templates."""
    try:
        template = EXTERIOR_PROMPTS[component_name]
        return template.format(
            component_value=component_value,
            history=history,
            environment_context=environment_context
        )
    except KeyError:
        logger.warning(f"No template found for {component_name}")
        return f"Describe {component_name} with: {component_value} (History: {history})"


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


def _generate_component_descriptions(model: str, components: Dict[str, tuple], history: str) -> Dict[str, str]:
    """Generate descriptions for each exterior component using the LLM service."""
    descriptions = {}

    # Generate environment first
    env_prompt = _build_component_prompt("Environment", components["environment"][1], history)
    env_response = generate_with_retry(
        prompt=env_prompt,
        model=model,
        temperature=0.85,
        top_p=0.9
    )

    if not env_response or not env_response.get("response"):
        raise ValueError("Empty response for Environment")

    environment_description = extract_solution(env_response["response"])
    descriptions["Environment"] = environment_description
    logger.info("Generated Environment description")

    # Generate remaining components with environment context
    for key, (name, value) in components.items():
        if name == "Environment":
            continue  # Skip, already processed

        try:
            prompt = _build_component_prompt(name, value, history, environment_description)
            response = generate_with_retry(
                prompt=prompt,
                model=model,
                temperature=0.85,
                top_p=0.9
            )
            if not response or not response.get("response"):
                raise ValueError(f"Empty response for {name}")

            descriptions[name] = extract_solution(response["response"])
            logger.info(f"Generated {name} description")

        except Exception as e:
            logger.warning(f"Failed to generate {name}: {str(e)}")
            descriptions[name] = f"{name} description unavailable"

    return descriptions
