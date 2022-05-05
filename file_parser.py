#!/usr/bin/python3

import struct
import argparse
import copy
from typing import *

from events import TraceXEvent, convert_events

parser = argparse.ArgumentParser(description="""
TraceX parser module, intended as a library but can be used as a standalone script""")
parser.add_argument('input_trxs', nargs='+', action='store',
                    help='Path to the input trx file(s) that contains TraceX event data')

"""
see https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter11 for
documentation on how a TraceX buffer is formatted
"""


class CStruct:
    def __init__(self, endian_str: str, fields: List[Tuple[str, str]]):
        self.data = {}
        self.endian_str = endian_str
        self.fields = fields

    def __repr__(self):
        return str({k: hex(v) if isinstance(v, int) else v
                    for k, v in self.data.items()
                    if 'reserved' not in k
                    })

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


def get_endian_str(buf: bytes) -> Tuple[str, int]:
    magic_file_str = b'TXTB'
    magic_str_size = len(magic_file_str)
    magic_file_number_big = int('0x' + magic_file_str.hex(), 16)
    magic_file_number_little = int('0x' + magic_file_str[::-1].hex(), 16)
    # unpack assuming big endian
    header_id = struct.unpack('>L', buf[0:magic_str_size])[0]
    if header_id == magic_file_number_big:
        return '>', magic_str_size
    elif header_id == magic_file_number_little:
        return '<', magic_str_size
    else:
        raise Exception(f'Invalid magic number: {hex(header_id)}')


def get_control_header(endian_str: str, buf: bytes, start_idx: int) -> Tuple[CStruct, int]:
    control_header = CStruct(endian_str, [
        ('L', 'timer_valid_mask'),
        ('L', 'trace_base_address'),
        ('L', 'obj_reg_start_pointer'),
        ('H', 'reserved1'),
        ('H', 'obj_reg_name_size'),
        ('L', 'obj_reg_end_pointer'),
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
    object_name_len = control_header['obj_reg_name_size']
    object_entry = CStruct(endian_str, [
        ('B', 'obj_reg_entry_obj_available **'),
        ('B', 'obj_reg_entry_obj_type **'),
        ('B', 'obj_reg_entry_obj_reserved1'),
        ('B', 'obj_reg_entry_obj_reserved2'),
        ('L', 'thread_reg_entry_obj_pointer'),
        ('L', 'obj_reg_entry_obj_parameter_1'),
        ('L', 'obj_reg_entry_obj_parameter_2'),
        (f'{object_name_len}s', 'thread_reg_entry_obj_name'),
    ])
    object_size = object_entry.total_size()

    obj_reg_addr_range = (control_header['obj_reg_end_pointer'] - control_header['obj_reg_start_pointer'])
    if obj_reg_addr_range % object_size != 0:
        raise Exception(f'Object registry range does not match object size: {obj_reg_addr_range}, {object_size}')
    num_objects = obj_reg_addr_range // object_size

    object_entry_start_idx = start_idx
    object_registry = []
    for obj_idx in range(num_objects):
        object_entry.clear()
        object_entry_end_idx = object_entry_start_idx + object_size
        object_entry.unpack(buf[object_entry_start_idx:object_entry_end_idx])
        # trim trailing NULs
        object_entry['thread_reg_entry_obj_name'] = object_entry['thread_reg_entry_obj_name'].strip(b'\0')
        object_registry.append(copy.deepcopy(object_entry))
        object_entry_start_idx += object_size
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
    event_size = event_entry.total_size()

    event_entry_addr_range = (control_header['buffer_end_pointer'] - control_header['buffer_start_pointer'])
    if event_entry_addr_range % event_size != 0:
        raise Exception(f'Event entries range does not match event size: {event_entry_addr_range}, {event_size}')
    num_entries = event_entry_addr_range // event_size

    event_entry_start_idx = start_idx
    raw_events = []
    for event_idx in range(num_entries):
        event_entry.clear()
        object_entry_end_idx = event_entry_start_idx + event_size
        event_entry.unpack(buf[event_entry_start_idx:object_entry_end_idx])
        if event_entry['event_id'] != 0:
            raw_events.append(copy.deepcopy(event_entry))
        event_entry_start_idx += event_size
    raw_events.sort(key=lambda t: t['time_stamp'])
    return raw_events, event_entry_start_idx


def parse_tracex_buffer(filepath: str, custom_events_map: Optional[Dict[int, TraceXEvent]] = None) -> List[TraceXEvent]:
    # format is control header, object registry entries, trace/event entries
    with open(filepath, 'rb') as fp:
        tracex_buf = fp.read()

    # Read control header id to figure out endianness
    endian_str, header_id_end_idx = get_endian_str(tracex_buf)
    # Unpack the rest of the control header
    control_header, control_header_end_idx = get_control_header(endian_str, tracex_buf, header_id_end_idx)

    # Unpack object entries
    object_registry, object_registry_end_idx = get_object_registry(endian_str, tracex_buf, control_header_end_idx,
                                                                   control_header)

    # Unpack trace/event entries
    raw_events, _ = get_event_entries(endian_str, tracex_buf, object_registry_end_idx, control_header)

    # Convert raw events to more human-understandable events, then apply the object registry
    tracex_events = convert_events(raw_events, object_registry, custom_events_map)
    return tracex_events


def main():
    for input_filepath in args.input_trxs:
        print(f'Parsing {input_filepath}')
        tracex_events = parse_tracex_buffer(input_filepath)
        print(f'total events: {len(tracex_events)}')
        total_ticks = tracex_events[-1].timestamp - tracex_events[0].timestamp
        print(f'delta ticks: {total_ticks}')

        print('Event Histogram:')
        events_histogram = {}
        for tracex_event in tracex_events:
            event_id = tracex_event.fn_name if tracex_event.fn_name else tracex_event.id
            if event_id in events_histogram:
                events_histogram[event_id] += 1
            else:
                events_histogram[event_id] = 1
        for event_id in sorted(events_histogram, key=lambda k: events_histogram[k], reverse=True):
            print(f'{event_id:<20}{events_histogram[event_id]}')

        print('All events:')
        for tracex_event in tracex_events:
            print(tracex_event)


if __name__ == '__main__':
    args = parser.parse_args()
    from signal import signal, SIGPIPE, SIG_DFL

    signal(SIGPIPE, SIG_DFL)
    main()