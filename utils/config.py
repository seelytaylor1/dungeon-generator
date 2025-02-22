# config.py
from schema import Schema, And, Or, Optional, SchemaError
import json
import logging


config_schema = Schema({
    'models': {
        'default': And(str, len),
        Optional('fallback'): Or(str, None)
    },
    'modules': [{
        'name': And(str, len),
        'function': And(str, len),
        'priority': And(int, lambda n: n >= 0),
        Optional('model'): Or(str, None),
        Optional('num_dice'): And(int, lambda n: n > 0),
        Optional('required_params'): [str],
        Optional('depends_on'): [str],
        Optional('retries'): And(int, lambda n: n >= 0),
        Optional('timeout'): And(int, lambda n: n > 0)
    }],
    'output': {
        'file': And(str, len),
        Optional('sanitize'): bool,
        Optional('merge_order'): [str],  # Made optional in latest version
        Optional('directory'): And(str, len)
    }
})


def build_config():
    """Load and validate configuration from config.json."""
    try:
        with open("config.json") as f:
            config = json.load(f)
        return config_schema.validate(config)
    except (FileNotFoundError, json.JSONDecodeError, SchemaError) as e:
        logging.error(f"❌ Config error: {str(e)}")
        return None
