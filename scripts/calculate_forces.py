import pyvista as pv
import numpy as np
import argparse

# Parse Arguments
parser = argparse.ArgumentParser(description="Calculate force on each body in a simulation result from its maxwell stress.")
parser.add_argument(
    "--input_file", type=str, default='results/case_t0001.vtu',
    help="Path to the elmer simulation results file. (default: results/case_t0001.vtu)."
)
args = parser.parse_args()

# Load data
filename = args.input_file
mesh = pv.read(filename)

# Step 1: Threshold
# -------------------------------------------------------------------
#
# ParaView filter: "Threshold"
# PyVista equivalent: mesh.threshold(...)
body_scalar_name = "GeometryIds"  # <--- Update if you have a different array name
lower_value = 1
upper_value = 1
thresholded = mesh.threshold([lower_value, upper_value], scalars=body_scalar_name)

# Step 2: Extract Surface
# -------------------------------------------------------------------
#
# ParaView filter: "Extract Surface"
# PyVista equivalent: thresholded.extract_surface()
#
# This converts volumetric cells (e.g., tetrahedra, hexahedra) into a surface mesh
# (triangles, polygons) that correspond to the outer surface of the thresholded body.
surface_mesh = thresholded.extract_surface()

# Step 3: Surface Normals
# -------------------------------------------------------------------
#
# ParaView filter: "Generate Surface Normals"
# PyVista method: .compute_normals()
#
# By default, compute_normals will generate point normals. If you want
# cell normals (similar to the "Surface" triangles in ParaView), specify:
#   cell_normals=True
# Here, we want cell normals because we eventually multiply by cell area.
surface_mesh = surface_mesh.compute_normals(cell_normals=True, point_normals=False)

# Step 4: Cell Size (Triangle Areas)
# -------------------------------------------------------------------
#
# ParaView filter: "Cell Size"
# PyVista function: .compute_cell_sizes(...) or .cell_sizes
#
# In ParaView, you add an "Area" array for each cell that indicates
# the area of that cell (triangle).
cell_sizes_mesh = surface_mesh.compute_cell_sizes(length=False, area=True, volume=False)
# Now, 'cell_sizes_mesh' is a new PyVista object that has the "Area" array for each cell.
cell_area = cell_sizes_mesh['Area']

# For convenience, we can just store this area array back into our surface_mesh cell_data:
surface_mesh.cell_data['Area'] = cell_area

# Step 5: "Calculator" to multiply area * Maxwell force * surface normal
# -------------------------------------------------------------------
# Extract the Maxwell force array from the cell_data
maxwell_force_x = surface_mesh.cell_data["maxwell stress e 1"]
maxwell_force_y = surface_mesh.cell_data["maxwell stress e 2"]
maxwell_force_z = surface_mesh.cell_data["maxwell stress e 3"]

# Extract cell normals from the cell_data (generated earlier)
normals = surface_mesh.cell_data['Normals']

# Extract the area we just computed
area = surface_mesh.cell_data['Area']

# Compute the force contribution in each direction:
#    F_dir = MaxwellForce_dir * Normal_dir * Area
force_x = maxwell_force_x * normals[:, 0] * area
force_y = maxwell_force_y * normals[:, 1] * area
force_z = maxwell_force_z * normals[:, 2] * area

# Optionally, store these partial results in the mesh
surface_mesh.cell_data["F_x"] = force_x
surface_mesh.cell_data["F_y"] = force_y
surface_mesh.cell_data["F_z"] = force_z

# Step 6: Sum all the force in each direction
# -------------------------------------------------------------------
total_force_x = np.sum(force_x)
total_force_y = np.sum(force_y)
total_force_z = np.sum(force_z)

# Print the results
print("Total force in X direction:", total_force_x)
print("Total force in Y direction:", total_force_y)
print("Total force in Z direction:", total_force_z)
