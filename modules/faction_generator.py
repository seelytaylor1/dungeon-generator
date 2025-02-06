import random
import logging
from typing import Dict, Any, List, Optional
from modules import tables
from modules.output_writer import OutputSanitizer
from ollama_manager import generate_with_retry  # Updated import

logger = logging.getLogger(__name__)

def generate_factions(model: str, history_content: str) -> Dict[str, Any]:
    """Generate dungeon factions using configured model"""
    try:
        num_factions = random.randint(1, 3)
        logger.info(f"Generating {num_factions} faction(s)")

        factions = []
        for i in range(num_factions):
            faction = _generate_single_faction(model, history_content, i+1)
            if faction:
                factions.append(faction)

        return {
            "num_factions": len(factions),
            "factions": factions
        }

    except Exception as e:
        logger.error(f"Faction generation failed: {str(e)}")
        return {"error": str(e)}

def _generate_single_faction(model: str, history: str, index: int) -> Optional[Dict]:
    """Generate a single faction with retry logic"""
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
            "content": OutputSanitizer.sanitize(response.get("response", ""))
        }

    except Exception as e:
        logger.error(f"Failed to generate faction {index}: {str(e)}")
        return None

def _assemble_faction_details() -> Dict[str, str]:
    """Assemble faction components from tables with validation"""
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
    """Create structured generation prompt"""
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
- 2-3 sentence description of their current activities"""

