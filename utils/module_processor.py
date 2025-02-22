# module_processor.py
import logging
import importlib
import asyncio
import random


async def process_module(module_info, output_data, config, args):
    skip_modules = ['history', 'faction', 'exterior', 'dungeon_content']
    if args.debug and module_info['name'] in skip_modules:
        logging.info(f"⏩ Skipping {module_info['name']} in debug mode")
        return

    module_name = module_info['name']
    function_name = module_info['function']
    default_model = config['models']['default']
    max_retries = module_info.get('retries', 1)
    timeout = module_info.get('timeout', 400)

    dependencies = module_info.get('depends_on', [])
    missing_deps = [dep for dep in dependencies if dep not in output_data]
    if missing_deps:
        logging.warning(f"⏭️ Skipping {module_name} - Missing dependencies: {missing_deps}")
        return

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
        'metadata': lambda: output_data.get('dungeon_map', {}).get('metadata') or {},
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
