# main.py
import logging
import json
import importlib
import asyncio
import random
from schema import Schema, And, Or, Optional, SchemaError
from ollama_manager import initialize_service, get_installed_models
from modules.doc_writer import merge_sections

# Configure logging globally
logging.basicConfig(
    level=logging.INFO,
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


async def process_module(module_info, output_data, config):
    module_name = module_info['name']
    function_name = module_info['function']
    default_model = config['models']['default']
    max_retries = module_info.get('retries', 1)
    timeout = module_info.get('timeout', 30)

    # Check dependencies
    dependencies = module_info.get('depends_on', [])
    missing_deps = [dep for dep in dependencies if dep not in output_data]
    if missing_deps:
        logging.warning(f"⏭️ Skipping {module_name} - Missing dependencies: {missing_deps}")
        return

    # Parameter resolution system
    param_resolvers = {
        'model': lambda: module_info.get('model', default_model),
        'history_content': lambda: output_data.get('history', {}).get('content', ''),
        'faction_content': lambda: "\n\n".join(
            f["content"] for f in output_data.get('faction', {}).get('factions', [])
        ),
        'exterior_content': lambda: output_data.get('exterior', {}).get('content', ''),
        'num_dice': lambda: module_info.get('num_dice', 11),
        'dice_rolls': lambda: [random.randint(1, 6) for _ in range(module_info.get('num_dice', 11))],
        'existing_data': lambda: output_data
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

            # Execute with timeout
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


def is_affirmative(response):
    return response.strip().lower() in ['yes', 'y']


def build_config():
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

    if not initialize_service():
        logging.error("❌ Failed to initialize Ollama service. Exiting.")
        return

    output_data = {}

    # User input handling
    generate_history = is_affirmative(input("📜 Generate history automatically? (yes/no): "))
    generate_faction = is_affirmative(input("🤼 Generate factions automatically? (yes/no): "))
    generate_exterior = is_affirmative(input("🌅 Generate exterior automatically? (yes/no): "))

    # Manual input collection
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

    # Module filtering
    filtered_modules = [
        mod for mod in config['modules']
        if not (
                (mod['name'] == 'history' and not generate_history) or
                (mod['name'] == 'faction' and not generate_faction) or
                (mod['name'] == 'exterior' and not generate_exterior)
        )
    ]

    # Process modules
    independent = []
    dependent = []
    for module in sorted(filtered_modules, key=lambda x: x['priority']):
        if module.get('depends_on'):
            dependent.append(module)
        else:
            independent.append(module)

    # Parallel processing for independent modules
    await asyncio.gather(*[
        process_module(mod, output_data, config)
        for mod in independent
    ])

    # Sequential processing for dependent modules
    for mod in dependent:
        await process_module(mod, output_data, config)

    # Merge individual section markdown files into final documentation.
    merge_sections(final_filename="documentation.md",
                   order=("history", "faction", "exterior", "dungeon_map"))

    # Optional: If any errors occurred, you could choose to not merge or flag the final document.
    if 'error' in output_data:
        logging.error("⛔ Some modules encountered errors. Please check the logs.")

if __name__ == "__main__":
    asyncio.run(main())
