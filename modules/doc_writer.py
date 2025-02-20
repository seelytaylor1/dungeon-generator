# doc_writer.py
import os
import logging

OUTPUT_DIR = "docs"


def ensure_output_dir():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)


def write_section(section_name: str, content: str) -> None:
    """
    Write (or overwrite) the markdown content for a given section.
    """
    ensure_output_dir()
    filename = os.path.join(OUTPUT_DIR, f"{section_name}.md")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    logging.info(f"Wrote {section_name} content to {filename}")


def merge_sections(final_filename: str = "dungeon.md",
                   order: tuple = ("history", "faction", "exterior", "dungeon_map", "dungeon_content"),
                   debug_content: dict = None) -> None:
    """
    Merge markdown files or debug content into final documentation.
    """
    ensure_output_dir()
    with open(final_filename, "w", encoding="utf-8") as fout:
        fout.write("# Dungeon Documentation\n\n")
        fout.write(f"*Generated on: {os.linesep}*\n\n")

        for section in order:
            # Write section header
            fout.write(f"## {section.replace('_', ' ').title()}\n\n")

            if debug_content and section in debug_content:
                # Handle debug content
                content = debug_content[section].get('content', '')
                fout.write(f"{content}\n\n")
                continue

            # Original file-based handling
            section_file = os.path.join(OUTPUT_DIR, f"{section}.md")
            if os.path.exists(section_file):
                with open(section_file, "r", encoding="utf-8") as fin:
                    fout.write(fin.read())
                    fout.write("\n\n")
            else:
                logging.warning(f"Section file for '{section}' not found.")

    logging.info(f"Final documentation written to {final_filename}")
