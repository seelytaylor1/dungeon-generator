# main.py
import logging
import json
import importlib
import asyncio
import random
from schema import Schema, And, Or, Optional, SchemaError
from ollama_manager import initialize_service, get_installed_models
from modules.doc_writer import merge_sections
import argparse

# Debug content configuration
DEBUG_CONTENT = {
    'history': {
        'content': "Ancient tomb built by a forgotten civilization. Later occupied by bandits. Recently disturbed by treasure hunters.",
        'metadata': {'source': 'debug'}
    },
    'faction': {
        'content': "## Active Factions\n1. Bandit Clan: Wants to protect stolen goods\n2. Undead Spirits: Seek to punish raiders\n3. Archaeologists: Document the site",
        'metadata': {'source': 'debug'}
    },
    'exterior': {
        'content': "Crumbling stone entrance partially buried in sand. Animal tracks circle the area.",
        'metadata': {'source': 'debug'}
    },
    'dungeon_content': {
        'content': """## Dungeon Content
### 13. GRAND HALL
Stone dust in air. Faded murals. Cracked obsidian floor.
• Central Pillar: Bear claw marks (DC 14 Strength)
▶ Iron Brazier: Melted silver residue (22 gp)
• Collapsed Archway: Leads downward

### 7. RITUAL CHAMBER
Charred bones smell. Bloodstained altar. Flickering shadows.
• Sacrificial Knife: Blackened blade (15 gp)
▶ Hidden Cache: Behind loose stone (DC 12 Perception)
• Wall Inscriptions: Warning in dead language""",
        'metadata': {'source': 'debug'}
    }
}

# Configure argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-y', '--yes', action='store_true', help='Automatically select yes for all prompts')
parser.add_argument('-n', '--no', action='store_true', help='Automatically select no for all prompts')
parser.add_argument('-d', '--debug', action='store_true',
                    help='Populate with debug content and skip all generation')
args = parser.parse_args()

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

config_schema = Schema({
    'models': {
        'default': And(str, len),
        Optional('fallback'): Or(str, None)
    },
    'modules': [{
        'name': And(str, len),
        'function': And(str, len),
        'priority': int,
        Optional('model'): Or(str, None),
        Optional('num_dice'): int,
        Optional('required_params'): [str],
        Optional('depends_on'): [str],
        Optional('retries'): And(int, lambda n: n >= 0),
        Optional('timeout'): And(int, lambda n: n > 0)
    }],
    'output': {
        'file': And(str, len),
        Optional('sanitize'): bool
    }
})


def is_affirmative(response):
    return response.strip().lower() in ['yes', 'y', 'debug']


def get_input(prompt):
    if args.debug:
        print(f"{prompt} [debug mode auto-no]")
        return 'debug'
    if args.yes: return 'yes'
    if args.no: return 'no'
    return input(prompt).strip().lower()


async def process_module(module_info, output_data, config):
    # Only skip LLM-dependent modules
    skip_modules = ['history', 'faction', 'exterior', 'dungeon_content']
    if args.debug and module_info['name'] in skip_modules:
        logging.info(f"⏩ Skipping {module_info['name']} in debug mode")
        return

    # Original process_module implementation
    module_name = module_info['name']
    function_name = module_info['function']
    default_model = config['models']['default']
    max_retries = module_info.get('retries', 1)
    timeout = module_info.get('timeout', 400)

    # Dependencies check
    dependencies = module_info.get('depends_on', [])
    missing_deps = [dep for dep in dependencies if dep not in output_data]
    if missing_deps:
        logging.warning(f"⏭️ Skipping {module_name} - Missing dependencies: {missing_deps}")
        return

    # Parameter resolution system
    param_resolvers = {
        'model': lambda: module_info.get('model', config['models']['default']),
        'history_content': lambda: output_data.get('history', {}).get('content', ''),
        'history_metadata': lambda: output_data.get('history', {}).get('metadata'),
        'faction_content': lambda: output_data.get('faction', {}).get('content', ''),
        'world_context': lambda: (
            f"Dungeon History:\n{output_data.get('history', {}).get('content', '')}\n\n"
            f"Active Factions:\n{output_data.get('faction', {}).get('content', '')}"
        ),
        'exterior_content': lambda: output_data.get('exterior', {}).get('content', ''),
        'num_dice': lambda: module_info.get('num_dice', 11),
        'dice_rolls': lambda: [random.randint(1, 6) for _ in range(module_info.get('num_dice', 11))],
        'existing_data': lambda: output_data,
        'metadata': lambda: output_data.get('dungeon_map', {}).get('metadata') or {}
    }

    try:
        module = importlib.import_module(f"modules.{module_name}_generator")
        module_function = getattr(module, function_name)
    except (ImportError, AttributeError) as e:
        logging.error(f"❌ Module load error: {e}")
        return

    for attempt in range(1, max_retries + 1):
        try:
            params = {}
            for param in module_info.get('required_params', []):
                if param in param_resolvers:
                    params[param] = param_resolvers[param]()
                else:
                    logging.warning(f"⚠️ Unknown parameter: {param}")
                    params[param] = None

            logging.info(f"🚀 Processing {module_name} (attempt {attempt}/{max_retries})")

            if asyncio.iscoroutinefunction(module_function):
                result = await asyncio.wait_for(module_function(**params), timeout)
            else:
                result = module_function(**params)

            if not result or 'error' in result:
                raise ValueError(f"Module failed: {result.get('error', 'Unknown error')}")

            output_data[module_name] = result
            logging.info(f"✅ {module_name.title()} succeeded")
            return

        except Exception as e:
            if attempt == max_retries:
                logging.error(f"❌ {module_name} failed after {max_retries} attempts: {str(e)}")
                output_data['error'] = str(e)
            else:
                logging.warning(f"🔄 Retrying {module_name} ({attempt}/{max_retries})")
                await asyncio.sleep(1 * attempt)


def build_config():
    """Load and validate configuration from config.json."""
    try:
        with open("config.json") as f:
            config = json.load(f)
        return config_schema.validate(config)
    except (FileNotFoundError, json.JSONDecodeError, SchemaError) as e:
        logging.error(f"❌ Config error: {str(e)}")
        return None


async def main():
    config = build_config()
    if not config:
        return

    output_data = {}

    if args.debug:
        logging.info("🐛 DEBUG MODE ACTIVATED - USING DEFAULT CONTENT")
        output_data.update({
            'history': DEBUG_CONTENT['history'],
            'faction': DEBUG_CONTENT['faction'],
            'exterior': DEBUG_CONTENT['exterior']
        })
    else:
        if not DEBUG_CONTENT['faction'].get('content'):
            raise ValueError("Debug faction content missing required 'content' field")

        if not initialize_service():
            logging.error("❌ Failed to initialize Ollama service. Exiting.")
            return

        debug_choice = get_input("📜 Generate content automatically? (yes/no/debug): ")
        if debug_choice == 'debug':
            args.debug = True
            return await main()

        generate_history = args.yes or (not args.no and is_affirmative(debug_choice))
        generate_faction = args.yes or (not args.no and is_affirmative(debug_choice))
        generate_exterior = args.yes or (not args.no and is_affirmative(debug_choice))

        if not generate_history:
            output_data['history'] = {
                'content': input("Enter dungeon history:\n"),
                'metadata': {'source': 'manual'}
            }
        if not generate_faction:
            output_data['faction'] = {
                'factions': [{'content': input("Enter faction details:\n")}],
                'metadata': {'source': 'manual'}
            }
        if not generate_exterior:
            output_data['exterior'] = {
                'content': input("Enter exterior description:\n"),
                'metadata': {'source': 'manual'}
            }

    if not args.debug:
        # Model initialization
        models = config['models']
        installed_models = get_installed_models()

        if models['default'] not in installed_models:
            if fallback := models.get('fallback'):
                if fallback in installed_models:
                    logging.warning(f"⚠️ Using fallback model: {fallback}")
                    models['default'] = fallback
                else:
                    logging.error("❌ No valid models available")
                    return
            else:
                logging.error("❌ Default model not available")
                return

        # Module processing
        filtered_modules = [
            mod for mod in config['modules']
            if not (
                    (mod['name'] == 'history' and not generate_history) or
                    (mod['name'] == 'faction' and not generate_faction) or
                    (mod['name'] == 'exterior' and not generate_exterior)
            )
        ]

        independent = []
        dependent = []
        for module in sorted(filtered_modules, key=lambda x: x['priority']):
            if module.get('depends_on'):
                dependent.append(module)
            else:
                independent.append(module)

        await asyncio.gather(*[
            process_module(mod, output_data, config)
            for mod in independent
        ])

        for mod in dependent:
            await process_module(mod, output_data, config)

    # Always merge sections
    merge_sections(
        final_filename="documentation.md",
        order=("history", "faction", "exterior", "dungeon_map", "dungeon_content"),
        debug_content=DEBUG_CONTENT if args.debug else None
    )

    if args.debug:
        logging.info("🛠 DEBUG OUTPUT COMPLETE - GENERATED WITH DEFAULT CONTENT")
    elif 'error' in output_data:
        logging.error("⛔ Some modules encountered errors. Please check the logs.")


if __name__ == "__main__":
    asyncio.run(main())
