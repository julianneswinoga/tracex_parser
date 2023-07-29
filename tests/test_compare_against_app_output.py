from parse_app_output import parse_app_txt_output

from tracex_parser.file_parser import parse_tracex_buffer


def test_against_app_output():
    demo_to_txt_output = {
        'demo_threadx.trx': 'tests/demo_threadx.txt',
    }

    for trx_filename, txt_filename in demo_to_txt_output.items():
        events, obj_map = parse_tracex_buffer(f'./{trx_filename}')
        app_output_data = parse_app_txt_output(txt_filename)
        for app_event, parsed_event in zip(app_output_data.event_list, events):
            assert app_event.time_stamp == parsed_event.timestamp
