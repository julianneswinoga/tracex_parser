import pytest
from typing import NamedTuple, Tuple

from tracex_parser.file_parser import parse_tracex_buffer


class TrxDemoStats(NamedTuple):
    total_events: int
    total_ticks: int
    obj_registry_size: int
    num_unique_events: int


filename_stat_tups = [
    ('demo_filex.trx', TrxDemoStats(950, 949000, 7, 25)),
    ('demo_netx_tcp.trx', TrxDemoStats(950, 949000, 19, 36)),
    ('demo_netx_udp.trx', TrxDemoStats(950, 949000, 17, 23)),
    ('demo_threadx.trx', TrxDemoStats(974, 40402, 16, 11)),
]


@pytest.mark.parametrize('filename_stat_tup', filename_stat_tups)
def test_demo_trx_files(filename_stat_tup: Tuple[str, TrxDemoStats]):
    trx_filename, tested_stats = filename_stat_tup

    events, obj_map = parse_tracex_buffer(f'./{trx_filename}')

    assert len(events) == tested_stats.total_events

    total_ticks = events[-1].timestamp - events[0].timestamp
    assert total_ticks == tested_stats.total_ticks

    obj_reg_size = len(obj_map.keys())
    assert obj_reg_size == tested_stats.obj_registry_size

    unique_events = set(e.id for e in events)
    assert len(unique_events) == tested_stats.num_unique_events
