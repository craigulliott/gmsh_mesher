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
python scripts/create_mesh.py
```

Run tests:

```bash
pytest tests/
```