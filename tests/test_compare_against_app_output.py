import pytest
from typing import Tuple

from parse_app_output import parse_app_txt_output

from tracex_parser.file_parser import parse_tracex_buffer

filename_tups = [
    ('demo_threadx.trx', 'tests/demo_threadx.txt'),
]


@pytest.mark.parametrize('filename_tup', filename_tups)
def test_against_app_output(filename_tup: Tuple[str, str]):
    trx_filename, txt_filename = filename_tup

    events, obj_map = parse_tracex_buffer(f'./{trx_filename}')
    app_output_data = parse_app_txt_output(txt_filename)
    assert len(app_output_data.event_list) == len(events)
    for app_event, parsed_event in zip(app_output_data.event_list, events):
        assert app_event.time_stamp == parsed_event.timestamp
        assert app_event.event_type == parsed_event.id
        assert app_event.cur_context_ptr == parsed_event.thread_ptr
        # Txt output sometimes doesn't have the full name? "System Timer Thr"
        assert app_event.cur_context_name in parsed_event.thread_name
        assert app_event.event_infos == parsed_event.raw_args
        assert app_event.priority == parsed_event.thread_priority
