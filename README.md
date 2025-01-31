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

## Full simulation workflow

For this workflow to function correctly, each body must be assigned a name corresponding to its material. The materials should be defined in scripts/elmer.template, and a mapping should be created in scripts/elmer_config.py. This setup currently works for me in Fusion 360, but if you’re using a different CAD software, you may need to adjust the regular expressions or modify the script to match your software’s output.

For example, my bodies in fusion 360 might be called "iron (1)", "iron (2)" and two magnets with opposing fields on the Y axis might be called "magnet_0_1_0 (1)" and "magnet_0_-1_0 (1)".

```bash
# Generate mesh.msh from model.iges, and generate elmer scripts
python ../scripts/create_mesh.py --generate_elmer_files

# Convert mesh.msh into elmer mesh format and place files in ./mesh
ElmerGrid 14 2 mesh.msh -autoclean

# Run the elmer solver and place the result in ./results
ElmerSolver
```

## Elmer

The resulting mesh from this software can be used to run a simulation in Elmer, here is a great video showing how to set that up

https://www.youtube.com/watch?v=_b0NPP12OCQ

### Notes for Running Magneto-Dynamic (MgDyn) Simulations with Elmer

These insights are the result of extensive trial and error over several days and are specifically geared toward using Gmsh to generate meshes for running Magneto-Dynamic (MgDyn) simulations in Elmer.

#### Key Learnings

1. **Mesh Quality is Critical**

   - Elmer is highly sensitive to the quality of the mesh. If your convergence history chart does not quickly trend downward (a red line starting at 1 and dropping to 1e-07 or lower within a few iterations), the mesh is likely the issue.

2. **Mesh Refinement**

   - The mesh should be most refined near your geometry and can become coarser toward the edges of the air volume. While it's common to refine only near features (e.g., vertices), I found that making the mesh uniform across the faces of objects yielded results that were easier to interpret.

3. **Air Volume Considerations**

   - **Size**: Ensure the air volume surrounding your geometry is very large. A large air volume reduces solver errors and provides better visualization capabilities with GUI tools.
   - **Overlap**: The air volume must **not** overlap with your bodies. Overlapping geometries caused significant issues in my workflow. The most effective approach to avoid this was to generate the air volume and subtract the bodies from it within my Python scripts.

4. **Mesh Optimization**

   - Utilizing the `Optimize` and `OptimizeNetgen` steps in Gmsh was crucial. Skipping these steps often led to mesh errors and poor simulation results.

5. **Platform Compatibility**

   - Running these simulations on a silicon-based Mac proved to be a significant challenge. After numerous unsuccessful attempts, I found that switching to a PC was the most practical solution.

#### Additional Tips
- Expect to iterate on your mesh design and simulation setup multiple times before achieving optimal results.
- Keep an eye on the solver logs and convergence charts for signs of issues early in the simulation process.
- Familiarize yourself with Python scripting in Gmsh to streamline and automate repetitive tasks, such as air volume creation and mesh refinement.
- Running Elmer with multiple threads is straightforward and significantly reduces simulation time. However, it introduced artifacts at the mesh partition boundaries, making the results more difficult to work with. Once the convergence history chart indicated that the results were reliable, I preferred to rerun the simulation (sometimes overnight) to produce a clean, unified result set.
- Start with small and simple meshes. Early in my process, I encountered many frustrating issues due to the size and complexity of my meshes, as well as the extended time required for processing. By starting with smaller, simpler meshes, I was able to better understand and fine-tune the parameters. Once I had a solid grasp of the workflow, both Gmsh and Elmer handled larger, more complex models efficiently and effectively.
- I ran into some issues with STEP files (meshing was failing). Exporting the same model from fusion 360 as an IGES fixed it, so I'm just using IGES files.

These notes are intended to help others avoid the same pitfalls and save valuable time when running MgDyn simulations with Elmer. If you encounter similar challenges or have additional insights, contributions are welcome!
