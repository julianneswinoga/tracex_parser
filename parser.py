#!/usr/bin/python3

import struct
import argparse
import copy
from typing import *


parser = argparse.ArgumentParser(description="""aaaaa""")
parser.add_argument('input_trxs', nargs='+', action='store',
                    help='Path to the input trx file(s) that contains TraceX event data')


class CStruct:
    def __init__(self, endian_str: str, fields: List[Tuple[str, str]]):
        self.data = {}
        self.endian_str = endian_str
        self.fields = fields

    def __repr__(self):
        return str(self.data)

    def __getitem__(self, key):
        return self.data[key]

    def __setitem__(self, key, value):
        self.data[key] = value

    def clear(self):
        self.data = {}

    def total_size(self):
        size = 0
        for field in self.fields:
            size += struct.calcsize(self.endian_str + field[0])
        return size

    def unpack(self, data: bytes):
        offset = 0
        for struct_def, field_name in self.fields:
            struct_format = self.endian_str + struct_def
            field_size = struct.calcsize(struct_format)
            unpacked_data = struct.unpack(struct_format, data[offset:offset + field_size])
            if len(unpacked_data) == 1:
                # unpack tuple
                self.data[field_name] = unpacked_data[0]
            else:
                self.data[field_name] = unpacked_data
            offset += field_size


def get_endian_str(control_header_id: bytes) -> str:
    magic_file_str = b'TXTB'
    magic_file_number_big = int('0x' + magic_file_str.hex(), 16)
    magic_file_number_little = int('0x' + magic_file_str[::-1].hex(), 16)
    # unpack assuming big endian
    header_id = struct.unpack('>L', control_header_id)[0]
    if header_id == magic_file_number_big:
        return '>'
    elif header_id == magic_file_number_little:
        return '<'
    else:
        raise Exception(f'Invalid magic number: {header_id}')


def get_control_header(endian_str: str, buf: bytes, start_idx: int) -> Tuple[CStruct, int]:
    control_header = CStruct(endian_str, [
        ('L', 'timer_valid_mask'),
        ('L', 'trace_base_address'),
        ('L', 'object_registry_start_pointer'),
        ('H', 'reserved1'),
        ('H', 'object_registry_name_size'),
        ('L', 'object_registry_end_pointer'),
        ('L', 'buffer_start_pointer'),
        ('L', 'buffer_end_pointer'),
        ('L', 'buffer_current_pointer'),
        ('L', 'reserved2'),
        ('L', 'reserved3'),
        ('L', 'reserved4'),
    ])
    control_header_end_idx = start_idx + control_header.total_size()
    control_header.unpack(buf[start_idx:control_header_end_idx])
    return control_header, control_header_end_idx


def get_object_registry(endian_str: str, buf: bytes, start_idx: int, control_header: CStruct) -> Tuple[List[CStruct], int]:
    object_entry = CStruct(endian_str, [
        ('B', 'object_registry_entry_object_available **'),
        ('B', 'object_registry_entry_object_type **'),
        ('B', 'object_registry_entry_object_reserved1'),
        ('B', 'object_registry_entry_object_reserved2'),
        ('L', 'thread_registry_entry_object_pointer'),
        ('L', 'object_registry_entry_object_parameter_1'),
        ('L', 'object_registry_entry_object_parameter_2'),
        (f"{control_header['object_registry_name_size']}s", 'thread_registry_entry_object_name'),
    ])
    object_registry_addr_range = (control_header['object_registry_end_pointer'] - control_header['object_registry_start_pointer'])
    if object_registry_addr_range % object_entry.total_size() != 0:
        raise Exception(f'Object registry range does not match object size: {object_registry_addr_range}, {object_entry.total_size()}')
    num_objects = object_registry_addr_range // object_entry.total_size()

    object_entry_start_idx = start_idx
    object_registry = []
    for obj_idx in range(num_objects):
        object_entry.clear()
        object_entry_end_idx = object_entry_start_idx + object_entry.total_size()
        object_entry.unpack(buf[object_entry_start_idx:object_entry_end_idx])
        # trim trailing NULs
        object_entry['thread_registry_entry_object_name'] = object_entry['thread_registry_entry_object_name'].strip(b'\0')
        object_registry.append(copy.deepcopy(object_entry))
        object_entry_start_idx += object_entry.total_size()
    return object_registry, object_entry_start_idx


def get_event_entries(endian_str: str, buf: bytes, start_idx: int, control_header: CStruct) -> Tuple[List[CStruct], int]:
    event_entry = CStruct(endian_str, [
        ('L', 'thread_pointer'),
        ('L', 'thread_priority'),
        ('L', 'event_id'),
        ('L', 'time_stamp'),
        ('L', 'information_field_1'),
        ('L', 'information_field_2'),
        ('L', 'information_field_3'),
        ('L', 'information_field_4'),
    ])
    event_entry_addr_range = (control_header['buffer_end_pointer'] - control_header['buffer_start_pointer'])
    if event_entry_addr_range % event_entry.total_size() != 0:
        raise Exception(f'Event entries range does not match event size: {event_entry_addr_range}, {event_entry.total_size()}')
    num_entries = event_entry_addr_range // event_entry.total_size()

    event_entry_start_idx = start_idx
    event_entries = []
    for event_idx in range(num_entries):
        event_entry.clear()
        object_entry_end_idx = event_entry_start_idx + event_entry.total_size()
        event_entry.unpack(buf[event_entry_start_idx:object_entry_end_idx])
        if event_entry['event_id'] != 0:
            event_entries.append(copy.deepcopy(event_entry))
        event_entry_start_idx += event_entry.total_size()
    event_entries.sort(key=lambda t: t['time_stamp'])
    return event_entries, event_entry_start_idx


def parse_tracex_buffer(filepath: str) -> Optional:
    print(f'Parsing {filepath}')

    # format is control header, object registry entries, trace/event entries
    with open(filepath, 'rb') as fp:
        tracex_buf = fp.read()

    # Read control header id to figure out endianness
    header_id_end_idx = 4
    endian_str = get_endian_str(tracex_buf[0:header_id_end_idx])
    # Unpack the rest of the control header
    control_header, control_header_end_idx = get_control_header(endian_str, tracex_buf, header_id_end_idx)
    print(control_header)

    # Unpack object entries
    object_registry, object_registry_end_idx = get_object_registry(endian_str, tracex_buf, control_header_end_idx, control_header)

    # Unpack trace/event entries
    event_entries, _ = get_event_entries(endian_str, tracex_buf, object_registry_end_idx, control_header)
    print('\n'.join(str(t) for t in event_entries))


def main():
    for input_filepath in args.input_trxs:
        parse_tracex_buffer(input_filepath)


if __name__ == '__main__':
    args = parser.parse_args()
    main()
