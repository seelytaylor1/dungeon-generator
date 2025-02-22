# doc_writer.py
import os
import logging
import json
from datetime import datetime
from typing import Dict, Optional, LiteralString


def _load_config(config_path: str) -> Dict:
    """Load and return configuration"""
    try:
        with open(config_path) as f:
            config = json.load(f)
        logging.debug(f"Loaded config from {config_path}")
        return config
    except FileNotFoundError:
        logging.error(f"Config file not found: {config_path}")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"Config loading failed: {str(e)}")
        raise


class DocumentationBuilder:
    def __init__(self, config_path: str = "config.json"):
        self.config = _load_config(config_path)
        self._validate_config()
        self.output_dir = self.config['output'].get('directory', 'docs')

    def _validate_config(self):
        """Validate required configuration elements"""
        if 'output' not in self.config:
            raise ValueError("Missing 'output' section in config")

        if 'file' not in self.config['output']:
            raise ValueError("Missing required output field: 'file'")

        # Set default merge_order if missing
        if 'merge_order' not in self.config['output']:
            self.config['output']['merge_order'] = [
                mod['name'] for mod in self.config.get('modules', [])
            ]
            logging.warning("Using default merge order from module list")

    def ensure_output_dir(self):
        """Create output directory if needed"""
        os.makedirs(self.output_dir, exist_ok=True)

    def write_section(self, section_name: str, content: str) -> None:
        """
        Write section content using config-driven paths
        """
        self.ensure_output_dir()
        filename = os.path.join(self.output_dir, f"{section_name}.md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        logging.info(f"Wrote {section_name} content to {filename}")

    def merge_sections(self, debug_content: Optional[Dict] = None) -> LiteralString | str | bytes:
        """
        Merge sections according to config specifications
        Returns path to final document
        """
        self.ensure_output_dir()
        output_file = self.config['output']['file']
        merge_order = self.config['output']['merge_order']

        final_path = os.path.join(self.output_dir, output_file)

        with open(final_path, "w", encoding="utf-8") as fout:
            # Write document header
            fout.write(f"# {self.config.get('title', 'Dungeon')}\n\n")
            fout.write(f"*Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            # Process each section in configured order
            for section in merge_order:
                section_header = self._get_section_header(section)
                fout.write(f"## {section_header}\n\n")

                content = self._get_section_content(section, debug_content)
                fout.write(f"{content}\n\n")

        logging.info(f"Final documentation written to {final_path}")
        return final_path

    def _get_section_header(self, section_name: str) -> str:
        """Get formatted section header from config metadata"""
        for module in self.config['modules']:
            if module['name'] == section_name:
                return module.get('display_name', section_name.replace('_', ' ').title())
        return section_name.replace('_', ' ').title()

    def _get_section_content(self, section_name: str, debug_content: Optional[Dict]) -> str:
        """Retrieve content from appropriate source"""
        if debug_content and section_name in debug_content:
            return debug_content[section_name].get('content', '')

        section_file = os.path.join(self.output_dir, f"{section_name}.md")
        if os.path.exists(section_file):
            with open(section_file, "r", encoding="utf-8") as fin:
                return fin.read()

        logging.warning(f"Missing content for section: {section_name}")
        return "*Section content missing*"

# Example usage:
# builder = DocumentationBuilder()
# builder.merge_sections(debug_content=DEBUG_CONTENT)
