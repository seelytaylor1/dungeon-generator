# modules/history_generator.py

import time
import requests
import random
import logging
from .shared import tables
from .shared.output_writer import sanitize_output, register_handler

def generate_history(model, history_content=None):
    try:
        while True:
            logging.info("📜 Starting adventure site history generation...")

            # Randomly select elements from your adventure site tables
            logging.info("🎲 Rolling for history components...")
            history = random.choice(tables.DUNGEON_TABLES["history"])
            logging.info(f"🏛️ History Base selected: {history}")
            modifier = random.choice(tables.DUNGEON_TABLES["modifier"])
            purpose = random.choice(tables.DUNGEON_TABLES["purpose"])
            logging.info(f"🛠️ Original Purpose selected: {modifier} {purpose}")
            ruin = random.choice(tables.DUNGEON_TABLES["ruin"])
            logging.info(f"💥 Cause of Ruin selected: {ruin}")
            present = random.choice(tables.DUNGEON_TABLES["present"])
            logging.info(f"🔮 Present Purpose selected: {present}")

            # Randomly select faction details for the original builders
            faction_creature_type = random.choice(tables.FACTION_TABLES["creature_type"])
            logging.info(f"👥 Faction Creature Type selected: {faction_creature_type}")
            faction_impulse = random.choice(tables.FACTION_TABLES["impulse"])
            logging.info(f"💡 Faction Impulse selected: {faction_impulse}")

            # Initialize content dictionary
            content = {}

            # Agent 0: Generate original builders
            logging.info("🏗️ Agent 0: Creating original builders...")
            agent0_prompt = f"""Create a brief description of the original builders of the adventure site. Use the following details:

- Creature Type: {faction_creature_type}
- Impulse: {faction_impulse}

Provide names and a concise background of who built the adventure site and their primary motivations. Limit your response to one paragraph."""

            agent0_response = generate_paragraph(model, agent0_prompt)
            builders_description = agent0_response.strip()
            time.sleep(2)

            # Agent 1: Generate ancient history (Paragraph 1)
            logging.info("🖋️ Agent 1: Writing ancient history...")
            agent1_prompt = f"""Provide a factual recounting of the adventure site's ancient history in one concise paragraph. Include the following:

- Builders: {builders_description}
- History: {history}
- Original Purpose: {modifier} {purpose}

Describe the inception, significance, and initial use of the location, focusing on key events and specifics without embellishment. Limit your response to one paragraph."""

            agent1_response = generate_paragraph(model, agent1_prompt)
            content['Paragraph 1'] = agent1_response.strip()
            time.sleep(2)

            # Agent 2: Generate cause of ruin (Paragraph 2)
            logging.info("🖋️ Agent 2: Writing cause of ruin...")
            agent2_prompt = f"""In one concise paragraph, factually recount the events that led to the builders' fall into ruin. Focus on key details without embellishment. Use the following information:

- Cause of Ruin: {ruin}

Earlier History:
{agent1_response}

Continue the recounting, limiting your response to one paragraph. Do not repeat previous paragraphs."""

            agent2_response = generate_paragraph(model, agent2_prompt)
            content['Paragraph 2'] = agent2_response.strip()
            time.sleep(2)

            # Agent 3: Generate present state (Paragraph 3)
            logging.info("🖋️ Agent 3: Writing present state...")
            agent3_prompt = f"""Provide a factual description of the adventure site's current state in one concise paragraph. Focus on who occupies the adventure site now and their purpose for being there. Name them. Include key details about its present use or perception. Use the following information:

- Present Purpose: {present}

Earlier History:
{agent1_response}
{agent2_response}

Limit your response to one paragraph. Do not repeat previous paragraphs."""

            agent3_response = generate_paragraph(model, agent3_prompt)
            content['Paragraph 3'] = agent3_response.strip()
            time.sleep(2)

            # Display the results from Agents 0-3
            full_history = f"{builders_description}\n\n{agent1_response}\n\n{agent2_response}\n\n{agent3_response}"
            print("\n📝 **Adventure Site History (Draft)**\n")
            print(full_history)
            print("\n")

            # Prompt the user for input
            print("What would you like to do next?")
            print("1. Start over")
            print("2. Use a summarization agent")
            print("3. Keep going")
            print("4. Provide your own adventure site history")
            user_choice = input("Enter the number of your choice: ").strip()

            if user_choice == '1':
                logging.info("🔄 User chose to start over.")
                continue  # Restart the loop to generate history again
            elif user_choice == '2':
                logging.info("📝 User chose to use a summarization agent.")
                # Agent 4: Summarization agent
                summary_prompt = f"""Summarize the adventure site's history into one concise paragraph that captures the essential facts and people. Ensure clarity and brevity.

Adventure Site History:
{full_history}

Provide the summary below."""
                summary_response = generate_paragraph(model, summary_prompt)
                final_history = summary_response.strip()
                break
            elif user_choice == '3':
                logging.info("➡️ User chose to keep going.")
                # Agent 4: Review and refine entire history
                logging.info("🔍 Agent 4: Reviewing and refining the history...")
                agent4_prompt = f"""Review and refine the entire adventure site history below for clarity and conciseness. Ensure each paragraph is factual and limited to one concise paragraph.

Adventure Site History:
{full_history}

Provide the revised history below."""
                agent4_response = generate_paragraph(model, agent4_prompt)
                final_history = agent4_response.strip()
                break
            elif user_choice == '4':
                logging.info("✏️ User chose to provide their own adventure site history.")
                print("Please enter your adventure site history. When you are finished, enter an empty line.")
                user_history_lines = []
                while True:
                    line = input()
                    if line == '':
                        break
                    user_history_lines.append(line)
                user_history = '\n'.join(user_history_lines)
                final_history = user_history.strip()

                # Optionally allow the user to provide metadata
                print("Would you like to provide key aspects (metadata) for your adventure site history? (yes/no)")
                provide_metadata = input().strip().lower()

                if provide_metadata in ('yes', 'y'):
                    # Prompt for each metadata item
                    print("Please enter the following details (or press Enter to leave empty):")
                    history_base = input("History Base: ").strip()
                    original_purpose = input("Original Purpose: ").strip()
                    cause_of_ruin = input("Cause of Ruin: ").strip()
                    present_purpose = input("Present Purpose: ").strip()
                    metadata = {
                        "History Base": history_base,
                        "Original Purpose": original_purpose,
                        "Cause of Ruin": cause_of_ruin,
                        "Present Purpose": present_purpose
                    }
                else:
                    metadata = {
                        "History Base": "",
                        "Original Purpose": "",
                        "Cause of Ruin": "",
                        "Present Purpose": ""
                    }
                break  # Exit the loop
            else:
                print("Invalid choice. Please enter 1, 2, 3, or 4.")
                continue  # Re-prompt if invalid input

        # <-- Move the following lines outside the while loop
        logging.info("✅ Adventure site history generation complete!")

        # If metadata is not set (from options 1-3), use the rolled metadata
        if 'metadata' not in locals():
            metadata = {
                "Builders": builders_description,
                "Faction Creature Type": faction_creature_type,
                "Faction Impulse": faction_impulse,
                "History Base": history,
                "Original Purpose": f"{modifier} {purpose}",
                "Cause of Ruin": ruin,
                "Present Purpose": present
            }

        return {
            "content": final_history,
            "metadata": metadata
        }

    except Exception as e:
        logging.exception("❌ Adventure site history generation failed")
        return {"error": str(e)}

def generate_paragraph(model, prompt):
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.7,
                "top_p": 0.9,
                "max_tokens": 250
            }
        },
        timeout=120
    )
    response.raise_for_status()
    return sanitize_output(response.json()["response"])

# Register the handler for the History section
def history_handler(data, f):
    if data.get('content'):
        f.write("## History\n\n")
        f.write(f"{data['content']}\n\n")
        if 'metadata' in data:
            f.write("### Key Aspects\n")
            for k, v in data['metadata'].items():
                if v:
                    f.write(f"- **{k}**: {v}\n")
            f.write("\n")

register_handler("History", history_handler)
