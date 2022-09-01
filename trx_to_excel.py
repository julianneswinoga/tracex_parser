#!/usr/bin/python3

import argparse
from typing import *

import xlsxwriter
from colorhash import ColorHash
from colour import Color

from file_parser import parse_tracex_buffer
from events import *

parser = argparse.ArgumentParser(description="""
Convert TraceX event dumps into an Excel spreadsheet""")
parser.add_argument('input_trxs', nargs='+', action='store',
                    help='Path to the input trx file(s) that contains TraceX event data')

sem_ptr_map = {
    0x1018B318: 'blockingRxCompleted',
    0x1018B298: 'txBufferLock',
    0x1018B258: 'rxTransferLock',
}

mtx_ptr_map = {
}

timeout_map = {
    0xFFFFFFFF: 'wait_forever',
    0x00000000: 'no_wait',
}

remap_rtn_type = List[Union[str, Dict]]


custom_events_map = {
    5000: tracex_event_factory('uartOpen', class_name_is_fn_name=True,
                               arg_map=['line_num', '_2', '_3', '_4']),
    5001: tracex_event_factory('uartClose', class_name_is_fn_name=True,
                               arg_map=['line_num', CommonArg.obj_id, '_3', '_4']),
    5002: tracex_event_factory('uartRead', class_name_is_fn_name=True,
                               arg_map=[CommonArg.obj_id, 'count', 'vmin', 'vtime']),
    5003: tracex_event_factory('uartReadBufferBlockingPl', class_name_is_fn_name=True,
                               arg_map=['xferlen', CommonArg.timeout, '_3', '_4']),
    5004: tracex_event_factory('uartWaitForReceiveToCompleteWithBuffer',class_name_is_fn_name=True,
                               arg_map=['bytesReq', CommonArg.timeout, '_3', '_4']),
    5005: tracex_event_factory('uartWaitForReceiveToCompleteWithBufferReturnEarly', class_name_is_fn_name=True,
                               arg_map=['_1', '_2', '_3', '_4']),
    5006: tracex_event_factory('uartWaitForReceiveToCompleteWithBufferReturnLate', class_name_is_fn_name=True,
                               arg_map=['_1', '_2', '_3', '_4']),
    5007: tracex_event_factory('uartReadMinimumBytesBlocking', class_name_is_fn_name=True,
                               arg_map=['xferlen', 'vmin', 'vtime', '_4']),
    5008: tracex_event_factory('uartISRError', class_name_is_fn_name=True,
                               arg_map=['notifyLevel', 'cond1', 'cond2', '_4']),
    5009: tracex_event_factory('uartSetRxFifoTriggerLevelPl', class_name_is_fn_name=True,
                               arg_map=['triglevel', '_2', '_3', '_4']),
    5010: tracex_event_factory('ioctl', class_name_is_fn_name=True,
                               arg_map=[CommonArg.obj_id, 'num', '_3', '_4']),
}


# time, actor, event
rich_event_cell = List[Union[str, remap_rtn_type]]
converted_row_type = List[Union[int, str, Union[str, rich_event_cell]]]
meta_row_type = List[Union[int, str, Union[str, rich_event_cell], Dict]]


def convert_file(filepath: str) -> List[converted_row_type]:
    events, reg_map = parse_tracex_buffer(filepath, custom_events_map)

    out_lines = [['time', 'actor', 'event']]  # header
    for event in events:
        thread_str = event.thread_name if event.thread_name is not None else event.thread_ptr
        thread_format = {'font_color': ColorHash(thread_str).hex}

        fn_str = str(event.id if event.fn_name is None else event.fn_name)
        fn = [{'bold': True}, fn_str] if event.id > 4096 else [fn_str]

        arg_list = []
        for arg_name, arg_val in event.mapped_args.items():
            if arg_name == CommonArg.obj_id and arg_val in sem_ptr_map:
                arg_val = sem_ptr_map[arg_val]

            if arg_name in [CommonArg.obj_id]:
                arg_format = {'font_color': ColorHash(arg_val).hex}
                arg_list.append(arg_format)
            arg_list.append(f'{arg_name}={arg_val},')
        # arg_list = [','.join(f'{arg_name}={hex(arg_val)}' for arg_name, arg_val in zip(event.arg_map, event.args))]

        event_str = fn + ['('] + arg_list + [')']
        out_lines.append([event.timestamp, [thread_format, thread_str], event_str])
    return out_lines


meta_match_type = Optional[Tuple[str, str, int, int]]


class MetaMatches:
    @staticmethod
    def critical_section(lines, i) -> meta_match_type:
        if i + 5 > len(lines) - 1:
            return None
        semget = event_id_map[83].fn_name in str(lines[i + 0][2]) and 'txBufferLock' in str(lines[i + 0][2])
        tid1 = event_id_map[103].fn_name in str(lines[i + 1][2])
        preempt1 = event_id_map[107].fn_name in str(lines[i + 2][2])
        tid2 = event_id_map[103].fn_name in str(lines[i + 3][2])
        preempt2 = event_id_map[107].fn_name in str(lines[i + 4][2])
        semput = event_id_map[80].fn_name in str(lines[i + 5][2]) and 'txBufferLock' in str(lines[i + 5][2])
        if semget and tid1 and preempt1 and tid2 and preempt2 and semput:
            return 'criticalSection', 'green', i, i + 5
        return None

    @staticmethod
    def rx_transfer(lines, i) -> meta_match_type:
        semget = event_id_map[83].fn_name in str(lines[i + 0][2]) and 'rxTransferLock' in str(lines[i + 0][2])
        if not semget:
            return None
        for offset in range(len(lines) - i):
            semput = event_id_map[80].fn_name in str(lines[i + offset][2]) and 'rxTransferLock' in str(lines[i + offset][2])
            if semput:
                return 'rxTransfer', 'yellow', i, i + offset
        return None

    @staticmethod
    def mutex_locks(lines, i) -> meta_match_type:
        # we can always assume that mutexes are used for locking
        mtxget = event_id_map[52].fn_name in str(lines[i + 0][2])
        if not mtxget:
            return None
        # Good god convert this to a regex
        mtxName = lines[i + 0][2][3].split(CommonArg.obj_id, maxsplit=1)[1].split(',', maxsplit=1)[0].split('=', maxsplit=1)[1]
        for offset in range(len(lines) - i):
            mtxPut = event_id_map[57].fn_name in str(lines[i + offset][2]) and mtxName in str(lines[i + offset][2])
            if mtxPut:
                return mtxName, 'purple', i, i + offset
        return None

    @staticmethod
    def rx_completed(lines, i) -> meta_match_type:
        semput = event_id_map[80].fn_name in str(lines[i + 0][2]) and 'blockingRxCompleted' in str(lines[i + 0][2])
        if not semput:
            return None
        for offset in range(len(lines) - i):
            semget = event_id_map[83].fn_name in str(lines[i + offset][2]) and 'blockingRxCompleted' in str(lines[i + offset][2])
            if semget:
                return 'blockingRxCompleted', 'red', i, i + offset
        return None


def add_trace_metadata(lines: List[converted_row_type]) -> List[meta_row_type]:
    meta_tuples: List[meta_match_type] = []
    meta_match_fns = [
        MetaMatches.rx_transfer,
        MetaMatches.rx_completed,
        MetaMatches.mutex_locks,
        MetaMatches.critical_section,
    ]
    for meta_match_fn in meta_match_fns:
        for i in range(len(lines)):
            meta_match = meta_match_fn(lines, i)
            if meta_match is not None:
                meta_tuples.append(meta_match)

    meta_lines = lines
    for meta_index, meta_tuple in enumerate(meta_tuples):
        meta_name, meta_color, meta_start, meta_end = meta_tuple
        meta_color = Color(meta_color)  # Convert to Color class
        # toggle the hue back and forth to split up meta sections that are right next to each other
        hue_offset = -0.03 if meta_index % 2 == 0 else 0.03
        bg_color = Color(hsl=(meta_color.hue + hue_offset,
                              meta_color.saturation,
                              meta_color.luminance)).hex_l
        for i in range(meta_start, meta_end + 1):
            meta_dict = {
                'value': f'{meta_name}|{meta_index}',
                'formatting': {'bg_color': bg_color},
            }
            meta_lines[i].append(meta_dict)
    return meta_lines


def write_rich_event_cell(workbook, worksheet, row, col, rich_cell: remap_rtn_type):
    new_field_parts = []
    rich = False
    for cell_part in rich_cell:
        # Find and convert dicts into formats
        if not cell_part:
            pass  # Don't write empty strings
        elif isinstance(cell_part, dict):
            rich = True
            new_field_parts.append(workbook.add_format(cell_part))
        else:
            new_field_parts.append(cell_part)

    if rich:
        if len(new_field_parts) <= 2:
            # write_rich_string doesn't like it when you lead with a format for whatever reason
            new_field_parts.insert(0, ' ')
        worksheet.write_rich_string(row, col, *new_field_parts)
    else:
        # Normal string, no rich parts
        worksheet.write(row, col, ''.join(new_field_parts))


def write_workbook(filepath: str, lines: List[meta_row_type]):
    print(f'Writing to {filepath}')
    workbook = xlsxwriter.Workbook(filepath)
    worksheet = workbook.add_worksheet()

    for row, rich_row in enumerate(lines):
        for col, row_part in enumerate(rich_row):
            if isinstance(row_part, list):
                # remapped event column
                write_rich_event_cell(workbook, worksheet, row, col, row_part)
            elif isinstance(row_part, dict):
                # meta info
                worksheet.write(row, col, row_part['value'], workbook.add_format(row_part['formatting']))
            else:
                # time, actor columns (and non-remapped events)
                worksheet.write(row, col, row_part)
    workbook.close()


def main():
    for input_filepath in args.input_trxs:
        converted_lines = convert_file(input_filepath)
        metadata_lines = add_trace_metadata(converted_lines)
        if '.' in input_filepath:
            output_file = input_filepath.rsplit('.', maxsplit=1)[0] + '_converted.xlsx'
        else:
            output_file = input_filepath + '_converted.xlsx'
        write_workbook(output_file, metadata_lines)


if __name__ == '__main__':
    args = parser.parse_args()
    main()
