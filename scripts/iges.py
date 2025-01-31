# iges.py

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

# return the units from a IGES file
def get_iges_units(filename):
    """
    Parses a IGES file to extract the units name from its Global Section.
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
