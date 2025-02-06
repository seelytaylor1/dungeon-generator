# main.py
import logging
import json
import importlib
import asyncio
import re
import random
from schema import Schema, And, Or, Optional, SchemaError
from ollama_manager import initialize_service, check_model_installed, get_installed_models
from modules.output_writer import write_markdown

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

# Enhanced configuration schema
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
    if not all(dep in output_data for dep in dependencies):
        logging.warning(f"⏭️ Skipping {module_name} - Missing dependencies: {dependencies}")
        return

    # Parameter resolution system
    param_resolvers = {
        'model': lambda: module_info.get('model', default_model),
        'history_content': lambda: output_data.get('history', {}).get('content', ''),
        'faction_content': lambda: "\n\n".join(
            f["content"] for f in output_data.get('faction', {}).get('factions', [])
        ),
        'num_dice': lambda: (
            logging.debug(f"🎲 Map using {module_info.get('num_dice', 11)} dice"),
            module_info.get('num_dice', 11)
        )[1],
        'dice_rolls': lambda: [
            random.randint(1, 6)
            for _ in range(module_info.get('num_dice', 11))
        ],
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
            # Build parameters
            params = {}
            for param in module_info.get('required_params', []):
                if param in param_resolvers:
                    params[param] = param_resolvers[param]()
                else:
                    logging.warning(f"⚠️ Unknown parameter: {param}")
                    params[param] = ""

            logging.info(f"🚀 Processing {module_name} (attempt {attempt}/{max_retries})")

            # Execute with timeout
            if asyncio.iscoroutinefunction(module_function):
                result = await asyncio.wait_for(module_function(**params), timeout)
            else:
                result = module_function(**params)

            if not result:
                raise ValueError("Empty response from module")

            output_data[module_name] = result
            logging.info(f"✅ {module_name.title()} succeeded")
            return

        except Exception as e:
            if attempt == max_retries:
                logging.error(f"❌ {module_name} failed after {max_retries} attempts: {str(e)}")
            else:
                logging.warning(f"🔄 Retrying {module_name} ({attempt}/{max_retries})")
                await asyncio.sleep(1 * attempt)


async def main():
    config = build_config()
    if not config:
        return

    # Ensure the Ollama service is running before proceeding.
    from ollama_manager import initialize_service  # Ensure we have the function imported.
    if not initialize_service():
        logging.error("❌ Failed to initialize Ollama service. Exiting.")
        return

    output_data = {}

    # Model initialization with fallback
    models = config['models']
    installed_models = get_installed_models()

    if models['default'] not in installed_models:
        fallback = models.get('fallback')
        if fallback and fallback in installed_models:
            logging.warning(f"⚠️ Using fallback model: {fallback}")
            models['default'] = fallback
        else:
            logging.error("❌ No valid models available")
            return

    # Process modules strategically
    independent = []
    dependent = []

    for module in sorted(config['modules'], key=lambda x: x['priority']):
        if not module.get('depends_on'):
            independent.append(module)
        else:
            dependent.append(module)

    # Process independent modules in parallel
    await asyncio.gather(*[
        process_module(mod, output_data, config)
        for mod in independent
    ])

    # Process dependent modules sequentially
    for mod in dependent:
        await process_module(mod, output_data, config)

    # Generate output with sanitization
    sanitize = config['output'].get('sanitize', True)
    write_markdown(
        filename=config['output']['file'],
        data=output_data,
        sanitize=sanitize
    )


def build_config():
    try:
        with open("config.json") as f:
            config = json.load(f)
        return config_schema.validate(config)
    except (FileNotFoundError, json.JSONDecodeError, SchemaError) as e:
        logging.error(f"❌ Config error: {str(e)}")
        return None


if __name__ == "__main__":
    asyncio.run(main())
