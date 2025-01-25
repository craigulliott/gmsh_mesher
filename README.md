# Gmsh Simulation Project

This project uses the Gmsh Python API to prepare a mesh for magnetic simulations in Elmer. It supports loading IGES files, creating surrounding air volumes, and refining meshes.

## Requirements

- Python 3.9+
- Gmsh SDK

## Setup

Setup Instructions
Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

Install dependencies:

```bash
pip install -r requirements.txt

# for apple silicon:
pip install -i https://gmsh.info/python-packages-dev --force-reinstall --no-cache-dir gmsh
```

Run the script:

```bash
python scripts/create_mesh.py ~/Downloads/many_magnets.iges --output_file ~/Downloads/many_magnets.msh
```

If you need to save a big file to a network drive, then it's much faster to move the file after it has been generated
```bash
python scripts/create_mesh.py ~/Downloads/many_magnets.iges --output_file /tmp/many_magnets.msh --refinement_factor 0.05 && mv /tmp/many_magnets.msh /Volumes/Users/Craig/Elmer/Projects/many_magnets/mesh.msh
```

```bash
# see options with
python scripts/create_mesh.py --help
```

Run tests:

```bash
pytest tests/
```

## Elmer

The resulting mesh from this software can be used to run a simulation in Elmer, here is a great video showing how to set that up

https://www.youtube.com/watch?v=_b0NPP12OCQ