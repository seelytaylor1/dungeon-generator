# main.py
import logging
import asyncio
from utils.cli import setup_arg_parser
from utils.config import build_config
from utils.constants import DEBUG_CONTENT
from utils.input_utils import get_input, is_affirmative
from utils.module_processor import process_module
from utils.doc_writer import DocumentationBuilder
from utils.ollama_manager import initialize_service, get_installed_models

# Setup logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

# Parse arguments
parser = setup_arg_parser()
args = parser.parse_args()


async def main():
    config = build_config()
    if not config:
        return

    output_data = {}

    if args.debug:
        logging.info("🐛 DEBUG MODE ACTIVATED - USING DEFAULT CONTENT")
        output_data.update(DEBUG_CONTENT)
    else:
        debug_choice = get_input("📜 Generate content automatically? (yes/no/debug): ", args)
        if debug_choice == 'debug':
            args.debug = True
            return await main()

        if not initialize_service():
            logging.error("❌ Failed to initialize Ollama service. Exiting.")
            return

        # Model availability check
        installed_models = get_installed_models()
        models = config['models']
        if models['default'] not in installed_models:
            if models.get('fallback') and models['fallback'] in installed_models:
                logging.warning(f"⚠️ Using fallback model: {models['fallback']}")
                models['default'] = models['fallback']
            else:
                logging.error("❌ No valid models available")
                return

        # Module generation decisions
        generation_decisions = {}
        for mod in config['modules']:
            if 'user_prompt' in mod:
                if args.yes:
                    decision = True
                elif args.no:
                    decision = False
                else:
                    response = get_input(f"{mod['user_prompt']} (yes/no): ", args)
                    decision = is_affirmative(response)
                generation_decisions[mod['name']] = decision

                if not decision:
                    output_data[mod['name']] = {
                        'content': input(f"Enter {mod['name'].replace('_', ' ')}:\n"),
                        'metadata': {'source': 'manual'}
                    }

        # Process modules
        filtered_modules = [mod for mod in config['modules'] if generation_decisions.get(mod['name'], True)]

        # Split modules into independent and dependent
        independent = []
        dependent = []
        for mod in sorted(filtered_modules, key=lambda x: x['priority']):
            if mod.get('depends_on'):
                dependent.append(mod)
            else:
                independent.append(mod)

        # Process modules concurrently
        await asyncio.gather(*[
            process_module(mod, output_data, config, args)
            for mod in independent
        ])

        # Process dependent modules sequentially
        for mod in dependent:
            await process_module(mod, output_data, config, args)

    # Generate final documentation
    builder = DocumentationBuilder("config.json")
    builder.merge_sections(
        debug_content=DEBUG_CONTENT if args.debug else None
    )

    if 'error' in output_data:
        logging.error("⛔ Some modules encountered errors. Check logs for details.")


if __name__ == "__main__":
    asyncio.run(main())
