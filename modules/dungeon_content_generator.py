# dungeon_content_generator.py
import random
import logging
import os
import re
from typing import Dict, List, Any

from modules.tables import EXPERIENCE_TABLES, ENCOUNTER_TABLES
from utils.ollama_manager import generate_with_retry
from modules.prompts import get_prompt, PROMPT_TEMPLATES
from utils.doc_writer import DocumentationBuilder

logger = logging.getLogger(__name__)

# Configuration Constants
ENCOUNTER_RATIO = {
    'combat': 2,
    'treasure': 2,
    'skill challenge': 2,
    'set dressing': 1
}

ENCOUNTER_COMPLEXITY = {
    'combat': {'max_features': 1},
    'treasure': {'max_features': 2},
    'skill challenge': {'max_features': 1},
    'set dressing': {'max_features': 1}
}

OUTPUT_DIR = "docs"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dungeon_content.md")


def validate_tables() -> None:
    """Validate data tables."""
    if not all([isinstance(t, dict) for t in [EXPERIENCE_TABLES, ENCOUNTER_TABLES]]):
        raise ValueError("Invalid table format")
    for k in ENCOUNTER_COMPLEXITY:
        if 'max_features' not in ENCOUNTER_COMPLEXITY[k]:
            raise ValueError(f"Missing complexity config for {k}")


def _clean_room_content(content_lines: List[str]) -> List[str]:
    """Clean up markdown formatting in room content.
    
    Removes ** markers from heading lines (lines with # symbols).
    """
    cleaned_lines = []
    for line in content_lines:
        # If line contains a # symbol, remove any ** markers
        if '#' in line:
            # Remove ** markers
            line = line.replace('**', '')
        cleaned_lines.append(line)
    return cleaned_lines


def generate_dungeon_content(
        metadata: Dict[str, Any],
        history_content: str,
        faction_content: str,
        model: str = "openthinker:7b"
) -> Dict[str, Any]:
    try:
        logger.info("🏰 Starting dungeon generation...")
        validate_tables()

        # Validate input parameters
        if not history_content:
            logger.error("Missing history content")
            return {'error': 'History content is required'}
        
        if not faction_content:
            logger.error("Missing faction content")
            return {'error': 'Faction content is required'}
            
        if not metadata or not metadata.get('nodes'):
            logger.error("Missing or invalid metadata")
            return {'error': 'Valid metadata with nodes is required'}

        # Generate summaries
        logger.debug("Generating history summary...")
        summarized_history = _generate_summary(history_content, "history_summary", model)
        
        logger.debug("Generating faction summary...")
        summarized_faction = _generate_summary(faction_content, "faction_summary", model)

        # Validate summaries
        if summarized_history.startswith("Summary unavailable"):
            logger.error(f"Failed to generate history summary: {summarized_history}")
            return {'error': 'Failed to generate history summary'}
            
        if summarized_faction.startswith("Summary unavailable"):
            logger.error(f"Failed to generate faction summary: {summarized_faction}")
            return {'error': 'Failed to generate faction summary'}

        batch_counts = {k: 0 for k in ENCOUNTER_RATIO}
        rooms = []

        for node in metadata.get('nodes', []):
            room_number = node.get('key', f"Room {len(rooms) + 1}")
            room_type = node.get('room_type', 'Chamber')
            logger.info(f"🚪 Processing {room_number} - {room_type}")
            
            # Select experience and encounter
            experience_type = random.choice(list(EXPERIENCE_TABLES.keys()))
            experience_desc = random.choice(EXPERIENCE_TABLES[experience_type])
            
            encounter_type = _select_encounter(batch_counts)
            encounter_config = ENCOUNTER_COMPLEXITY[encounter_type]
            encounter_desc = random.choice(ENCOUNTER_TABLES[encounter_type])
            
            logger.info(f"|-- Encounter: {encounter_type} - {encounter_desc}")
            logger.info(f"|-- Experience: {experience_type} - {experience_desc}")

            # Generate initial room content
            llm_prompt = get_prompt(
                "room_description",
                {
                    "room_number": room_number,
                    "room_type": room_type,
                    "experience_type": experience_type,
                    "experience_desc": experience_desc,
                    "encounter_type": encounter_type,
                    "encounter_desc": encounter_desc,
                    "max_features": encounter_config['max_features'],
                    "history_summary": summarized_history,
                    "faction_summary": summarized_faction
                }
            )

            logger.debug(f"Room {room_number} prompt:\n{llm_prompt[:500]}...")

            try:
                raw_response = generate_with_retry(llm_prompt, model).get('response', '')
                
                logger.debug(f"Room {room_number} raw response:\n{raw_response[:500]}...")
                
                # Extract content between solution tags if present
                content = _extract_solution_content(raw_response)
                
                # Process the content into lines
                initial_room = [line for line in content.split('\n') if line.strip()]
                
                # If empty result, use a fallback
                if not initial_room:
                    logger.warning(f"|-- ⚠️ Empty content for {room_number}, using fallback")
                    initial_room = [
                        f"{room_number}. EMPTY CHAMBER",
                        "A bare chamber with cracked stone walls. Dust covers the floor, and cobwebs hang from the ceiling.",
                        "• Debris: Scattered stones and broken pottery.",
                        "▶ Inspection: Nothing of value can be found."
                    ]
                
                # Apply quality control step
                logger.info(f"|-- Applying quality control...")
                qc_prompt = get_prompt(
                    "room_quality_control",
                    {
                        "room_number": room_number,
                        "room_type": room_type,
                        "original_content": '\n'.join(initial_room),
                        "experience_type": experience_type,
                        "experience_desc": experience_desc,
                        "encounter_type": encounter_type,
                        "encounter_desc": encounter_desc,
                        "max_features": encounter_config['max_features'],
                        "history_content": summarized_history,
                        "faction_content": summarized_faction
                    }
                )
                
                qc_result = generate_with_retry(qc_prompt, model)
                
                if qc_result and 'response' in qc_result and qc_result['response'].strip():
                    # Use the extraction function to clean the response
                    qc_content = _extract_solution_content(qc_result['response'])
                    
                    # Process the cleaned content
                    final_room = [line for line in qc_content.split('\n') if line.strip()]
                    
                    # Only fall back if QC produced empty content
                    if not final_room:
                        logger.warning(f"|-- ⚠️ QC produced empty content, falling back to original")
                        final_room = initial_room
                else:
                    logger.warning(f"|-- ⚠️ QC generation failed, falling back to original")
                    final_room = initial_room
                
                # Clean content formatting
                final_room = _clean_room_content(final_room)
                
            except Exception as e:
                logger.error(f"|-- ❌ Generation failed: {str(e)}")
                final_room = [
                    f"{room_number}. EMPTY CHAMBER",
                    "A bare chamber with cracked stone walls. Dust covers the floor, and cobwebs hang from the ceiling.",
                    "• Debris: Scattered stones and broken pottery.",
                    "▶ Inspection: Nothing of value can be found."
                ]
            
            rooms.append({
                'room_number': room_number,
                'type': room_type,
                'content': final_room,
                'experience': f"{experience_type}: {experience_desc}",
                'encounter': encounter_type
            })

            logger.info(f"✅ Completed {room_number} | Exp: {experience_type} | Enc: {encounter_type}\n")

        # Process and write results
        final_content = "# Dungeon Content\n\n"
        for room in rooms:
            room_content = '\n'.join(room['content'])
            final_content += f"### {room['room_number']}: {room['type']}\n"
            final_content += f"{room_content}\n\n"
            final_content += f"**Experience**: {room['experience']}\n"
            final_content += f"**Encounter**: {room['encounter']}\n\n---\n\n"
        
        # Write using documentation builder
        doc_builder = DocumentationBuilder()
        doc_builder.write_section("dungeon_content", final_content)
        
        return {
            "content": final_content,
            "rooms": rooms,
            "stats": _calculate_stats(rooms)
        }
            
    except Exception as e:
        logger.error(f"🔥 Critical failure: {str(e)}")
        return {'error': str(e)}


def _extract_solution_content(text: str) -> str:
    """Extract content between solution markers and remove any stray markers."""
    try:
        # First attempt to extract content between tags
        solution_pattern = re.compile(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', re.DOTALL)
        match = solution_pattern.search(text)
        
        if match:
            content = match.group(1).strip()
        else:
            content = text.strip()
        
        # Clean up any remaining solution tags
        content = re.sub(r'<\|begin_of_solution\|>', '', content)
        content = re.sub(r'<\|end_of_solution\|>', '', content)
        
        return content
        
    except Exception as e:
        logger.error(f"Failed to extract solution content: {e}")
        # Make sure to clean any tags even in error cases
        cleaned = text.strip()
        cleaned = re.sub(r'<\|begin_of_solution\|>', '', cleaned)
        cleaned = re.sub(r'<\|end_of_solution\|>', '', cleaned)
        return cleaned


def _select_encounter(batch_counts: Dict[str, int]) -> str:
    """Weighted random selection of encounter type with balancing."""
    # Calculate weights
    weights = {}
    total_encounters = sum(batch_counts.values()) + 1  # Avoid divide by zero
    
    for encounter, weight in ENCOUNTER_RATIO.items():
        # Adjust weight by current distribution
        current_ratio = batch_counts.get(encounter, 0) / total_encounters
        # Invert ratio to favor less frequent encounter types
        adjusted_weight = weight * (1 - current_ratio)
        weights[encounter] = max(0.1, adjusted_weight)
    
    # Normalize weights
    total_weight = sum(weights.values())
    weights = {k: v / total_weight for k, v in weights.items()}
    
    # Convert to cumulative distribution
    cumulative = 0
    distribution = {}
    for k, v in weights.items():
        cumulative += v
        distribution[k] = cumulative
    
    # Select encounter
    r = random.random()
    for encounter, threshold in distribution.items():
        if r <= threshold:
            batch_counts[encounter] = batch_counts.get(encounter, 0) + 1
            return encounter
    
    # Fallback
    encounter = random.choice(list(ENCOUNTER_RATIO.keys()))
    batch_counts[encounter] = batch_counts.get(encounter, 0) + 1
    return encounter


def _generate_summary(content: str, template_name: str, model: str) -> str:
    """Generate summary content."""
    if not content:
        return "Summary unavailable: missing content"
    
    try:
        prompt = get_prompt(template_name, {"history_content": content, "faction_content": content})
        logger.debug(f"Summary prompt for {template_name}:\n{prompt[:500]}...")
        result = generate_with_retry(prompt, model)
        
        if not result or not result.get('response'):
            return "Summary unavailable: empty response"
            
        # Clean any potential solution tags from summaries as well
        summary = _extract_solution_content(result['response'])
        
        if result and 'response' in result:
            logger.debug(f"Summary response for {template_name}:\n{result['response'][:500]}...")
        else:
            logger.debug(f"Empty or invalid response for {template_name} summary")
        
        return summary
        
    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return f"Summary unavailable: {str(e)}"


def _calculate_stats(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate generation statistics."""
    counts = {
        'encounters': {},
        'experience': {},
        'avg_features': 0
    }

    for room in rooms:
        counts['encounters'][room['encounter']] = counts['encounters'].get(room['encounter'], 0) + 1
        
        exp_str = room['experience']
        exp_type = exp_str.split(':')[0].strip() if ':' in exp_str else exp_str.strip()
        counts['experience'][exp_type] = counts['experience'].get(exp_type, 0) + 1

        # Count features (lines starting with •)
        feature_count = sum(1 for line in room['content'] if line.strip().startswith('•'))
        counts['avg_features'] += feature_count
    
    if rooms:
        counts['avg_features'] = round(counts['avg_features'] / len(rooms), 1)
    
    return counts
