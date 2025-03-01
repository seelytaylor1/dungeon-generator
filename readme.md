# Dungeon Generator

![seal-small](https://github.com/user-attachments/assets/1603836e-e803-4e58-9989-57ae92ff1522)

## Overview

This project is a procedural dungeon generator designed for Shadowdark RPG. 

It leverages a combo of AI-driven prompts and random inputs to generate a dungeon.

![readme-screenshot](https://github.com/user-attachments/assets/f3bdf627-71aa-4c97-b0fc-48585680f3f3)

## Features
- AI-driven ancient history generation.
- AI-generated, history-specific factions.
- Procedurally created concept map of the dungeon.
- AI-driven room descriptions. 
- Flux.dev AI-powered image generation for dungeon rooms.

## Requirements
Ensure you have Python 3 installed along with the required dependencies.
```bash
pip install -r requirements.txt
```
In addition, you'll need [Ollama](https://ollama.com) and a local model installed. The script currently 
implements [openthinker:7b](https://ollama.com/library/openthinker), an uncensored distillation of deepseek-r1, as 
the primary model. 



## Usage
Run the generator with:
```bash
python main.py
```
Valid inputs are `yes`, `no`, and `debug`. You can also supply those at runtime with -y, -n, and -d flags.
Specify `no` if you have some ideas about the dungeon you want to generate.
Specify `debug` if you want to skip the first three steps of generation.

## Known Issues & Debugging
- Dungeon Content not being written to final doc.
- Final doc has formatting problems.
- Sometimes, the dungeon map adds nodes outside the view.
- Hardcoded models, temperature, and context window.
- Somewhat questionable room content outputs.
- Image generation requires significant GPU memory (at least 8GB VRAM).

## Future Enhancements
- Fix Known issues.
- Implement loops.
- Generate random encounter tables.
- Further refine AI prompts for better room outputs.

## Contributing
Pull requests are welcome! Not looking for bug reports; I got enough problems ;)

## License
All rights reserved for now.

