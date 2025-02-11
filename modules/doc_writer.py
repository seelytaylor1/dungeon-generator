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
                   order: tuple = ("history", "faction", "exterior", "dungeon_map")) -> None:
    """
    Merge the markdown files from each section in the specified order
    into one final markdown document.
    """
    ensure_output_dir()
    with open(final_filename, "w", encoding="utf-8") as fout:
        # Write a global header.
        fout.write("# Dungeon Documentation\n\n")
        fout.write(f"*Generated on: {os.linesep}*\n\n")

        for section in order:
            section_file = os.path.join(OUTPUT_DIR, f"{section}.md")
            if os.path.exists(section_file):
                with open(section_file, "r", encoding="utf-8") as fin:
                    content = fin.read()
                    # Ensure each section has a header.
                    fout.write(f"## {section.replace('_', ' ').title()}\n\n")
                    fout.write(content)
                    fout.write("\n\n")
            else:
                logging.warning(f"Section file for '{section}' not found.")
    logging.info(f"Final documentation written to {final_filename}")
