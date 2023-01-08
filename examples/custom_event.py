#!/usr/bin/python3
from tracex_parser.file_parser import parse_tracex_buffer
from tracex_parser.events import tracex_event_factory, CommonArg

customEvent = tracex_event_factory('SomeCustomEvent', 'custEvent', ['line_num', CommonArg.obj_id, 'fd', '_4'])
custom_events = {
    5000: customEvent,
}
events, obj_map = parse_tracex_buffer('./my_tracex_dump.trx', custom_events_map=custom_events)
