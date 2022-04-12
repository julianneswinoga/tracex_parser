#!/usr/bin/python3

import argparse
from typing import *

import xlsxwriter
from colorhash import ColorHash
from colour import Color

from parser import parse_tracex_buffer
from events import *

parser = argparse.ArgumentParser(description="""aaaaa""")
parser.add_argument('input_csvs', nargs='+', action='store',
                    help='Path to the input csv file(s) that contains TraceX event data (exported from Tracealyzer)')

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


class uartOpen(TraceXEvent):
    fn_name = 'uartOpen'
    arg_map = ['line_num', '_2', '_3', '_4']


class uartClose(TraceXEvent):
    fn_name = 'uartClose'
    arg_map = ['line_num', CommonArgsMap.obj_id, '_3', '_4']


class uartRead(TraceXEvent):
    fn_name = 'uartRead'
    arg_map = [CommonArgsMap.obj_id, 'count', 'vmin', 'vtime']


class uartReadBufferBlockingPl(TraceXEvent):
    fn_name = 'uartReadBufferBlockingPl'
    arg_map = ['xferlen', CommonArgsMap.timeout, '_3', '_4']


class uartWaitForReceiveToCompleteWithBuffer(TraceXEvent):
    fn_name = 'uartWaitForReceiveToCompleteWithBuffer'
    arg_map = ['bytesReq', CommonArgsMap.timeout, '_3', '_4']


class uartWaitForReceiveToCompleteWithBufferReturnEarly(TraceXEvent):
    fn_name = 'uartWaitForReceiveToCompleteWithBufferReturnEarly'


class uartWaitForReceiveToCompleteWithBufferReturnLate(TraceXEvent):
    fn_name = 'uartWaitForReceiveToCompleteWithBufferReturnLate'


class uartReadMinimumBytesBlocking(TraceXEvent):
    fn_name = 'uartReadMinimumBytesBlocking'
    arg_map = ['xferlen', 'vmin', 'vtime', '_4']


class uartISRError(TraceXEvent):
    fn_name = 'uartISRError'
    arg_map = ['notifyLevel', 'cond1', 'cond2', '_4']


class uartSetRxFifoTriggerLevelPl(TraceXEvent):
    fn_name = 'uartSetRxFifoTriggerLevelPl'
    arg_map = ['triglevel', '_3', '_4', '_4']


custom_events_map = {
    5000: uartOpen,
    5001: uartClose,
    5002: uartRead,
    5003: uartReadBufferBlockingPl,
    5004: uartWaitForReceiveToCompleteWithBuffer,
    5005: uartWaitForReceiveToCompleteWithBufferReturnEarly,
    5006: uartWaitForReceiveToCompleteWithBufferReturnLate,
    5007: uartReadMinimumBytesBlocking,
    5008: uartISRError,
    5009: uartSetRxFifoTriggerLevelPl,
}


# time, actor, event
rich_event_cell = List[Union[str, remap_rtn_type]]
converted_row_type = List[Union[int, str, Union[str, rich_event_cell]]]
meta_row_type = List[Union[int, str, Union[str, rich_event_cell], Dict]]


def convert_file(filepath: str) -> List[converted_row_type]:
    events = parse_tracex_buffer(filepath, custom_events_map)

    out_lines = [['time', 'actor', 'event']]  # header
    for event in events:
        thread_str = event.thread_name if event.thread_name is not None else event.thread_ptr
        thread_format = {'font_color': ColorHash(thread_str).hex}

        fn_str = str(event.id if event.fn_name is None else event.fn_name)
        if event.id > 4096:
            fn = [{'bold': True}, fn_str, '(']
        else:
            fn = [fn_str, '(']

        if isinstance(event.args, list):
            if event.arg_map is None:
                arg_list = [','.join(f'{arg_num}={hex(arg_val)}' for arg_num, arg_val in enumerate(event.args))]
            else:
                arg_list = [','.join(f'{arg_name}={hex(arg_val)}' for arg_name, arg_val in zip(event.arg_map, event.args))]
        else:
            arg_list = []
            for arg_name, arg_val in event.mapped_args.items():
                if arg_name == CommonArgsMap.obj_id and arg_val in sem_ptr_map:
                    arg_val = sem_ptr_map[arg_val]

                if arg_name in [CommonArgsMap.obj_id]:
                    arg_format = {'font_color': ColorHash(arg_name).hex}
                    arg_list.append(arg_format)
                arg_list.append(f'{arg_name}={arg_val},')

        event_str = fn + arg_list + [')']
        out_lines.append([event.timestamp, [thread_format, thread_str], event_str])
    return out_lines


meta_match_type = Optional[Tuple[str, int, int]]


class MetaMatches:
    @staticmethod
    def critical_section(lines, i) -> meta_match_type:
        if i + 5 > len(lines) - 1:
            return None
        semget = SemGetEvent.fn_name in str(lines[i + 0][2]) and 'txBufferLock' in str(lines[i + 0][2])
        tid1 = ThreadIdEvent.fn_name in str(lines[i + 1][2])
        preempt1 = ThreadPreemptionChangeEvent.fn_name in str(lines[i + 2][2])
        tid2 = ThreadIdEvent.fn_name in str(lines[i + 3][2])
        preempt2 = ThreadPreemptionChangeEvent.fn_name in str(lines[i + 4][2])
        semput = SemPutEvent.fn_name in str(lines[i + 5][2]) and 'txBufferLock' in str(lines[i + 5][2])
        if semget and tid1 and preempt1 and tid2 and preempt2 and semput:
            return 'green', i, i + 5
        return None

    @staticmethod
    def rx_transfer(lines, i) -> meta_match_type:
        semget = SemGetEvent.fn_name in str(lines[i + 0][2]) and 'rxTransferLock' in str(lines[i + 0][2])
        if not semget:
            return None
        for offset in range(len(lines) - i):
            semput = SemPutEvent.fn_name in str(lines[i + offset][2]) and 'rxTransferLock' in str(lines[i + offset][2])
            if semput:
                return 'yellow', i, i + offset
        return None

    @staticmethod
    def mutex_locks(lines, i) -> meta_match_type:
        # we can always assume that mutexes are used for locking
        mtxget = MtxGetEvent.fn_name in str(lines[i + 0][2])
        if not mtxget:
            return None
        mtxName = lines[i + 0][2][2].split(CommonArgsMap.obj_id, maxsplit=1)[1].split(',', maxsplit=1)[0]
        for offset in range(len(lines) - i):
            mtxPut = MtxPutEvent.fn_name in str(lines[i + offset][2]) and mtxName in str(lines[i + offset][2])
            if mtxPut:
                return 'purple', i, i + offset
        return None

    @staticmethod
    def rx_completed(lines, i) -> meta_match_type:
        semput = SemPutEvent.fn_name in str(lines[i + 0][2]) and 'blockingRxCompleted' in str(lines[i + 0][2])
        if not semput:
            return None
        for offset in range(len(lines) - i):
            semget = SemGetEvent.fn_name in str(lines[i + offset][2]) and 'blockingRxCompleted' in str(lines[i + offset][2])
            if semget:
                return 'red', i, i + offset
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
        meta_color, meta_start, meta_end = meta_tuple
        meta_color = Color(meta_color)  # Convert to Color class
        # toggle the hue back and forth to split up meta sections that are right next to each other
        hue_offset = -0.03 if meta_index % 2 == 0 else 0.03
        bg_color = Color(hsl=(meta_color.hue + hue_offset,
                              meta_color.saturation,
                              meta_color.luminance)).hex_l
        for i in range(meta_start, meta_end + 1):
            meta_dict = {
                'value': meta_index,
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
    for input_filepath in args.input_csvs:
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
