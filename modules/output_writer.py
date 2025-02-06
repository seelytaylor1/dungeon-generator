# output_writer.py
import re
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
import html

from modules.dungeon_map_generator import save_graph_image

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OutputSanitizer:
    @staticmethod
    def sanitize(text: str) -> str:
        """Sanitize content removing dangerous HTML and special markers."""
        cleaned = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)
        cleaned = html.escape(cleaned)  # Basic HTML sanitization
        return cleaned.strip()


class SectionHandler:
    def __init__(self):
        self.handlers = {}
        self.default_handler = self._default_handler

    def register(self, section: str, handler: callable):
        self.handlers[section.lower()] = handler

    def get_handler(self, section: str) -> callable:
        return self.handlers.get(section.lower(), self.default_handler)

    @staticmethod
    def _default_handler(data: Any, f) -> None:
        """Handle unknown section types safely."""
        if isinstance(data, dict):
            SectionHandler._handle_dict(data, f)
        elif isinstance(data, list):
            SectionHandler._handle_list(data, f)
        else:
            f.write(f"{str(data)}\n\n")

    @staticmethod
    def _handle_dict(data: Dict, f) -> None:
        if content := data.get('content'):
            f.write(f"{content}\n\n")
        if metadata := data.get('metadata'):
            f.write("### Key Aspects\n")
            for k, v in metadata.items():
                f.write(f"- **{k}**: {v}\n")
            f.write("\n")

    @staticmethod
    def _handle_list(data: List, f) -> None:
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    f.write(f"- **{key.title()}**: {value}\n")
            else:
                f.write(f"{item}\n")
        f.write("\n")


def _write_header(f) -> None:
    f.write("# Dungeon Documentation\n\n")
    f.write(f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")


class MarkdownWriter:
    def __init__(self, sanitize: bool = True):
        self.sanitize = sanitize
        self.handler = SectionHandler()
        self._register_default_handlers()

    def _register_default_handlers(self):
        # Register handlers using static methods on the class.
        self.handler.register("history", MarkdownWriter.history_handler)
        self.handler.register("faction", MarkdownWriter.factions_handler)
        self.handler.register("dungeon_map", MarkdownWriter.dungeon_map_handler)
        self.handler.register("exterior", MarkdownWriter.exterior_handler)

    @staticmethod
    def history_handler(data: Dict, f) -> None:
        if content := data.get('content'):
            f.write(f"{content}\n\n")
        if metadata := data.get('metadata'):
            f.write("### Historical Periods\n")
            for k, v in metadata.items():
                f.write(f"- **{k}**: {v}\n")
            f.write("\n")

    @staticmethod
    def factions_handler(data: Dict, f) -> None:
        try:
            factions = data.get('factions', [])
            f.write(f"**Total Factions**: {len(factions)}\n\n")
            for idx, faction in enumerate(factions, 1):
                f.write(f"#### Faction {idx}\n")
                f.write(f"- **Goal**: {faction.get('goal', 'Unknown')}\n")
                f.write(f"- **Obstacle**: {faction.get('obstacle', 'None')}\n")
                f.write(f"- **Members**: {faction.get('size', 'Some')} {faction.get('creature_type', 'creatures')}\n")
                f.write(f"\n{faction.get('content', '')}\n\n")
        except KeyError as e:
            logger.warning(f"Invalid faction structure: {str(e)}")

    @staticmethod
    def dungeon_map_handler(data: Dict, f) -> None:
        try:
            # If data is nested under "metadata", extract it.
            if "metadata" in data:
                data = data["metadata"]

            f.write(f"**Map Seed**: `{data.get('seed', 'N/A')}`\n\n")

            # Process nodes and build a mapping for room labels.
            nodes = data.get('nodes')
            id_to_key = {}
            if nodes:
                f.write("### Rooms\n")
                for node in nodes:
                    # Use the node's 'key' if available; otherwise, fall back to 'id'.
                    room_label = node.get('key') or node.get('id', 'Unknown')
                    id_to_key[node.get('id')] = room_label

                    room_type = node.get('room_type', 'Undefined')
                    f.write(f"- **{room_label}**: {room_type}\n")
                    features = node.get('features')
                    if features:
                        f.write(f"  - Features: {', '.join(features)}\n")
                f.write("\n")

            # Process edges using the lookup dictionary.
            edges = data.get('edges')
            if edges:
                f.write("### Connections\n")
                for edge in edges:
                    start_id = edge.get('start_id', 'Unknown')
                    end_id = edge.get('end_id', 'Unknown')
                    start_label = id_to_key.get(start_id, start_id)
                    end_label = id_to_key.get(end_id, end_id)
                    f.write(f"- {start_label} ↔ {end_label}\n")
                f.write("\n")

            # Generate the graph image using the helper function.
            from modules.dungeon_map_generator import save_graph_image
            save_graph_image(nodes, edges, image_filename="dungeon_graph.png")

            # Embed the image into the markdown file.
            f.write("### Dungeon Layout Graph\n")
            f.write("![Dungeon Graph](dungeon_graph.png)\n\n")

            # Process traversals if any.
            traversals = data.get('traversals')
            if traversals:
                f.write("### Critical Path\n")
                for traversal in traversals:
                    f.write(f"- {traversal.get('key', 'Unknown')}: {traversal.get('description', '')}\n")
        except KeyError as e:
            logger.warning(f"Missing map data key: {str(e)}")

    @staticmethod
    def exterior_handler(data: Dict, f) -> None:
        if content := data.get('content'):
            f.write(f"{content}\n\n")
        if features := data.get('features'):
            f.write("### Notable Exterior Features\n")
            for feature in features:
                f.write(f"- {feature}\n")
            f.write("\n")

    def write(self, filename: str, data: Dict[str, Any]) -> None:
        try:
            with open(filename, "w", encoding="utf-8") as f:
                _write_header(f)
                self._write_sections(f, data)
            logger.info(f"Successfully wrote output to {filename}")
        except Exception as e:
            logger.error(f"Failed to write output: {str(e)}")
            raise

    def _write_sections(self, f, data: Dict) -> None:
        for section, content in data.items():
            f.write(f"## {section.replace('_', ' ').title()}\n\n")
            handler = self.handler.get_handler(section)
            handler(self._process_content(content), f)

    def _process_content(self, content: Any) -> Any:
        if self.sanitize:
            return self._recursive_sanitize(content)
        return content

    def _recursive_sanitize(self, content: Any) -> Any:
        if isinstance(content, str):
            return OutputSanitizer.sanitize(content)
        if isinstance(content, list):
            return [self._recursive_sanitize(item) for item in content]
        if isinstance(content, dict):
            return {k: self._recursive_sanitize(v) for k, v in content.items()}
        return content



def write_markdown(filename: str, data: dict, sanitize: bool = True):
    """Modified to properly pass loop data"""
    # Add error check at start
    if 'error' in data:
        logging.error("Cannot generate output - errors present in data")
        return

    try:
        # Get loop data from metadata
        loops = data.get('metadata', {}).get('loops', [])

        # Pass all required parameters
        save_graph_image(
            nodes=data['metadata']['nodes'],
            edges=data['metadata']['edges'],
            loops=loops,  # This was missing
            image_filename="dungeon_graph.png"
        )

        # Rest of your markdown writing code...

    except KeyError as e:
        logging.error(f"Missing data for output generation: {str(e)}")
    except Exception as e:
        logging.error(f"Output generation failed: {str(e)}")


