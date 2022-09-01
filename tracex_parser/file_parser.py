#!/usr/bin/python3

import struct
import argparse
import copy
import sys
from typing import *

from .helpers import TraceXParseException, CStruct, TextColour
from .events import TraceXEvent, convert_events

parser = argparse.ArgumentParser(description="""
TraceX parser module, intended as a library but can be used as a standalone script""")
parser.add_argument('input_trxs', nargs='+', action='store',
                    help='Path to the input trx file(s) that contains TraceX event data')
parser.add_argument('-v', '--verbose', action='count', default=0,
                    help='Set the verbosity of logging')
parser.add_argument('-n', '--nocolor', action='store_true', help='Do not add color to the output')


def get_endian_str(buf: bytes) -> Tuple[str, int]:
    """
    Returns the endianness of the TraceX dump based on the first couple bytes
    """
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
        raise TraceXParseException(f'Invalid magic number: {hex(header_id)}')


def get_control_header(endian_str: str, buf: bytes, start_idx: int) -> Tuple[CStruct, int]:
    """
    @see https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter11#event-trace-control-header
    Unpacks the control header into a dict-like CStruct
    """
    control_header = CStruct(endian_str, [
        ('L', 'timer_valid_mask'),
        ('L', 'trace_base_address'),
        ('L', 'obj_reg_start_pointer'),
        ('H', 'reserved1'),
        ('H', 'obj_reg_name_size'),
        ('L', 'obj_reg_end_pointer'),
        ('L', 'buf_start_ptr'),
        ('L', 'buf_end_ptr'),
        ('L', 'buf_cur_ptr'),
        ('L', 'reserved2'),
        ('L', 'reserved3'),
        ('L', 'reserved4'),
    ])
    control_header_end_idx = start_idx + control_header.total_size()
    control_header.unpack(buf[start_idx:control_header_end_idx])
    return control_header, control_header_end_idx


def get_object_registry(endian_str: str, buf: bytes, start_idx: int, control_header: CStruct) \
        -> Tuple[Dict[int, CStruct], int]:
    """
    @see https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter11#event-trace-object-registry
    Unpacks the object registry into a list of dict-like CStructs
    """
    object_name_len = control_header['obj_reg_name_size']
    object_entry = CStruct(endian_str, [
        ('B', 'obj_reg_entry_obj_available **'),
        ('B', 'obj_reg_entry_obj_type **'),
        ('B', 'reserved1'),
        ('B', 'reserved2'),
        ('L', 'thread_reg_entry_obj_ptr'),
        ('L', 'obj_reg_entry_obj_parameter_1'),
        ('L', 'obj_reg_entry_obj_parameter_2'),
        (f'{object_name_len}s', 'thread_reg_entry_obj_name'),
    ])
    object_size = object_entry.total_size()

    obj_reg_addr_range = (control_header['obj_reg_end_pointer'] - control_header['obj_reg_start_pointer'])
    if obj_reg_addr_range % object_size != 0:
        raise TraceXParseException(
            f'Object registry range does not match object size: {obj_reg_addr_range}, {object_size}')
    num_objects = obj_reg_addr_range // object_size

    object_entry_start_idx = start_idx
    object_registry_arr = []
    for obj_idx in range(num_objects):
        object_entry.clear()
        object_entry_end_idx = object_entry_start_idx + object_size
        object_entry.unpack(buf[object_entry_start_idx:object_entry_end_idx])
        # trim trailing NULs
        object_entry['thread_reg_entry_obj_name'] = object_entry['thread_reg_entry_obj_name'].strip(b'\0')
        object_registry_arr.append(copy.deepcopy(object_entry))
        object_entry_start_idx += object_size

    obj_reg_map = {}
    for obj in object_registry_arr:
        obj_ptr = obj['thread_reg_entry_obj_ptr']
        if obj_ptr != 0x0 and obj_ptr in obj_reg_map:
            print(f'{obj} is has the same address of {obj_reg_map[obj_ptr]} in the object registry! Not overwriting')
            continue
        obj_reg_map[obj_ptr] = obj

    return obj_reg_map, object_entry_start_idx


def get_event_entries(endian_str: str, buf: bytes, start_idx: int, control_header: CStruct) \
        -> Tuple[List[CStruct], int]:
    """
    @see https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter11#event-trace-entries
    Unpacks the TraceX events into a list of dict-like CStructs.
    Events are sorted by their timestamp.
    """
    event_entry = CStruct(endian_str, [
        ('L', 'thread_ptr'),
        ('L', 'thread_priority'),
        ('L', 'event_id'),
        ('L', 'time_stamp'),
        ('L', 'info_field_1'),
        ('L', 'info_field_2'),
        ('L', 'info_field_3'),
        ('L', 'info_field_4'),
    ])
    event_size = event_entry.total_size()

    event_entry_addr_range = (control_header['buf_end_ptr'] - control_header['buf_start_ptr'])
    if event_entry_addr_range % event_size != 0:
        raise TraceXParseException(
            f'Event entries range does not match event size: {event_entry_addr_range}, {event_size}')
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


def parse_tracex_buffer(filepath: str, custom_events_map: Optional[Dict[int, TraceXEvent]] = None) \
        -> Tuple[List[TraceXEvent], Dict[int, CStruct]]:
    """
    Parse a TraceX binary dump (canonically .trx) into a list of TraceXEvent classes
    :param filepath: Path to where the TraceX file is
    :param custom_events_map: Dictionary of {id: TraceXEvents} to map custom events (id >= 4096) into human-readable
    events.
    :return: List of TraceX events
    """
    # Overall format is control header, object registry entries, trace/event entries
    with open(filepath, 'rb') as fp:
        tracex_buf = fp.read()

    # Read control header id to figure out endianness
    endian_str, header_id_end_idx = get_endian_str(tracex_buf)
    # Unpack the rest of the control header
    control_header, control_header_end_idx = get_control_header(endian_str, tracex_buf, header_id_end_idx)

    # Unpack object entries
    obj_reg_map, obj_reg_end_idx = get_object_registry(endian_str, tracex_buf, control_header_end_idx, control_header)

    # Unpack trace/event entries
    raw_events, _event_end_idx = get_event_entries(endian_str, tracex_buf, obj_reg_end_idx, control_header)
    # Could do some error checking here about the event end idx, but I don't think it would be worth it

    # Convert raw events to more human-understandable events, then apply the object registry
    tracex_events = convert_events(raw_events, obj_reg_map, custom_events_map)
    return tracex_events, obj_reg_map


def main():
    for input_filepath in args.input_trxs:
        print(f'Parsing {input_filepath}')
        tracex_events, obj_reg_map = parse_tracex_buffer(input_filepath)
        print(f'{colour.wte}total events: {len(tracex_events)}{colour.rst}')
        print(f'{colour.wte}object registry size: {len(obj_reg_map.keys())}{colour.rst}')
        total_ticks = tracex_events[-1].timestamp - tracex_events[0].timestamp
        print(f'{colour.wte}delta ticks: {total_ticks}{colour.rst}')

        if args.verbose > 0:
            print(f'{colour.grn}Event Histogram:{colour.rst}')
            events_histogram = {}
            for tracex_event in tracex_events:
                event_id = tracex_event.fn_name if tracex_event.fn_name else tracex_event.id
                if event_id in events_histogram:
                    events_histogram[event_id] += 1
                else:
                    events_histogram[event_id] = 1
            for event_id in sorted(events_histogram, key=lambda k: events_histogram[k], reverse=True):
                event_colour = colour.blu if isinstance(event_id, str) else colour.yel
                print(f'{event_colour}{event_id:<20}{events_histogram[event_id]}{colour.rst}')

        if args.verbose > 1:
            print(f'{colour.grn}All events:{colour.rst}')
            for tracex_event in tracex_events:
                print(tracex_event.as_str(colour))


if __name__ == '__main__':
    args = parser.parse_args()

    from signal import signal, SIGPIPE, SIG_DFL
    # Don't break when piping output
    signal(SIGPIPE, SIG_DFL)

    # set up colours
    have_colours = sys.stdout.isatty() and not args.nocolor
    colour = TextColour(have_colours)
    main()
