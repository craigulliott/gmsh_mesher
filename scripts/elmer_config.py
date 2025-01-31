# elmer_config.py is a configuration file generator for Elmer
from jinja2 import Environment, FileSystemLoader
import os
import re

def name_to_material(name):
    cases = {
        r"^Shapes/air": 1,
        r"^Shapes/magnet_1_0_0": 2,
        r"^Shapes/magnet_-1_0_0": 3,
        r"^Shapes/magnet_0_1_0": 4,
        r"^Shapes/magnet_0_-1_0": 5,
        r"^Shapes/magnet_0_0_1": 6,
        r"^Shapes/magnet_0_0_-1": 7,
        r"^Shapes/iron": 8,
    }
    for pattern, material_id in cases.items():
        if re.match(pattern, name, re.IGNORECASE):  # Case insensitive match
            return material_id

    raise ValueError(f"No material found for: name '{name}'")

def generate(config_data):

    # Get the directory where the script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Load the template from the correct directory
    env = Environment(loader=FileSystemLoader(script_dir))
    template = env.get_template("elmer.template")

    # Render the template with data
    config_text = template.render(config_data)

    print("Generated elmer configuration file:")
    print(config_text)

    # Return the text
    return config_text
