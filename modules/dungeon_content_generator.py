# dungeon_content_generator.py
import random
import logging
import os
import re
from typing import Dict, List, Any

from modules.tables import EXPERIENCE_TABLES, ENCOUNTER_TABLES
from ollama_manager import generate_with_retry
from modules.prompts import get_prompt, PROMPT_TEMPLATES

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


def generate_dungeon_content(
        metadata: Dict[str, Any],
        history_content: str,
        faction_content: str,
        model: str = "openthinker:7b"
) -> Dict[str, Any]:
    try:
        logger.info("🏰 Starting dungeon generation...")
        validate_tables()

        # Cache the summarized history once
        summarized_history = _generate_summary(history_content, "history_summary", model)
        logger.debug(f"Cached Summarized History: {summarized_history}")

        # Cache the summarized faction once
        summarized_faction = _generate_summary(faction_content, "faction_summary", model)
        logger.debug(f"Cached Summarized Faction: {summarized_faction}")

        batch_counts = {k: 0 for k in ENCOUNTER_RATIO}
        rooms = []

        for node in metadata.get('nodes', []):
            room_number = node.get('key', f"Room {len(rooms) + 1}")
            room_type = node.get('room_type', 'Chamber')
            logger.info(f"🚪 Processing {room_number} - {room_type}")
            logger.debug(f"Node data: {node}")

            # Select experience and encounter
            experience_type = random.choice(list(EXPERIENCE_TABLES.keys()))
            experience_desc = random.choice(EXPERIENCE_TABLES[experience_type])
            logger.debug(f"Selected experience: {experience_type} - {experience_desc}")

            encounter_type = _select_encounter(batch_counts)
            encounter_config = ENCOUNTER_COMPLEXITY[encounter_type]
            encounter_desc = random.choice(ENCOUNTER_TABLES[encounter_type])
            logger.info(f"|-- Encounter: {encounter_type} (max {encounter_config['max_features']} features)")

            # Use cached summaries in the prompt
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
                    "history_content": summarized_history,   # Cached history summary
                    "faction_summary": summarized_faction       # Cached faction summary
                }
            )

            logger.debug(f"LLM Prompt:\n{llm_prompt}")

            # Process LLM response as before
            logger.info("|-- Generating content...")
            try:
                raw_response = generate_with_retry(llm_prompt, model).get('response', '')
                logger.debug(f"Raw LLM Response:\n{raw_response}")
                parsed_room = _validate_llm_output(raw_response, room_number)
                logger.debug(f"Parsed Content: {parsed_room}")

                final_room = _perform_quality_control(
                    content=parsed_room,
                    max_features=encounter_config['max_features'],
                    experience_type=experience_type,
                    room_number=room_number,
                    room_type=room_type,
                    encounter_type=encounter_type,
                    encounter_desc=encounter_desc,
                    history_content=summarized_history,
                    faction_content=summarized_faction,
                    experience_desc=experience_desc
                )
                logger.info(f"|-- Quality Control applied for {room_number}")

                rooms.append({
                    'room_number': room_number,
                    'type': room_type,
                    'content': final_room,
                    'experience': f"{experience_type}: {experience_desc}",
                    'encounter': encounter_type
                })

                logger.info(f"✅ Completed {room_number} | Exp: {experience_type} | Enc: {encounter_type}\n")

            except Exception as e:
                logger.error(f"❌ Failed {room_number}: {str(e)}")
                logger.error("Problematic content:\n...")
                continue

        return {
            'rooms': rooms,
            'stats': _calculate_stats(rooms),
            'batch_progress': batch_counts
        }

    except Exception as e:
        logger.error(f"🔥 Critical failure: {str(e)}")
        return {'error': str(e)}


def _generate_summary(content: str, template_key: str, model: str) -> str:
    """Generate a summary using a template and cache only the solution text."""
    try:
        template = PROMPT_TEMPLATES.get(template_key)
        if not template:
            raise ValueError(f"Missing template: {template_key}")

        formatted_prompt = template.format(
            history_content=content if "history" in template_key else "",
            faction_content=content if "faction" in template_key else ""
        )
        response = generate_with_retry(formatted_prompt, model)
        full_response = response.get('response', '').strip()

        # Try to extract only the solution text between the markers.
        pattern = re.compile(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', re.DOTALL)
        match = pattern.search(full_response)
        if match:
            summary_text = match.group(1).strip()
        else:
            # If solution markers are absent, remove chain-of-thought markers.
            summary_text = full_response.replace("<|begin_of_thought|>", "") \
                .replace("<|end_of_thought|>", "").strip()
        return summary_text

    except Exception as e:
        logger.error(f"Summary generation failed: {str(e)}")
        return "Summary unavailable."


def _select_encounter(batch_counts: Dict[str, int]) -> str:
    """Maintain 2:2:2:1 ratio per batch."""
    available = [e for e, max_count in ENCOUNTER_RATIO.items()
                 if batch_counts[e] < max_count]

    if not available:
        available = list(ENCOUNTER_RATIO.keys())
        for k in batch_counts:
            batch_counts[k] = 0
        logger.warning("🔄 Resetting encounter batch counts")

    choice = random.choice(available)
    batch_counts[choice] += 1
    logger.debug(f"Selected encounter: {choice} (Counts: {batch_counts})")
    return choice


def _validate_llm_output(text: str, room_number: str) -> List[str]:
    """
    Extracts the content between <|begin_of_solution|> and <|end_of_solution|>
    if present. Otherwise, returns the full text wrapped in a list.
    No additional formatting is performed here.
    """
    pattern = re.compile(r'<\|begin_of_solution\|>(.*?)<\|end_of_solution\|>', re.DOTALL)
    match = pattern.search(text)
    if match:
        solution = match.group(1).strip()
    else:
        solution = text.strip()
    return [solution]


def _perform_quality_control(
        content: List[str],
        max_features: int,
        experience_type: str,
        room_number: str,
        room_type: str,
        encounter_type: str,
        encounter_desc: str,
        history_content: str,
        faction_content: str,
        experience_desc: str  # new parameter passed from caller
) -> List[str]:
    """
    Passes the original room content to a second LLM step for quality control.
    The QC prompt instructs the LLM to output the room in the strict desired format.
    Returns the final reviewed output as a list of lines.
    """
    original_content = "\n".join(content)
    qc_prompt = get_prompt(
        template_name="room_quality_control",
        context={
            "room_number": room_number,
            "room_type": room_type,
            "original_content": original_content,
            "experience_type": experience_type,
            "experience_desc": experience_desc,  # now included
            "encounter_type": encounter_type,
            "encounter_desc": encounter_desc,
            "max_features": max_features,
            "history_content": history_content,
            "faction_content": faction_content
        }
    )
    logger.debug(f"Room {room_number} QC prompt input:\n{qc_prompt}")

    try:
        qc_result = generate_with_retry(
            prompt=qc_prompt,
            model="openthinker:7b",
            temperature=0.7,
            top_p=0.9
        )
        if qc_result and 'response' in qc_result:
            qc_generated = qc_result['response']
            logger.debug(f"Room {room_number} raw QC output:\n{qc_generated}")
            final_content = _validate_llm_output(qc_generated, room_number)
            logger.debug(f"Room {room_number} QC reviewed output:\n{final_content}")
            return final_content
        else:
            raise ValueError("Invalid QC LLM response format")
    except Exception as e:
        logger.error(f"Quality Control generation failed for Room {room_number}: {str(e)}")
        # If QC fails, return the original content unchanged
        return content


def _write_map_to_file(rooms: List[Dict[str, Any]]) -> None:
    """Generate markdown output with proper section merging."""
    md = ["# Dungeon Content\n"]

    # Add core rooms section
    for room in rooms:
        md.extend([
            f"### {room['room_number']}: {room['type']}",
            *room['content'],
            f"*Experience Focus*: {room['experience']}",
            f"*Encounter Type*: {room['encounter']}",
            "---\n"
        ])

    md.append("\n## Appendix\n")
    md.extend(_generate_appendix(rooms))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))


def _generate_appendix(rooms: List[Dict[str, Any]]) -> List[str]:
    """Generate standardized appendix sections."""
    return [
        "### Experience Distribution",
        *["- " + line for line in _format_experience_stats(rooms)],
        "\n### Encounter Overview",
        *["- " + line for line in _format_encounter_stats(rooms)]
    ]


def _calculate_stats(rooms: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate generation statistics."""
    counts = {
        'encounters': {},
        'experience': {},
        'avg_features': round(
            sum(len(r['content']) - 1 for r in rooms) / len(rooms), 1) if rooms else 0
    }

    for room in rooms:
        counts['encounters'][room['encounter']] = counts['encounters'].get(room['encounter'], 0) + 1
        exp_str = room['experience']
        exp_type = exp_str.split(':')[0].strip() if ':' in exp_str else exp_str.strip()
        counts['experience'][exp_type] = counts['experience'].get(exp_type, 0) + 1

    return counts


# --- New functions added to fix formatting errors --- #

def _format_experience_stats(rooms: List[Dict[str, Any]]) -> List[str]:
    """
    Generate a list of strings representing the experience distribution.
    Each string is in the format: "ExperienceType: Count"
    """
    stats = {}
    for room in rooms:
        exp_str = room.get('experience', '')
        exp_type = exp_str.split(':')[0].strip() if ':' in exp_str else exp_str.strip()
        stats[exp_type] = stats.get(exp_type, 0) + 1
    return [f"{k}: {v}" for k, v in sorted(stats.items())]


def _format_encounter_stats(rooms: List[Dict[str, Any]]) -> List[str]:
    """
    Generate a list of strings representing the encounter distribution.
    Each string is in the format: "EncounterType: Count"
    """
    stats = {}
    for room in rooms:
        encounter = room.get('encounter', '').strip()
        stats[encounter] = stats.get(encounter, 0) + 1
    return [f"{k}: {v}" for k, v in sorted(stats.items())]
