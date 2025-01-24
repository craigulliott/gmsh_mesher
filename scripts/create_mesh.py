import gmsh
import os
import shutil

# Input IGES file path
INPUT_IGES_FILE = "data/two_magnets.iges"

# Output mesh file path
OUTPUT_MESH_FILE = "data/output.msh"
# Final file is copied to the output directory (faster to copy the final file if the target is a network drive)
TARGET_MESH_FILE = "/Volumes/Users/Craig/Elmer/Meshes/two_magnets.msh"

# Mesh parameters
AIR_BOX_PADDING = 50.0  # Padding around the geometry
TARGET_MESH_SIZE = 4.0  # Default element size
REFINEMENT_FACTOR = 0.1  # Refinement near bodies
REFINE_DIST_MIN = 2.0  # Minimum distance for refinement
REFINE_DIST_MAX = 10.0  # Minimum distance for refinement

def main():
    # Initialize Gmsh
    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)

    try:
        if not os.path.exists(INPUT_IGES_FILE):
            raise FileNotFoundError(f"Input IGES file not found: {INPUT_IGES_FILE}")

        # Load the IGES file
        gmsh.model.occ.importShapes(INPUT_IGES_FILE)
        gmsh.model.occ.synchronize()

        # Check the imported volumes
        object_volumes = gmsh.model.getEntities(dim=3)
        if not object_volumes:
            raise ValueError("No volumes found in the IGES file.")
        print("Imported volumes:", object_volumes)

        # Fetch surface tags of the imported geometry (before adding the air volume)
        object_surfaces = gmsh.model.getEntities(dim=2)
        surface_tags = [s[1] for s in object_surfaces]
        print("Object surface tags:", surface_tags)

        # Get the bounding box of the geometry
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)
        print("Bounding box dimensions:", xmin, xmax, ymin, ymax, zmin, zmax)

        # Create air volume
        xmin -= AIR_BOX_PADDING
        ymin -= AIR_BOX_PADDING
        zmin -= AIR_BOX_PADDING
        xmax += AIR_BOX_PADDING
        ymax += AIR_BOX_PADDING
        zmax += AIR_BOX_PADDING

        # Define the air volume as a box
        air_volume = gmsh.model.occ.addBox(xmin, ymin, zmin, xmax - xmin, ymax - ymin, zmax - zmin)
        gmsh.model.occ.synchronize()
        print("Air volume tag:", air_volume)

        # Cut the geometry from the air volume
        print("Object volume tags:", object_volumes)
        air_volume_cut = gmsh.model.occ.cut(
            [(3, air_volume)],
            [(3, tag) for tag in [v[1] for v in object_volumes]],
            removeObject=True,
            removeTool=False
        )
        gmsh.model.occ.synchronize()
        print("Air volume cut result:", air_volume_cut)

        remaining_volumes = gmsh.model.getEntities(dim=3)
        print("Remaining volumes after cut:", remaining_volumes)

        # Add physical groups for volumes
        for volume in remaining_volumes:
            gmsh.model.addPhysicalGroup(3, [volume[1]])

        # Add physical groups for all surfaces
        surfaces = gmsh.model.getEntities(dim=2)
        print("Surfaces in the model:", surfaces)
        for surface in surfaces:
            gmsh.model.addPhysicalGroup(2, [surface[1]])

        # Create a mesh size field for refinement near the bodies
        distance_field_tag = gmsh.model.mesh.field.add("Distance")
        gmsh.model.mesh.field.setNumbers(distance_field_tag, "SurfacesList", surface_tags)

        for volume in remaining_volumes:
            gmsh.model.addPhysicalGroup(3, [volume[1]])

        # Define a threshold field
        threshold_field_tag = gmsh.model.mesh.field.add("Threshold")
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "InField", distance_field_tag)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "SizeMin", TARGET_MESH_SIZE * REFINEMENT_FACTOR)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "SizeMax", TARGET_MESH_SIZE)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "DistMin", REFINE_DIST_MIN)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "DistMax", REFINE_DIST_MAX)

        # Apply the field as the background mesh field
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold_field_tag)

        # Generate mesh
        gmsh.model.mesh.generate(3)

        # Save the mesh
        gmsh.write(OUTPUT_MESH_FILE)
        print(f"Mesh saved to {OUTPUT_MESH_FILE}")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        gmsh.finalize()

        # Copy the file
        try:
            print(f"Copying file to {TARGET_MESH_FILE}")
            shutil.copy(OUTPUT_MESH_FILE, TARGET_MESH_FILE)
            print(f"File copied from {OUTPUT_MESH_FILE} to {TARGET_MESH_FILE}")
        except FileNotFoundError:
            print(f"The file {OUTPUT_MESH_FILE} does not exist.")
        except PermissionError:
            print("Permission denied. Unable to copy the file.")
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
