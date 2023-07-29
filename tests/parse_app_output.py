from typing import NamedTuple, List


class AppEvent(NamedTuple):
    event_number: int
    relative_time: int
    event_type: int
    cur_context_name: str
    cur_context_ptr: int
    priority: int
    next_context_name: str
    next_context_ptr: int
    event_infos: List[int]
    time_stamp: int
    priority_inversion: str
    raw_event: int
    raw_priority: int


class AppHeaderInfo(NamedTuple):
    total_threads: int
    total_events: int
    max_rel_ticks: int
    trace_id: int
    timer_mask: int
    obj_name_size: int
    trace_base_addr: int
    obj_start_addr: int
    obj_end_addr: int
    buf_start_addr: int
    buf_end_addr: int
    buf_oldest_addr: int


class AppOutputData(NamedTuple):
    header_info: AppHeaderInfo
    event_list: List[AppEvent]


def parse_header_txt(lines: List[str]) -> AppHeaderInfo:
    numbers_in_order = [line.rsplit(maxsplit=1)[1] for line in lines]
    header_info = AppHeaderInfo(
        total_threads=int(numbers_in_order[0]),
        total_events=int(numbers_in_order[1]),
        max_rel_ticks=int(numbers_in_order[2]),
        trace_id=int(numbers_in_order[3]),
        timer_mask=int(numbers_in_order[4], 16),
        obj_name_size=int(numbers_in_order[5]),
        trace_base_addr=int(numbers_in_order[6], 16),
        obj_start_addr=int(numbers_in_order[7], 16),
        obj_end_addr=int(numbers_in_order[8], 16),
        buf_start_addr=int(numbers_in_order[9], 16),
        buf_end_addr=int(numbers_in_order[10], 16),
        buf_oldest_addr=int(numbers_in_order[11], 16),
    )
    return header_info


def parse_events_txt(lines: List[str]) -> List[AppEvent]:
    event_header_str = lines.pop(0)  # just ignore the header
    event_list = []
    for event_str in lines:
        event_str_split = [e.strip() for e in event_str.split('    ') if e]
        event_str_split = list(filter(lambda s: s != '(', event_str_split))
        if event_str_split[4].lower() == 'interrupt':
            cur_context = ['INTERRUPT', 'FFFFFFFF']
            next_context = ['INTERRUPT', 'FFFFFFFF']
        else:
            cur_context = event_str_split[4].replace('(', '').replace(')', '').rsplit(maxsplit=1)
            next_context = event_str_split[6].replace('(', '').replace(')', '').rsplit(maxsplit=1)
        app_event = AppEvent(
            event_number=int(event_str_split[0]),
            relative_time=int(event_str_split[1]),
            event_type=int(event_str_split[3].strip(')( ')),
            cur_context_name=cur_context[0],
            cur_context_ptr=int(cur_context[1], 16),
            priority=int(event_str_split[5].split(maxsplit=1)[0]),  # Ignore the '?'
            next_context_name=next_context[0],
            next_context_ptr=int(next_context[1], 16),
            event_infos=[int(s.split()[1], 16) for s in event_str_split[7:11]],
            time_stamp=int(event_str_split[11], 16),
            priority_inversion=event_str_split[12],
            raw_event=int(event_str_split[13]),
            raw_priority=int(event_str_split[14], 16),
        )
        event_list.append(app_event)
    return event_list


def parse_app_txt_output(filename: str) -> AppOutputData:
    with open(filename, 'r') as fp:
        txt_lines = fp.readlines()

    section_name_to_key = {
        'tracex version': 'input_output_files',
        'header information': 'header_info',
        'threads in this trace': 'thread_info',
        'objects in trace': 'object_info',
        'performance statistics': 'performance_stats',
        'thread execution': 'thread_execution_info',
        'thread stack': 'thread_stack_info',
        'filex performance': 'filex_info',
        'netx performance': 'netx_info',
        'popular services': 'popular_services',
        'trace events': 'trace_events',
        'trace done': 'trace_done',
    }

    lines_by_section = {}
    cur_section = 'unknown'
    for line in txt_lines:
        line_striped = line.strip()  # Strip whitespace
        if not line_striped or line_striped.isspace():
            pass  # just ignore blank lines
        elif line_striped.startswith('********') and line_striped.endswith('********'):
            section_raw_name = line_striped.strip('* ')
            for section_name, key in section_name_to_key.items():
                if section_name.lower() in section_raw_name.lower():
                    cur_section = key
                    break
            else:
                cur_section = 'unknown'
        else:
            if cur_section in lines_by_section:
                lines_by_section[cur_section].append(line_striped)
            else:
                lines_by_section[cur_section] = [line_striped]
    assert 'unknown' not in lines_by_section

    header_info = parse_header_txt(lines_by_section['header_info'])
    event_list = parse_events_txt(lines_by_section['trace_events'])

    app_output_data = AppOutputData(
        header_info=header_info,
        event_list=event_list,
    )
    return app_output_data
