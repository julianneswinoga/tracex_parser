#!/usr/bin/python3

import argparse
from typing import *

import xlsxwriter
from colorhash import ColorHash
from colour import Color

from parser import parse_tracex_buffer
from events import CommonArgsMap, SemGetEvent, SemPutEvent

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


# see tx_trace.h
class EventRemaps:
    @staticmethod
    def _extra_args(**kwargs) -> str:
        return ' <' + ','.join([f'{n}={hex(a)}' for n, a in kwargs.items()]) + '>'

    @staticmethod
    def isrEnter(fn_name, arg_list) -> remap_rtn_type:
        stack_ptr, isr_num, sys_state, preempt_dis = arg_list
        isr_format = {'font_color': ColorHash(isr_num).hex}
        extra_args = EventRemaps._extra_args(stack_ptr=stack_ptr, sys_state=sys_state, preempt_dis=preempt_dis)
        return ['isrEnter(', isr_format, f'{isr_num})', extra_args]

    @staticmethod
    def isrExit(fn_name, arg_list) -> remap_rtn_type:
        stack_ptr, isr_num, sys_state, preempt_dis = arg_list
        isr_format = {'font_color': ColorHash(isr_num).hex}
        extra_args = EventRemaps._extra_args(stack_ptr=stack_ptr, sys_state=sys_state, preempt_dis=preempt_dis)
        return ['isrExit(', isr_format, f'{isr_num})', extra_args]

    @staticmethod
    def semGet(fn_name, arg_list) -> remap_rtn_type:
        sem_id, timeout, cur_cnt, stack_ptr = arg_list
        if sem_id in sem_ptr_map:
            sem_id = sem_ptr_map[sem_id]
        sem_format = {'font_color': ColorHash(sem_id).hex}
        if timeout in timeout_map:
            timeout = timeout_map[timeout]
        extra_args = EventRemaps._extra_args(cur_cnt=cur_cnt, stack_ptr=stack_ptr)
        return ['semGet(', sem_format, f'{sem_id}', f', {timeout})', extra_args]

    @staticmethod
    def semPut(fn_name, arg_list) -> remap_rtn_type:
        sem_id, cur_cnt, suspend_cnt, ceiling = arg_list
        if sem_id in sem_ptr_map:
            sem_id = sem_ptr_map[sem_id]
        sem_format = {'font_color': ColorHash(sem_id).hex}

        extra_args = EventRemaps._extra_args(cur_cnt=cur_cnt, suspend_cnt=suspend_cnt)
        if ceiling == 1:
            return ['semBPut(', sem_format, f'{sem_id}', f')', extra_args]
        else:
            return ['semCeilingPut(', sem_format, f'{sem_id}', f', {ceiling})', extra_args]

    @staticmethod
    def mtxGet(fn_name, arg_list) -> remap_rtn_type:
        mtx_id, timeout, arg3, arg4 = arg_list
        if mtx_id in mtx_ptr_map:
            mtx_id = mtx_ptr_map[mtx_id]
        else:
            mtx_id = hex(mtx_id)
        mtx_format = {'font_color': ColorHash(mtx_id).hex}
        if timeout in timeout_map:
            timeout = timeout_map[timeout]
        extra_args = EventRemaps._extra_args(arg3=arg3, arg4=arg4)
        return ['mtxGet(', mtx_format, f'{mtx_id}', f', {timeout})', extra_args]

    @staticmethod
    def mtxPut(fn_name, arg_list) -> remap_rtn_type:
        mtx_id, owning_thread, ownCnt, stack_ptr = arg_list
        if mtx_id in mtx_ptr_map:
            mtx_id = mtx_ptr_map[mtx_id]
        else:
            mtx_id = hex(mtx_id)
        mtx_format = {'font_color': ColorHash(mtx_id).hex}

        return ['mtxPut(', mtx_format, f'{mtx_id}', f', owning_thread={owning_thread} have={ownCnt})']

    @staticmethod
    def threadIdentify(fn_name, arg_list) -> remap_rtn_type:
        # No args
        return ['threadIdentify()']

    @staticmethod
    def threadPreemptionChange(fn_name, arg_list) -> remap_rtn_type:
        next_ctx, new_thresh, old_thresh, thread_state = arg_list
        extra_args = EventRemaps._extra_args(next_ctx=next_ctx, thread_state=thread_state)
        return [f'preemptionChange({old_thresh} -> {new_thresh})', extra_args]

    @staticmethod
    def timeSlice(fn_name, arg_list) -> remap_rtn_type:
        nxt_thread, sys_state, preempt_disable, stack = arg_list
        extra_args = EventRemaps._extra_args(nxt_thread=nxt_thread, sys_state=sys_state, preempt_disable=preempt_disable, stack=stack)
        return ['timeSlice()', extra_args]

    @staticmethod
    def timeGet(fn_name, arg_list) -> remap_rtn_type:
        cur_ticks, next_ctx, arg3, arg4 = arg_list
        return [f'tick() -> {cur_ticks}ticks']

    @staticmethod
    def uartOpen(fn_name, arg_list) -> remap_rtn_type:
        line_number, arg2, arg3, arg4 = arg_list
        return [{'bold': True}, f'uartOpen()']

    @staticmethod
    def uartClose(fn_name, arg_list) -> remap_rtn_type:
        line_number, fd, arg3, arg4 = arg_list
        fd_format = {'font_color': ColorHash(fd).hex}
        return [{'bold': True}, 'uartClose(', fd_format, f'fd={fd})']

    @staticmethod
    def uartRead(fn_name, arg_list) -> remap_rtn_type:
        fd, count, vmin, vtime = arg_list
        fd_format = {'font_color': ColorHash(fd).hex}
        return [{'bold': True}, 'uartRead(', fd_format, f'fd={fd},', f'count={count},', f'vmin={vmin},',
                f'vtime={vtime})']

    @staticmethod
    def uartReadBufferBlockingPl(fn_name, arg_list) -> remap_rtn_type:
        xferlen, timeout, arg3, arg4 = arg_list
        if timeout in timeout_map:
            timeout = timeout_map[timeout]
        return [{'bold': True}, 'uartReadBufferBlockingPl(', f'xferlen={xferlen},', f'timeout={timeout})']

    @staticmethod
    def uartWaitForReceiveToCompleteWithBuffer(fn_name, arg_list) -> remap_rtn_type:
        bytesReq, timeout, arg3, arg4 = arg_list
        if timeout in timeout_map:
            timeout = timeout_map[timeout]
        return [{'bold': True}, 'uartWaitForReceiveToCompleteWithBuffer(', f'bytesReq={bytesReq},',
                f'timeout={timeout})']

    @staticmethod
    def uartWaitForReceiveToCompleteWithBufferReturnEarly(fn_name, arg_list) -> remap_rtn_type:
        return [{'bold': True}, f'uartWaitForReceiveToCompleteWithBufferReturnEarly()']

    @staticmethod
    def uartWaitForReceiveToCompleteWithBufferReturnLate(fn_name, arg_list) -> remap_rtn_type:
        return [{'bold': True}, f'uartWaitForReceiveToCompleteWithBufferReturnLate()']

    @staticmethod
    def uartReadMinimumBytesBlocking(fn_name, arg_list) -> remap_rtn_type:
        xferlen, vmin, vtime, arg4 = arg_list
        if vtime in timeout_map:
            vtime = timeout_map[vtime]
        return [{'bold': True}, 'uartReadMinimumBytesBlocking(', f'xferlen={xferlen},', f'vmin={vmin},',
                f'vtime={vtime})']

    @staticmethod
    def uartISRError(fn_name, arg_list) -> remap_rtn_type:
        notifyLevel, cond1, cond2, arg4 = arg_list
        return [{'bold': True}, 'uartISRError(', f'notifyLevel={notifyLevel},', f'bufferLargerThanNotifyLevel={cond1},',
                f'userRxPtrsNotNull={cond2})']

    @staticmethod
    def uartSetRxFifoTriggerLevelPl(fn_name, arg_list) -> remap_rtn_type:
        triglevel, arg2, arg3, arg4 = arg_list
        return [{'bold': True}, 'uartSetRxFifoTriggerLevelPl(', f'triglevel={triglevel})']


type_to_fn_map: Dict[int, Callable[[str, List], remap_rtn_type]] = {
    3: EventRemaps.isrEnter,
    4: EventRemaps.isrExit,
    5: EventRemaps.timeSlice,
    52: EventRemaps.mtxGet,
    57: EventRemaps.mtxPut,
    80: EventRemaps.semPut,
    83: EventRemaps.semGet,
    103: EventRemaps.threadIdentify,
    107: EventRemaps.threadPreemptionChange,
    120: EventRemaps.timeGet,
    5000: EventRemaps.uartOpen,
    5001: EventRemaps.uartClose,
    5002: EventRemaps.uartRead,
    5003: EventRemaps.uartReadBufferBlockingPl,
    5004: EventRemaps.uartWaitForReceiveToCompleteWithBuffer,
    5005: EventRemaps.uartWaitForReceiveToCompleteWithBufferReturnEarly,
    5006: EventRemaps.uartWaitForReceiveToCompleteWithBufferReturnLate,
    5007: EventRemaps.uartReadMinimumBytesBlocking,
    5008: EventRemaps.uartISRError,
    5009: EventRemaps.uartSetRxFifoTriggerLevelPl,
}


# time, actor, event
rich_event_cell = List[Union[str, remap_rtn_type]]
converted_row_type = List[Union[int, str, Union[str, rich_event_cell]]]
meta_row_type = List[Union[int, str, Union[str, rich_event_cell], Dict]]


def convert_file(filepath: str) -> List[converted_row_type]:
    events = parse_tracex_buffer(filepath)

    out_lines = [['time', 'actor', 'event']]  # header
    for event in events:
        thread_str = event.thread_name if event.thread_name is not None else event.thread_ptr
        thread_format = {'font_color': ColorHash(thread_str).hex}

        fn_str = event.function_name if event.function_name is not None else event.id
        if isinstance(event.args, list):
            # No processing was done
            arg_list = [', '.join(f'{num}={hex(arg)}' for num, arg in enumerate(event.args))]
        else:
            arg_list = []
            for arg_name, arg_val in event.mapped_args.items():
                if arg_name == CommonArgsMap.obj_id and arg_val in sem_ptr_map:
                    arg_val = sem_ptr_map[arg_val]

                if arg_name in [CommonArgsMap.obj_id]:
                    arg_format = {'font_color': ColorHash(arg_name).hex}
                    arg_list.append(arg_format)
                arg_list.append(f'{arg_name}={arg_val},')

        event_str = [f'{fn_str}('] + arg_list + [')']
        out_lines.append([event.timestamp, [thread_format, thread_str], event_str])
    return out_lines


meta_match_type = Optional[Tuple[str, int, int]]


class MetaMatches:
    @staticmethod
    def critical_section(lines, i) -> meta_match_type:
        if i + 5 > len(lines) - 1:
            return None
        semget = SemGetEvent.function_name in str(lines[i + 0][2]) and 'txBufferLock' in str(lines[i + 0][2])
        tid1 = 'threadIdentify' in str(lines[i + 1][2])
        preempt1 = 'preemptionChange' in str(lines[i + 2][2])
        tid2 = 'threadIdentify' in str(lines[i + 3][2])
        preempt2 = 'preemptionChange' in str(lines[i + 4][2])
        semput = SemPutEvent.function_name in str(lines[i + 5][2]) and 'txBufferLock' in str(lines[i + 5][2])
        if semget and tid1 and preempt1 and tid2 and preempt2 and semput:
            return 'green', i, i + 5
        return None

    @staticmethod
    def rx_transfer(lines, i) -> meta_match_type:
        semget = SemGetEvent.function_name in str(lines[i + 0][2]) and 'rxTransferLock' in str(lines[i + 0][2])
        if not semget:
            return None
        for offset in range(len(lines) - i):
            semput = SemPutEvent.function_name in str(lines[i + offset][2]) and 'rxTransferLock' in str(lines[i + offset][2])
            if semput:
                return 'yellow', i, i + offset
        return None

    @staticmethod
    def mutex_locks(lines, i) -> meta_match_type:
        # we can always assume that mutexes are used for locking
        mtxget = 'mtxGet' in str(lines[i + 0][2])
        if not mtxget:
            return None
        mtxName = lines[i + 0][2][2]  # First parameter of the function
        for offset in range(len(lines) - i):
            mtxPut = 'mtxPut' in str(lines[i + offset][2]) and mtxName in str(lines[i + offset][2])
            if mtxPut:
                return 'purple', i, i + offset
        return None

    @staticmethod
    def rx_completed(lines, i) -> meta_match_type:
        semput = SemPutEvent.function_name in str(lines[i + 0][2]) and 'blockingRxCompleted' in str(lines[i + 0][2])
        if not semput:
            return None
        for offset in range(len(lines) - i):
            semget = SemGetEvent.function_name in str(lines[i + offset][2]) and 'blockingRxCompleted' in str(lines[i + offset][2])
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
