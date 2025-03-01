"""
Dungeon Image Generator Module

This module generates images for dungeon sections using WebForgeUI
and integrates them into the dungeon.md file.
"""

import os
import re
import time
import json
import requests
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from PIL import Image
from io import BytesIO

# Check if required packages are available
try:
    import requests
    from PIL import Image
    REQUIREMENTS_MET = True
except ImportError:
    REQUIREMENTS_MET = False

class DungeonImageGenerator:
    """
    A class to generate images for a dungeon and update the markdown file.
    """
    
    def __init__(self, project_root: str = None, webforgeui_url: str = "http://127.0.0.1:7860"):
        """
        Initialize the DungeonImageGenerator.
        
        Args:
            project_root: Root directory of the project. If None, uses current directory.
            webforgeui_url: URL of the WebForgeUI server. Default is localhost:7860.
        """
        self.project_root = Path(project_root or os.getcwd())
        self.webforgeui_url = webforgeui_url
        
    def ask_for_image_generation(self) -> bool:
        """Ask the user if they want to generate images."""
        while True:
            response = input("Do you want to generate images for your dungeon? (yes/no): ").lower().strip()
            if response in ["yes", "y"]:
                if not REQUIREMENTS_MET:
                    print("Required libraries are not installed for image generation.")
                    print("Please install them with: pip install requests pillow")
                    return False
                
                # Ask for WebForgeUI URL if different from default
                custom_url = input(f"Enter WebForgeUI URL (default: {self.webforgeui_url}): ").strip()
                if custom_url:
                    self.webforgeui_url = custom_url
                    
                return True
            elif response in ["no", "n"]:
                return False
            else:
                print("Please answer 'yes' or 'no'.")
    
    def parse_dungeon_md(self, file_path: Path) -> Dict[str, str]:
        """
        Parse the dungeon.md file and extract text between headings.
        
        Returns a dictionary with heading as key and content as value.
        """
        if not file_path.exists():
            print(f"File {file_path} does not exist.")
            return {}
        
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Split by headings (## heading)
        sections = re.split(r'(^##\s+.*$)', content, flags=re.MULTILINE)
        
        # Group headings with their content
        result = {}
        current_heading = "Introduction"  # Default for content before first heading
        
        for section in sections:
            if section.strip():
                if section.startswith("##"):
                    current_heading = section.strip("# \n")
                    result[current_heading] = ""
                else:
                    if current_heading in result:
                        result[current_heading] += section
                    else:
                        result[current_heading] = section
        
        return result
    
    def setup_model(self) -> bool:
        """
        Verify connection to WebForgeUI.
        """
        try:
            print(f"Testing connection to WebForgeUI at {self.webforgeui_url}...")
            
            # Make a simple request to check if the server is available
            response = requests.get(f"{self.webforgeui_url}/ping", timeout=5)
            
            if response.status_code == 200:
                print("Successfully connected to WebForgeUI.")
                return True
            else:
                print(f"WebForgeUI server returned status code {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to WebForgeUI: {e}")
            print("Make sure WebForgeUI is running and accessible at the specified URL.")
            
            # Ask if the user wants to provide a different URL
            retry = input("Would you like to try a different WebForgeUI URL? (yes/no): ").lower().strip()
            if retry in ["yes", "y"]:
                new_url = input("Enter WebForgeUI URL: ").strip()
                if new_url:
                    self.webforgeui_url = new_url
                    return self.setup_model()
            
            return False
    
    def generate_image(
        self,
        prompt: str,
        output_path: Path,
        image_name: str,
        negative_prompt: str = "blurry, low quality, weird artifacts, distorted, text, watermark",
        width: int = 1024,
        height: int = 1024,
        num_inference_steps: int = 30,
        guidance_scale: float = 7.0,
        seed: int = None
    ) -> Optional[Path]:
        """
        Generate an image using WebForgeUI.
        """
        try:
            # Create output directory if it doesn't exist
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Prepare the prompt for a fantasy dungeon scene
            enhanced_prompt = f"fantasy dungeon scene, detailed, atmospheric, {prompt}"
            
            # Prepare payload for WebForgeUI
            payload = {
                "prompt": enhanced_prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "steps": num_inference_steps,
                "cfg_scale": guidance_scale,
                "sampler_name": "DPM++ 2M Karras",  # Common sampler
            }
            
            # Set seed if provided
            if seed is not None:
                payload["seed"] = seed
            else:
                # Use random seed if not provided
                payload["seed"] = -1
            
            print(f"Generating image for '{image_name}'...")
            
            # Call WebForgeUI API to generate the image
            response = requests.post(
                f"{self.webforgeui_url}/sdapi/v1/txt2img",
                json=payload,
                timeout=300  # Extended timeout for image generation
            )
            
            if response.status_code != 200:
                print(f"Error: WebForgeUI returned status code {response.status_code}")
                print(response.text)
                return None
                
            # Parse the response
            result = response.json()
            
            # The API returns images as base64-encoded strings
            if "images" in result and len(result["images"]) > 0:
                # Decode the image from base64
                import base64
                image_data = base64.b64decode(result["images"][0])
                
                # Create an image from the binary data
                image = Image.open(BytesIO(image_data))
                
                # Save the image
                image_path = output_path / f"{image_name}.png"
                image.save(image_path)
                
                print(f"Image saved to {image_path}")
                return image_path
            else:
                print("No images returned from WebForgeUI")
                return None
                
        except Exception as e:
            print(f"Error generating image: {e}")
            return None
    
    def update_dungeon_md(self, file_path: Path, image_map: Dict[str, Path]) -> bool:
        """
        Update the dungeon.md file with links to generated images.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # Split by headings (## heading)
            sections = re.split(r'(^##\s+.*$)', content, flags=re.MULTILINE)
            
            updated_content = []
            current_heading = None
            
            for section in sections:
                updated_content.append(section)
                
                if section.startswith("##"):
                    current_heading = section.strip("# \n")
                    if current_heading in image_map:
                        # Add image link after the heading
                        relative_path = os.path.relpath(image_map[current_heading], file_path.parent)
                        image_link = f"\n\n![{current_heading}]({relative_path})\n"
                        updated_content.append(image_link)
            
            # Write the updated content back to the file
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("".join(updated_content))
            
            return True
        except Exception as e:
            print(f"Error updating dungeon.md: {e}")
            return False
    
    def clean_section_for_prompt(self, text: str, max_length: int = 500) -> str:
        """
        Clean and prepare a section text to be used as a prompt for image generation.
        """
        # Remove any markdown formatting
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)  # Remove links
        text = re.sub(r'[*_~`#]', '', text)         # Remove formatting characters
        text = re.sub(r'\n+', ' ', text)            # Replace newlines with spaces
        
        # Truncate to max length
        if len(text) > max_length:
            text = text[:max_length-3] + "..."
        
        return text.strip()
    
    def generate_images(self, dungeon_md_path: str = "docs/dungeon.md") -> bool:
        """
        Main function to orchestrate the image generation process.
        """
        # Convert to Path object
        md_path = self.project_root / Path(dungeon_md_path)
        
        # Ask user if they want images
        if not self.ask_for_image_generation():
            print("Skipping image generation.")
            return False
        
        # Setup the connection to WebForgeUI
        if not self.setup_model():
            print("Failed to connect to WebForgeUI.")
            return False
        
        # Parse dungeon.md
        print("Parsing dungeon content...")
        sections = self.parse_dungeon_md(md_path)
        if not sections:
            print("Failed to parse dungeon content or file is empty.")
            return False
        
        # Create img directory
        img_dir = md_path.parent / "img"
        img_dir.mkdir(exist_ok=True)
        
        # Generate images for each section
        print("Generating images...")
        image_map = {}
        for heading, content in sections.items():
            # Skip very short sections or introduction
            if len(content.strip()) < 50 or heading.lower() == "introduction":
                continue
            
            print(f"Generating image for section: {heading}")
            prompt = self.clean_section_for_prompt(content)
            
            # Create a filename-safe version of the heading
            safe_heading = re.sub(r'[^\w\-_]', '_', heading)
            
            image_path = self.generate_image(
                prompt=prompt,
                output_path=img_dir,
                image_name=safe_heading
            )
            
            if image_path:
                image_map[heading] = image_path
                print(f"Generated image for {heading}: {image_path}")
            else:
                print(f"Failed to generate image for {heading}")
        
        # Update dungeon.md with image links
        if image_map:
            print("Updating dungeon.md with image links...")
            if self.update_dungeon_md(md_path, image_map):
                print(f"Successfully updated {md_path} with {len(image_map)} images.")
                return True
            else:
                print(f"Failed to update {md_path}.")
                return False
        else:
            print("No images were generated.")
            return False


def generate_dungeon_images(dungeon_md_path: str = "docs/dungeon.md", project_root: str = None, webforgeui_url: str = "http://127.0.0.1:7860") -> bool:
    """
    Generate images for the dungeon and update the markdown file.
    
    Args:
        dungeon_md_path: Path to the dungeon.md file
        project_root: Root directory of the project. If None, uses current directory.
        webforgeui_url: URL of the WebForgeUI server. Default is localhost:7860.
        
    Returns:
        True if successful, False otherwise
    """
    generator = DungeonImageGenerator(project_root, webforgeui_url)
    return generator.generate_images(dungeon_md_path)


if __name__ == "__main__":
    # When run as a script, generate images for the default dungeon.md file
    generate_dungeon_images()
