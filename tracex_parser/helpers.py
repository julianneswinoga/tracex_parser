import struct
from typing import *


class TraceXBaseException(Exception):
    pass


class TraceXParseException(TraceXBaseException):
    pass


class TraceXEventException(TraceXBaseException):
    pass


class CStruct:
    """
    Dict-like helper class to help unpack raw binary data into a dictionary
    """
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


class TextColour:
    def __init__(self, have_colours: bool = True):
        self.blk = '\u001b[30m' if have_colours else ''
        self.red = '\u001b[31m' if have_colours else ''
        self.grn = '\u001b[32m' if have_colours else ''
        self.yel = '\u001b[33m' if have_colours else ''
        self.blu = '\u001b[34m' if have_colours else ''
        self.mag = '\u001b[35m' if have_colours else ''
        self.cya = '\u001b[36m' if have_colours else ''
        self.wte = '\u001b[37m' if have_colours else ''
        self.rst = '\u001b[0m' if have_colours else ''
