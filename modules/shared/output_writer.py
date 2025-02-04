# output_writer.py

import re
from datetime import datetime
import logging

handlers = {}

def sanitize_output(text):
    return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

def register_handler(section, handler):
    handlers[section.lower()] = handler  # Use lower case for consistent matching

def write_section(section, data, f):
    if section.lower() in handlers:
        handlers[section.lower()](data, f)
    else:
        logging.warning(f"No handler registered for section: {section}")

def write_markdown(output_path, content_dict):
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# Dungeon Documentation\n\n")
            f.write(f"*Generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n\n")

            for section, data in content_dict.items():
                write_section(section, data, f)

        logging.info(f"Markdown file written: {output_path}")
    except Exception as e:
        logging.exception(f"Failed to write markdown file: {output_path}")

# Example default handler for plain text sections
def default_handler(data, f):
    if isinstance(data, dict):
        if data.get('content'):
            f.write(f"{data['content']}\n\n")
            if 'metadata' in data:
                f.write("### Key Aspects\n")
                for k, v in data['metadata'].items():
                    f.write(f"- **{k}**: {v}\n")
            f.write("\n")
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    f.write(f"- **{key.capitalize()}**: {value}\n")
                f.write("\n")
            else:
                f.write(f"{item}\n\n")

# Register the default handler
register_handler("default", default_handler)

# Register the handler for the Dungeon Map section
def dungeon_map_handler(data, f):
    f.write("## Dungeon Map\n\n")
    f.write("### Nodes (Rooms):\n\n")
    for node in data['dungeon_map']['nodes']:
        f.write(f"- **{node.get('key', node['id'])}**: {node['room_type']} at position {node['position']}\n")
        if node.get('is_entrance'):
            f.write("  - This is the entrance.\n")
    f.write("\n### Connections (Edges):\n\n")
    for edge in data['dungeon_map']['edges']:
        f.write(f"- {edge[0]} connected to {edge[1]}\n")
    if data['dungeon_map']['traversals']:
        f.write("\n### Traversals:\n\n")
        for traversal in data['dungeon_map']['traversals']:
            f.write(f"- **{traversal['key']}**: Node {traversal['node_id']} intersects edge {traversal['edge']}\n")
    if data['dungeon_map']['junctions']:
        f.write("\n### Junctions:\n\n")
        for junction in data['dungeon_map']['junctions']:
            f.write(f"- **{junction['key']}**: Edges {junction['edges'][0]} and {junction['edges'][1]} intersect\n")
    f.write("\n")

register_handler("dungeon_map", dungeon_map_handler)
