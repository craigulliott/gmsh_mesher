import os
import argparse
import gmsh
import re

def is_iges_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline().strip()
            # Check if the file starts with 'S' followed by spaces and a number
            return first_line.startswith("S") and first_line[1:].strip().isdigit()
    except Exception as e:
        print(f"Error reading file: {e}")
        return False

# for parsing IGES files
def decode_hollerith(s):
    """
    If 's' matches the pattern nH..., decode as a Hollerith string.
    Otherwise return s unchanged.
    """
    match = re.match(r'^(\d+)H(.*)', s)
    if match:
        length = int(match.group(1))
        return match.group(2)[:length]
    return s

# return the units from an IGES file
def get_iges_units(filename):
    """
    Parses an IGES file to extract the units name from its Global Section.
    Returns a tuple: (units_flag, units_name), where units_flag is the
    numeric code and units_name is the textual representation.
    """
    with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    # 1) Collect the Global Section lines (marked 'G' in column 73)
    global_lines = []
    for line in lines:
        # Ensure line is at least 73 chars and check the flag in column 73 (index 72)
        if len(line) >= 73 and line[72] == 'G':
            # Keep only the first 72 characters (ASCII data) ignoring columns 73-80
            global_lines.append(line[:72])

    # 2) Concatenate Global Section lines into one string
    #    (They form a single “record” logically)
    global_data = ''.join(global_lines)

    if not global_data:
        raise ValueError("No Global Section found (no lines with 'G' flag).")

    # 3) The first character is the parameter delimiter (e.g. ',')
    #    The second character is the record delimiter (e.g. ';')
    param_delimiter  = global_data[0]
    record_delimiter = global_data[1]

    # 4) Sometimes the Global Section is also split by the record delimiter,
    #    but often there's only one record. We'll split by the param_delimiter
    #    to get the parameter fields. (If the file uses record_delimiter in
    #    between, you may need to re-concatenate or handle carefully.)
    #    For simplicity, assume the entire global_data is one record we can
    #    split by param_delimiter.

    # Strip off the first two characters (param_delim + record_delim)
    # before splitting, as they are not part of the actual fields.
    # Then split on the param_delimiter.
    fields = global_data[2:].split(param_delimiter)

    # Make sure we have enough fields
    if len(fields) < 15:
        raise ValueError("Global Section does not have enough fields to extract units.")

    return decode_hollerith(fields[12].strip())

def main():
    try:
        # Initialize Gmsh
        gmsh.initialize()
        gmsh.option.setNumber("General.Terminal", 1)

        # ---------------- Parse Arguments ----------------
        parser = argparse.ArgumentParser(description="Generate a mesh from an input IGES file.")
        parser.add_argument("input_file", type=str, help="Path to the input IGES file.")
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
            "--output_file", type=str, default="final_mesh.msh",
            help="Path to the output mesh file (default: final_mesh.msh)."
        )
        args = parser.parse_args()

        input_file = args.input_file
        output_file = args.output_file
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
            auto_air_mesh_factor = 70
            # override (unless its been set manually)
            if args.refinement_factor == 0.02:
                refinement_factor = 0.015

        else:
            auto_air_mesh_factor = 50

        # --------------------------------------------------

        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input IGES file not found: {input_file}")

        if not is_iges_file(input_file):
            raise FileNotFoundError(f"Input file did not appear to be an IGES file")

        unit_name = get_iges_units(input_file)

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

        print("Default number of threads used:", gmsh.option.getNumber("General.NumThreads"))
        cores = os.cpu_count()
        print(f"Number of logical processors (cores) on this machine: {cores}")
        if cores > 2:
            gmsh.option.setNumber("General.NumThreads", cores - 1)
            print(f"Number of threads set to {cores - 1}")


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
        # Disabled until we figure out how to configure elmer to handle them
        # gmsh.option.setNumber("Mesh.ElementOrder", 2)

        # Enable mesh optimization to reduce skewness and improve element shapes
        gmsh.option.setNumber("Mesh.Optimize", 3) # 3 passes
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

        # Create air volume
        xmin -= air_box_padding
        ymin -= air_box_padding
        zmin -= air_box_padding
        xmax += air_box_padding
        ymax += air_box_padding
        zmax += air_box_padding

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

        # Print the bounding box of the geometry
        air_vol_xmin, air_vol_ymin, air_vol_zmin, air_vol_xmax, air_vol_ymax, air_vol_zmax = gmsh.model.getBoundingBox(-1, -1)
        print(f"Bounding box dimensions with Air Volume (meters): x {air_vol_xmin:.2f}, {air_vol_xmax:.2f}, y {air_vol_ymin:.2f}, {air_vol_ymax:.2f}, z {air_vol_zmin:.2f}, {air_vol_zmax:.2f}")

        print(f"Moving geometry to the 0,0 origin so that none of the study falls in a negative quadrant")
        x_offset = -air_vol_xmin
        y_offset = -air_vol_ymin
        z_offset = -air_vol_zmin
        gmsh.model.occ.translate([(3, air_volume)], x_offset, y_offset, z_offset)
        gmsh.model.occ.translate([(3, tag) for tag in [v[1] for v in object_volumes]], x_offset, y_offset, z_offset)
        gmsh.model.occ.synchronize()

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
