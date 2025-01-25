import os
import argparse
import gmsh

def main():
    try:
        # Initialize Gmsh
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)

        # ---------------- Parse Arguments ----------------
        parser = argparse.ArgumentParser(description="Generate a mesh from an input STEP/IGES file.")
        parser.add_argument("input_file", type=str, help="Path to the input STEP/IGES file.")
        parser.add_argument(
            "--air_mesh_size", type=float, default=0,
            help="Default element size for the air volume where it is not near bodies (default: calculated automatically based on the total air volume)."
        )
        parser.add_argument(
            "--refinement_factor", type=float, default=0.01,
            help="Refinement factor for the mesh near bodies, if your model is in MM and target mesh size is 4mm, a value of 0.1 will result in a mesh of 0.4mm (default: 0.01)."
        )
        parser.add_argument(
            "--air_box_padding", type=float, default=400.0,
            help="Padding around the geometry for the air volume (default: 400.0)."
        )
        parser.add_argument(
            "--refine_dist_min", type=float, default=4.0,
            help="The distance from body surfaces where the mesh starts to become less refined (default: 2.0)."
        )
        parser.add_argument(
            "--refine_dist_max", type=float, default=40.0,
            help="The distance from body surfaces where the mesh fidelity will be back at the air_mesh_size value (default: 10.0)."
        )
        parser.add_argument(
            "--output_file", type=str, default="final_mesh.msh",
            help="Path to the output mesh file (default: final_mesh.msh)."
        )
        args = parser.parse_args()

        air_box_padding = args.air_box_padding
        input_file = args.input_file
        output_file = args.output_file
        air_mesh_size = args.air_mesh_size
        refinement_factor = args.refinement_factor
        refine_dist_min = args.refine_dist_min
        refine_dist_max = args.refine_dist_max
        # --------------------------------------------------


        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input STEP/IGES file not found: {input_file}")

        print("Default number of threads used:", gmsh.option.getNumber("General.NumThreads"))
        cores = os.cpu_count()
        print(f"Number of logical processors (cores) on this machine: {cores}")
        if cores > 2:
            gmsh.option.setNumber("General.NumThreads", cores - 1)
            print(f"Number of threads set to {cores - 1}")

        # Load the STEP/IGES file
        gmsh.model.occ.importShapes(input_file)
        gmsh.model.occ.synchronize()

        # Remove duplicate entities
        duplicates = gmsh.model.occ.removeAllDuplicates()
        print("Duplicates:", duplicates)
        if duplicates:
            raise ValueError("Duplicates found in the STEP/IGES file.")
        gmsh.model.occ.synchronize()

        # Check the imported volumes
        object_volumes = gmsh.model.getEntities(dim=3)
        if not object_volumes:
            raise ValueError("No volumes found in the STEP/IGES file.")
        print("Imported volumes:", object_volumes)

        # Set tolerances to avoid self-intersections
        gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-6)

        # Use 2nd-order elements to capture field gradients more accurately.
        # Disabled until we figure out how to configure elmer to handle them
        # gmsh.option.setNumber("Mesh.ElementOrder", 2)

        # Enable mesh optimization to reduce skewness and improve element shapes
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)  # Advanced Netgen optimization

        # Set the default meshing algorithm and element order
        # 7 = Frontal-Delaunay (3D)
        # 9 = HXT (highly optimized for multithreading)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)

        # Fetch surface tags of the imported geometry (before adding the air volume)
        object_surfaces = gmsh.model.getEntities(dim=2)
        surface_tags = [s[1] for s in object_surfaces]
        print("Object surface tags:", surface_tags)

        # Get the bounding box of the geometry
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)
        print("Bounding box dimensions:", xmin, xmax, ymin, ymax, zmin, zmax)

        # Create air volume
        xmin -= air_box_padding
        ymin -= air_box_padding
        zmin -= air_box_padding
        xmax += air_box_padding
        ymax += air_box_padding
        zmax += air_box_padding

        if air_mesh_size == 0:
            air_mesh_size = round(((xmax - xmin) + (ymax - ymin) + (zmax - zmin)) / 40)
            print("Air mesh size automatically set to:", air_mesh_size)

        size_min = air_mesh_size * refinement_factor
        print("Most detailed mesh size automatically set to:", size_min)


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
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "SizeMin", size_min)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "SizeMax", air_mesh_size)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "DistMin", refine_dist_min)
        gmsh.model.mesh.field.setNumber(threshold_field_tag, "DistMax", refine_dist_max)

        # Apply the field as the background mesh field
        gmsh.model.mesh.field.setAsBackgroundMesh(threshold_field_tag)

        # Generate mesh
        gmsh.model.mesh.generate(3)

        # Save the mesh
        print(f"Saving to {output_file}")
        gmsh.write(output_file)
        print(f"Mesh saved")

    except Exception as e:
        print(f"Error: {e}")

    finally:
        gmsh.finalize()

if __name__ == "__main__":
    main()
