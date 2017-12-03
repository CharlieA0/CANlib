"""
Generate header files that set up structs (bms.h, can_node.h, etc.).
Run this file to write just these files or main.py to write all files.
"""
import sys
sys.path.append("ParseCAN")
import ParseCAN
from common import struct_paths, spec_path

expected_keys = ["bms", "cannode", "currentsensor", "dash", "vcu"]


def write(output_paths, spec_path):
    """
    Write the header files for the main structs in the library.

    :param output_paths: a dictionary with a path for the BMS, CAN node, current sensor, dash, and VCU header files
    :param spec_path: path to the CAN spec
    """
    spec = ParseCAN.spec.can(spec_path)
    try:
        for key in expected_keys:
            with open(output_paths[key], 'w') as f:
                f.write("#ifndef _MY18_CAN_LIBRARY_" + key.upper() + "_H\n")
                f.write("#define _MY18_CAN_LIBRARY_" + key.upper() + "_H\n\n")
                f.write('#include "can_validator/fsae_can_spec.h"\n\n')
                f.write("#include <stdint.h>\n")
                f.write("#include <stdbool.h>\n\n")
                f.write('#include "ids.h"\n\n')

                for message in spec.messages.values():
                    if (message.name.lower().startswith(key)):
                        f.write("typedef struct {\n")
                        for segment_name, segment in message.segments.items():
                            if segment.c_type != "enum":
                                field_name = segment_name
                                if field_name == 'unused':
                                    continue
                                f.write("  " + segment.c_type + " " + field_name + ";\n")
                            else:
                                enum_name = "Can_" + message.name
                                enum_name += "ID_T"
                                f.write("  " + enum_name + " " + segment_name + ";\n")
                        f.write("} Can_" + message.name + "_T;\n\n")
                f.write("#endif // _MY18_CAN_LIBRARY_" + key.upper() + "_H")
    except KeyError as e:
        print("No path passed for " + e.args[0] + " header file, please add it to output_paths dictionary")
        raise


if __name__ == "__main__":
    write(struct_paths, spec_path)