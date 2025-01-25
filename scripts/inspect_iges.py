import gmsh
import argparse

# Initialize Gmsh
gmsh.initialize()

try:
    # ---------------- Parse Arguments ----------------
    parser = argparse.ArgumentParser(description="Extract metadata from an IGES file for material mapping.")
    parser.add_argument("input_file", type=str, help="Path to the input IGES file.")
    args = parser.parse_args()

    input_file = args.input_file
    # --------------------------------------------------

    # Load the IGES file
    print(f"Loading IGES file: {input_file}")
    gmsh.model.occ.importShapes(input_file)
    gmsh.model.occ.synchronize()

    # Fetch and print metadata
    print("\n--- Entity Metadata ---")

    # 1. Print all volumes (dim=3)
    volumes = gmsh.model.getEntities(dim=3)
    for vol in volumes:
        name = gmsh.model.getEntityName(vol[0], vol[1])
        bbox = gmsh.model.getBoundingBox(vol[0], vol[1])
        print(f"Volume {vol[1]} : {name}")

except Exception as e:
    print(f"An error occurred: {e}")
finally:
    gmsh.finalize()
