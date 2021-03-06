import sys
sys.path.append('ParseCAN')
from ParseCAN.ParseCAN.spec import Endianness, Type

from math import ceil, floor, log2
from common import pack_unpack_c_path, pack_unpack_c_base_path, coord, is_multplxd, frame_handler


def swap_endianness_fn(type: Type):
    if type.isbool():
        return ''

    return 'swap_' + type.type


def write_atoms_unpack(fw, atoms, tot_name):
    for atom in atoms:
        if atom.type.isenum():
            enum_name = coord(tot_name, atom.name) + '_T'

            fw(
                '\t' 'type_out->' + atom.name + ' = (' + enum_name + ')EXTRACT(bitstring, ' +
                str(atom.slice.start) + ', ' + str(atom.slice.length) + ');' '\n'
            )
        elif atom.type.type == 'bool':
            fw(
                '\t' 'type_out->' + atom.name + ' = EXTRACT(bitstring, ' + str(atom.slice.start) + ', ' +
                str(atom.slice.length) + ');' '\n'
            )
        else:
            if atom.type.endianness == Endianness.LITTLE:
                fw(
                    '\t' 'type_out->' + atom.name + ' = ' + swap_endianness_fn(atom.type) +
                    '(EXTRACT(bitstring, ' + str(atom.slice.start) + ', ' +
                    str(atom.slice.length) + '));' '\n'
                )
            else:
                if atom.type.issigned():
                    fw(
                        '\t' 'type_out->' + atom.name + ' = SIGN(EXTRACT(bitstring, ' +
                        str(atom.slice.start) + ', ' + str(atom.slice.length) + '), ' +
                        str(atom.slice.length) + ');' '\n'
                    )
                else:
                    fw(
                        '\t' 'type_out->' + atom.name + ' = EXTRACT(bitstring, ' +
                        str(atom.slice.start) + ', ' + str(atom.slice.length) + ');' '\n'
                    )


def write_can_unpack(frame, name_prepends, fw):
    tot_name = coord(name_prepends, frame.name, prefix=False)
    fw(
        'void CANlib_Unpack_' + tot_name +'(Frame *can_in, CANlib_' + tot_name +
        '_T *type_out) {\n'
        '\t' 'uint64_t bitstring = 0;' '\n'
        '\t' 'to_bitstring(can_in->data, &bitstring);\n'
    )

    write_atoms_unpack(fw, frame.atom, tot_name)

    fw('}' '\n\n')


def can_pack_handler(frame, name_prepends, bus_ext, fw, parent_slice=None):
    if is_multplxd(frame):
        if parent_slice is not None:
            raise NotImplementedError("Multilevel multiplexing not yet supported!")
        for sub_frame in frame.frame:
            can_pack_handler(sub_frame, name_prepends + '_' + frame.name, bus_ext, fw, frame.slice)
    else:
        write_can_pack(frame, name_prepends, bus_ext, fw, parent_slice)

def write_can_pack(frame, name_prepends, bus_ext, fw, parent_slice=None):
    is_multplxd_subframe = parent_slice is not None

    tot_name = coord(name_prepends, frame.name, prefix=False)
    fw(
        'void CANlib_Pack_' + tot_name + '(CANlib_' + tot_name + '_T *type_in, Frame *can_out)'
        '{\n\t' 'uint64_t bitstring = 0;' '\n'
    )

    if is_multplxd_subframe:
        if True: # TODO: check endianness, like atom.type.endianness == Endianness.LITTLE:
            # TODO: Actually grab key type
            fw(
                '\t' 'bitstring = INSERT(CANlib_' + tot_name +
                '_key, bitstring, ' + str(parent_slice.start) + ', ' + str(parent_slice.length) +
                ');' '\n\n'
            )

    write_atoms_pack(fw, frame.atom)

    length = max(atom.slice.start + atom.slice.length for atom in frame.atom)

    fw(
        '\t' 'from_bitstring(&bitstring, can_out->data);' '\n'
    )

    key_name = ""
    if not is_multplxd_subframe:
        key_name = coord(name_prepends, frame.name, 'key')
    else:
        key_name = coord(name_prepends, 'key')

    fw(
        '\t' 'can_out->id = {};'.format(key_name) + '\n'
        '\t' 'can_out->dlc = ' + str(ceil(length / 8)) + ';' '\n'
        '\t' 'can_out->extended = ' + str(bus_ext).lower() + ';' '\n'
        '}' '\n\n'
    )


def write_atoms_pack(fw, atoms):
    for atom in atoms:
        # HACK/TODO: This is assuming big endian systems that run CANlib
        if atom.type.endianness == Endianness.LITTLE:
            fw(
                '\t' 'bitstring = INSERT(' + swap_endianness_fn(atom.type) + '(type_in->' + atom.name + '), bitstring, ' +
                str(atom.slice.start) + ', ' + str(atom.slice.length) + ');' '\n\n'
            )
        else:
            fw(
                '\t' 'bitstring = INSERT(type_in->' + atom.name + ', bitstring, ' + str(atom.slice.start) +
                ', ' + str(atom.slice.length) + ');' '\n'
            )


def write(can, output_path=pack_unpack_c_path, base_path=pack_unpack_c_base_path):
    '''
    Generate pack_unpack.c file.

    :param output_path: file to be written to
    :param can: CAN spec
    :param base_path: File with template code that's not autogenerated
    '''
    with open(output_path, 'w') as f:
        fw = f.write

        fw('#include "pack_unpack.h"\n')

        # Copy over base
        with open(base_path) as base:
            lines = base.readlines()
            f.writelines(lines)

        fw('\n')

        for bus in can.bus:
            for msg in bus.frame:
                can_pack_handler(msg, bus.name, bus.extended, fw)
                frame_handler(msg, bus.name, write_can_unpack, fw)
