# TraceX Parser
[![Documentation Status](https://readthedocs.org/projects/tracex_parser/badge/?version=latest)](https://tracex_parser.readthedocs.io/en/latest/?badge=latest)
[![CircleCI](https://circleci.com/gh/julianneswinoga/tracex_parser.svg?style=shield)](https://circleci.com/gh/julianneswinoga/tracex_parser)
[![Coverage Status](https://coveralls.io/repos/github/julianneswinoga/tracex_parser/badge.svg?branch=master)](https://coveralls.io/github/julianneswinoga/tracex_parser?branch=master)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/tracex_parser)](https://pypi.org/project/tracex_parser/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/tracex_parser)

This python package parses ThreadX trace buffers into both human and machine-readable formats.
Don't know where to begin? Check out the [quick-start](https://tracex-parser.readthedocs.io/en/latest/quickstart.html) documentation.
More documentation about ThreadX trace buffers can be found [here](https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter5).

## Install
### Via `pip`
```console
$ python3 -m pip install tracex-parser
```

### Via `snap`
> [!NOTE]
> This installation method only allows you to use the command line file parser, not the Python library

```console
$ sudo snap install tracex-parser
$ sudo snap alias tracex-parser.parse-trx parse-trx  # Register the `parse-trx` command, otherwise you will need to use tracex-parser.parse-trx
$ sudo snap connect tracex-parser:removable-media  # Required to allow reading of files outside of /home
```

> [!NOTE]
> Due to how snap packages work, there are restrictions on which files snaps are allowed to access.
> Currently only `/home`, `/media`, `/run/media`, `/mnt` are able to be read.
> For example attempting to read a file in `/tmp` will throw a `No such file or directory` error


## Example trace buffers
In the repository source there are a couple example TraceX traces which can be used to verify that things are working correctly.
### As a python module
[documentation](https://tracex-parser.readthedocs.io/en/latest/py-interface.html)
```pycon
>>> from tracex_parser.file_parser import parse_tracex_buffer
>>> events, obj_map = parse_tracex_buffer('./demo_threadx.trx')
>>> events
[4265846278:thread 7 threadResume(thread_ptr=thread 6,prev_state=0xd,stack_ptr=0x12980,next_thread=), 4265846441:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x1,stack_ptr=0x129a0), 4265846566:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x2,stack_ptr=0x129a0)]
>>> obj_map[0xeea4]
{'obj_reg_entry_obj_available **': '0x0', 'obj_reg_entry_obj_type **': '0x1', 'thread_reg_entry_obj_ptr': '0xeea4', 'obj_reg_entry_obj_parameter_1': '0xef4c', 'obj_reg_entry_obj_parameter_2': '0x3fc', 'thread_reg_entry_obj_name': b'System Timer Thread'}
```

### As a command line utility
[documentation](https://tracex-parser.readthedocs.io/en/latest/cli-interface.html)
The `file_parser` module can also be run as a script, which will provide simple statistics on the trace as well as dumping all the events in the trace.
It can be run by either:
- Running the module manually: `python3 -m tracex_parser.file_parser`
- Using the newly installed command: `parse-trx`

Both run methods are identical.
```console
$ parse-trx -vvv ./demo_threadx.trx
Parsing ./demo_threadx.trx
total events: 974
object registry size: 16
delta ticks: 40402
Event Histogram:
queueSend     493
queueReceive  428
threadResume  19
threadSuspend 16
mtxPut        4
isrEnter      3
isrExit       3
semPut        2
semGet        2
mtxGet        2
threadSleep   2
All events:
2100:thread 2 queueReceive(queue_ptr=0x6b84,dst_ptr=0x115a0,timeout=WaitForever,enqueued=0x13)
1939:thread 2 queueReceive(queue_ptr=0x6b84,dst_ptr=0x115a0,timeout=WaitForever,enqueued=0x12)
1778:thread 2 queueReceive(queue_ptr=0x6b84,dst_ptr=0x115a0,timeout=WaitForever,enqueued=0x11)
1617:thread 2 queueReceive(queue_ptr=0x6b84,dst_ptr=0x115a0,timeout=WaitForever,enqueued=0x10)
1456:thread 2 queueReceive(queue_ptr=0x6b84,dst_ptr=0x115a0,timeout=WaitForever,enqueued=0xf)
...
