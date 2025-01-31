import os
import argparse
import gmsh
import elmer_config
import iges
from types import SimpleNamespace

def main():
    try:
        # Initialize Gmsh
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)

        # ---------------- Parse Arguments ----------------
        parser = argparse.ArgumentParser(description="Generate a mesh from an input IGES file.")
        parser.add_argument(
            "--input_file", type=str, default='model.iges',
            help="Path to the input IGES file. (default: model.iges)."
        )
        parser.add_argument(
            "--air_mesh_size", type=float, default=0,
            help="Default element size in MM for the air volume where it is not near bodies (default: calculated automatically based on the total air volume)."
        )
        parser.add_argument(
            "--refinement_factor", type=float, default=0.02,
            help="Refinement factor for the mesh near bodies, if your model is in MM and target mesh size is 4mm, a value of 0.1 will result in a mesh of 0.4mm (default: 0.02)."
        )
        parser.add_argument(
            "--air_box_padding", type=float, default=400.0,
            help="Padding around the geometry in MM for the air volume (default: 400.0)."
        )
        parser.add_argument(
            "--refine_dist_min", type=float, default=4.0,
            help="The distance from body surfaces in MM where the mesh starts to become less refined (default: 4.0)."
        )
        parser.add_argument(
            "--refine_dist_max", type=float, default=40.0,
            help="The distance from body surfaces in MM where the mesh fidelity will be back at the air_mesh_size value (default: 40.0)."
        )
        parser.add_argument(
            "--draft", action='store_true',
            help="If true, default values will be chosen that result in a less fine mesh (default: false)."
        )
        parser.add_argument(
            "--fine", action='store_true',
            help="If true, default values will be chosen that result in a very fine mesh (default: false)."
        )
        parser.add_argument(
            "--multi_thread", action='store_true',
            help="If true, mesh will be created with multiple threads. This algorithm will result in slightly a slightly different mesh each time."
        )
        parser.add_argument(
            "--output_file", type=str, default="mesh.msh",
            help="Path to the output mesh file (default: mesh.msh)."
        )
        parser.add_argument(
            "--elmer_config_file", type=str, default="case.sif",
            help="Path to the output elmer script file (default: case.sif)."
        )
        parser.add_argument(
            "--elmer_result_file", type=str, default="case.vtu",
            help="Path to the elmer simulation result (default: case.vtu)."
        )
        parser.add_argument(
            "--generate_elmer_files", action='store_true',
            help="If true, will generate elmer script and ELMERSOLVER_STARTINFO file."
        )
        args = parser.parse_args()

        input_file = args.input_file
        output_file = args.output_file
        elmer_config_file = args.elmer_config_file
        elmer_result_file = args.elmer_result_file
        air_box_padding = args.air_box_padding
        air_mesh_size = args.air_mesh_size
        refinement_factor = args.refinement_factor
        refine_dist_min = args.refine_dist_min
        refine_dist_max = args.refine_dist_max

        if args.draft:
            # a less fine mesh is desired
            print("Draft mode enabled")
            auto_air_mesh_factor = 20

        elif args.fine:
            # a very fine mesh is desired
            print("Fine mode enabled")
            auto_air_mesh_factor = 40
            # override refinement_factor (unless its been set manually)
            if args.refinement_factor == 0.02:
                refinement_factor = 0.015
            # override refine_dist_max (unless its been set manually)
            if args.refine_dist_max == 40.0:
                refinement_factor = 60.0

        else:
            auto_air_mesh_factor = 30

        # --------------------------------------------------

        if args.multi_thread:
            print("Default number of threads used:", gmsh.option.getNumber("General.NumThreads"))
            cores = os.cpu_count()
            print(f"Number of logical processors (cores) on this machine: {cores}")
            if cores > 2:
                gmsh.option.setNumber("General.NumThreads", cores - 1)
                print(f"Number of threads set to {cores - 1}")

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input IGES file not found: {input_file}")

        if not iges.is_iges_file(input_file):
            raise FileNotFoundError(f"Input file did not appear to be a IGES file")

        unit_name = iges.get_iges_units(input_file)

        print(f"IGES File Units Name: {unit_name}")
        if unit_name == "MM":
            scale_factor = 0.001
        elif unit_name == "CM":
            scale_factor = 0.01
        elif unit_name == "M":
            scale_factor = 1
        else:
            raise FileNotFoundError(f"Expected units to be MM, but IGES file is using unexpected units: {unit_name}")

        # Load the IGES file
        gmsh.option.setNumber("Geometry.OCCImportLabels", 1)
        gmsh.model.occ.importShapes(input_file)
        gmsh.model.occ.synchronize()

        # Get the initial bounding box of the geometry
        initial_xmin, initial_ymin, initial_zmin, initial_xmax, initial_ymax, initial_zmax = gmsh.model.getBoundingBox(-1, -1)
        print(f"Initial bounding box dimensions (in {unit_name}): x {initial_xmin:.2f}, {initial_xmax:.2f}, y {initial_ymin:.2f}, {initial_ymax:.2f}, z {initial_zmin:.2f}, {initial_zmax:.2f}")

        if scale_factor != 1:
            air_box_padding = air_box_padding * scale_factor
            air_mesh_size = air_mesh_size * scale_factor
            refine_dist_min = refine_dist_min * scale_factor
            refine_dist_max = refine_dist_max * scale_factor

            print(f"Scaling model (converting {unit_name} to M)")
            # Get all entities in the model to apply scaling
            entities = gmsh.model.occ.getEntities()

            print(f"Applying scale factor of {scale_factor}")
            # Apply scaling to convert from mm to m (scale factor 0.001)
            gmsh.model.occ.dilate(entities, 0, 0, 0, scale_factor, scale_factor, scale_factor)

            print("Scaling complete (model is now in meters)")

            # Synchronize the model to apply transformations
            gmsh.model.occ.synchronize()

            # Print the new bounding box of the geometry
            scaled_xmin, scaled_ymin, scaled_zmin, scaled_xmax, scaled_ymax, scaled_zmax = gmsh.model.getBoundingBox(-1, -1)
            print(f"New bounding box dimensions (meters): x {scaled_xmin:.4f}, {scaled_xmax:.4f}, y {scaled_ymin:.4f}, {scaled_ymax:.4f}, z {scaled_zmin:.4f}, {scaled_zmax:.4f}")

        # Synchronize the model to apply transformations
        gmsh.model.occ.synchronize()

        # Remove duplicate entities
        duplicates = gmsh.model.occ.removeAllDuplicates()
        print("Duplicates:", duplicates)
        if duplicates:
            raise ValueError("Duplicates found in the IGES file.")
        gmsh.model.occ.synchronize()

        # Check the imported volumes
        object_volumes = gmsh.model.getEntities(dim=3)
        if not object_volumes:
            raise ValueError("No volumes found in the IGES file.")
        print("Imported volumes:", object_volumes)

        # Set tolerances to avoid self-intersections
        gmsh.option.setNumber("Geometry.ToleranceBoolean", 1e-6)

        # Use 2nd-order elements to capture field gradients more accurately.
        # gmsh.option.setNumber("Mesh.ElementOrder", 2)

        # Enable mesh optimization to reduce skewness and improve element shapes
        gmsh.option.setNumber("Mesh.Optimize", 3) # 3 passes
        gmsh.option.setNumber("Mesh.OptimizeNetgen", 1)  # Advanced Netgen optimization

        # Set the default meshing algorithm and element order
        # 7 = Frontal-Delaunay (3D)
        # 9 = HXT (highly optimized for multithreading)
        gmsh.option.setNumber("Mesh.Algorithm3D", 1)

        # Get the bounding box of the geometry
        xmin, ymin, zmin, xmax, ymax, zmax = gmsh.model.getBoundingBox(-1, -1)

        print(f"Moving geometry so that none of the study will fall in a negative quadrant")
        air_vol_xmin = xmin - air_box_padding
        air_vol_ymin = ymin - air_box_padding
        air_vol_zmin = zmin - air_box_padding
        x_offset = -air_vol_xmin if air_vol_xmin < 0 else 0
        y_offset = -air_vol_ymin if air_vol_ymin < 0 else 0
        z_offset = -air_vol_zmin if air_vol_zmin < 0 else 0

        gmsh.model.occ.translate([(3, tag) for tag in [v[1] for v in object_volumes]], x_offset, y_offset, z_offset)
        gmsh.model.occ.synchronize()

        # Fetch surface tags of the imported geometry (before adding the air volume)
        object_surfaces = gmsh.model.getEntities(dim=2)
        surface_tags = [s[1] for s in object_surfaces]
        print("Object surface tags:", surface_tags)

        # Create air volume
        xmin = 0
        ymin = 0
        zmin = 0
        xmax += (2 * air_box_padding)
        ymax += (2 * air_box_padding)
        zmax += (2 * air_box_padding)

        # calculate a sane default for air_mesh_size (unless one was provided)
        if air_mesh_size == 0:
            air_mesh_size = round(((xmax - xmin) + (ymax - ymin) + (zmax - zmin)) / auto_air_mesh_factor, 5)
            print(f"Air mesh size automatically set to {air_mesh_size:.5f} m ({(air_mesh_size * 1000):.2f} mm):", )

        size_min = round(air_mesh_size * refinement_factor, 5)
        print(f"Most detailed mesh size automatically set to {size_min:.5f} m ({(size_min * 1000):.2f} mm):", )

        print(f"Final value for air_box_padding: {air_box_padding} m ({air_box_padding * 1000} mm)")
        print(f"Final value for air_mesh_size: {air_mesh_size} m ({air_mesh_size * 1000} mm)")
        print(f"Final value for refine_dist_min: {refine_dist_min} m ({refine_dist_min * 1000} mm)")
        print(f"Final value for refine_dist_max: {refine_dist_max} m ({refine_dist_max * 1000} mm)")

        # Define the air volume as a box
        air_volume = gmsh.model.occ.addBox(xmin, ymin, zmin, xmax - xmin, ymax - ymin, zmax - zmin)
        gmsh.model.occ.synchronize()

        print("Air volume tag:", air_volume)

        # Print the final bounding box of the geometry
        final_xmin, final_ymin, final_zmin, final_xmax, final_ymax, final_zmax = gmsh.model.getBoundingBox(-1, -1)
        print(f"Final bounding box dimensions with Air Volume (meters): x {final_xmin:.2f}, {final_xmax:.2f}, y {final_ymin:.2f}, {final_ymax:.2f}, z {final_zmin:.2f}, {final_zmax:.2f}")

        # Cut the geometry from the air volume
        print("Object volume tags:", object_volumes)
        air_volume_cut = gmsh.model.occ.fragment(
            [(3, air_volume)],
            [(3, tag) for tag in [v[1] for v in object_volumes]]
        )
        gmsh.model.occ.synchronize()
        print("Air volume fragment result:", air_volume_cut)

        remaining_volumes = gmsh.model.getEntities(dim=3)
        print("Remaining volumes after fragment:", remaining_volumes)

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

        if args.generate_elmer_files:
            # generate the elmer configuration
            print("Generating elmer config")
            bodies_for_elmer = []
            for dim, tag in object_volumes:
                name = gmsh.model.getEntityName(dim, tag)
                print(f"Testing body {name} (ID {tag}): Material = '{0}' to elmer config")
                material = elmer_config.name_to_material(name)
                body_force = elmer_config.name_to_body_force(name)
                body = SimpleNamespace(name=name, id=tag, material=material, body_force=body_force)
                bodies_for_elmer.append(body)
                print(f"Added body {name} (ID {body.id}): Material = '{body.material}', Body Force = '{body.body_force}' to elmer config")

            air_body = SimpleNamespace(name="Air", id=air_volume, material=elmer_config.name_to_material("Shapes/air"), body_force=None)
            bodies_for_elmer.append(air_body)
            print(f"Added air (ID {air_body.id}): Material = '{air_body.material}', Body Force = '{air_body.body_force}' to elmer config")

            # the surface tags for the air volume
            all_surfaces = gmsh.model.getEntities(dim=2)
            # the last 6 positions in the list (not zero indexed)are the outer surface of the air volume
            air_boundary_surface_ids = list(range(len(all_surfaces) - 5, len(all_surfaces) + 1))
            air_boundaries = " ".join(map(str, air_boundary_surface_ids))

            elmer_config_result = elmer_config.generate({
                "bodies": bodies_for_elmer,
                "air_boundaries": air_boundaries,
                "config_file": elmer_config_file,
                "result_file": elmer_result_file,
            })

            # Write elmer script to a file
            with open(elmer_config_file, "w") as f:
                f.write(elmer_config_result)

            # Create ELMERSOLVER_STARTINFO
            with open('ELMERSOLVER_STARTINFO', "w") as f:
                f.write(f"{elmer_config_file}\n1\n")


    except Exception as e:
        print(f"Error: {e}")

    finally:
        gmsh.finalize()

if __name__ == "__main__":
    main()
