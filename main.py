import logging
import json
import importlib
from ollama_manager import initialize_service, check_model_installed
from modules.shared.output_writer import write_markdown

# Include emojis in the format and set logging level to INFO
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    try:
        with open("config.json", "r") as config_file:
            config = json.load(config_file)

        if not initialize_service():
            logging.error("❌ Failed to initialize Ollama")
            return

        model_name = config["models"]["default"]
        if not check_model_installed(model_name):
            logging.error(f"❌ Model '{model_name}' not installed. Run 'ollama pull {model_name}' first")
            return

        output_data = {}
        for module_info in sorted(config["modules"], key=lambda x: x["priority"]):
            module_name = module_info["name"]
            module_function_name = module_info["function"]
            module_model = module_info.get("model", model_name)
            num_dice = module_info.get("num_dice", 11)  # Default to 11 if not specified

            module = importlib.import_module(f"modules.{module_name}_generator")
            module_function = getattr(module, module_function_name)

            # Fetch history and faction content if available
            history_content = output_data.get("History", {}).get("content", "")
            faction_content = ""
            if "Faction" in output_data:
                factions = output_data["Faction"]
                # Concatenate faction content
                faction_descriptions = [faction['content'] for faction in factions['factions']]
                faction_content = "\n\n".join(faction_descriptions)

            logging.info(f"🚀 Starting generation for module: {module_name.capitalize()}")

            # Pass required parameters to the module function
            if module_name == "exterior":
                result = module_function(module_model, history_content, faction_content)
            elif module_name == "dungeon_map":
                # Pass num_dice to the dungeon_map function
                result = module_function(num_dice)
            else:
                result = module_function(module_model, history_content)

            if result is None:
                logging.error(f"❌ {module_name.capitalize()} generation failed: No result returned.")
                continue

            if 'error' in result:
                logging.error(f"❌ {module_name.capitalize()} generation failed: {result['error']}")
                continue

            output_data[module_name.replace("_", " ").title()] = result  # Ensure consistency
            logging.info(f"✅ {module_name.capitalize()} generated successfully!")

        write_markdown(config["output"]["file"], output_data)
        logging.info(f"📝 Documentation generated: {config['output']['file']}")

    except Exception as e:
        logging.exception("💥 An unexpected error occurred:")

if __name__ == "__main__":
    main()
