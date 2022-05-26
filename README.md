# TraceX Parser
This python package parses ThreadX trace buffers into both human and machine-readable formats.
More documentation about ThreadX trace buffers can be found [here](https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter5).

## Install
`pip3 install tracex-parser`

## Example trace buffers
In the repository source there are a couple example TraceX traces which can be used to verify that things are working correctly.
### As a python module
```pycon
>>> from tracex_parser.file_parser import parse_tracex_buffer
>>> events, obj_map = parse_tracex_buffer('./demo_threadx.trx')
>>> events
[4265846278:thread 7 threadResume(thread_ptr=thread 6,prev_state=0xd,stack_ptr=0x12980,next_thread=), 4265846441:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x1,stack_ptr=0x129a0), 4265846566:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x2,stack_ptr=0x129a0)]
>>> obj_map[0xeea4]
{'obj_reg_entry_obj_available **': '0x0', 'obj_reg_entry_obj_type **': '0x1', 'thread_reg_entry_obj_ptr': '0xeea4', 'obj_reg_entry_obj_parameter_1': '0xef4c', 'obj_reg_entry_obj_parameter_2': '0x3fc', 'thread_reg_entry_obj_name': b'System Timer Thread'}
```

### As a command line utility
The `file_parser` module can also be run as a script, which will provide simple statistics on the trace as well as dumping all the events in the trace:
```console
$ python3 -m tracex_parser.file_parser -vvv ./demo_threadx.trx
Parsing ./demo_threadx.trx
total events: 974
object registry size: 16
delta ticks: 156206
Event Histogram:
queueSend           493
queueReceive        428
threadResume        19
threadSuspend       16
mtxPut              4
isrExit             3
isrEnter            3
semGet              2
semPut              2
threadSleep         2
mtxGet              2
All events:
4265846278:thread 7 threadResume(thread_ptr=thread 6,prev_state=0xd,stack_ptr=0x12980,next_thread=)
4265846441:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x1,stack_ptr=0x129a0)
4265846566:thread 7 mtxPut(obj_id=mutex 0,owning_thread=0x6adc,own_cnt=0x2,stack_ptr=0x129a0)
4265846825:thread 4 threadSuspend(thread_ptr=thread 4,new_state=0x6,stack_ptr=0x11d70,next_thread=thread 7)
4265846953:thread 4 semGet(obj_id=semaphore 0,timeout=WaitForever,cur_cnt=0x0,stack_ptr=0x11d98)
...
```

## Details
The main interface to this module is through the `parse_tracex_buffer()` function in the `file_parser` module.

### Custom User Event Parsing
This module also allows you to specify the format of user events such that they can automatically be parsed from their raw form.

#### Create the event with `events.tracex_event_factory()`
Arguments:
- `class_name`: A unique name to represent the event (internally it is the name of the returned class)
- `fn_name`: A nice name that will be shown in the trace output
- `arg_map`: A list of exactly 4 argument names to apply to the event.
  - Names prefixed with an underscore (`_`) will not be shown by default
  - See [events.CommonArg](#events.CommonArg) for special handling of arguments
- `class_name_is_fn_name`: If `True` you do not have to specify a `fn_name` and the `class_name` will be used instead

##### `events.CommonArg`
Some attributes under this class have special meaning to the parsing logic:
- `events.CommonArg.timeout`: Will replace the raw number with:
  - `0`&#8594;`'NoWait`
  - `0xFFFFFFFF`&#8594;`'WaitForever`
- `events.CommonArg.obj_id`: Will look in the object registry for an object with the same memory address and replace the raw number with that object's name
- `events.CommonArg.thread_ptr`: Same as `events.CommonArg.obj_id`, but for thread names
- `events.CommonArg.next_thread`: Same as `events.CommonArg.thread_ptr`

#### Use custom events with `parse_tracex_buffer()`
Once the custom event is created with `events.tracex_event_factory()` you need to assign it to an event id.
This is done by creating a dictionary with the key corresponding to the event id and the value being the custom event.
Then that dictionary is passed to the `custom_events_map` parameter of `parse_tracex_buffer()`

#### Example
In this example we are going to parse event #5000, which I have compiled into my TraceX application using `tx_trace_user_event_insert()`.
I've passed following arguments to event #5000:
1. Line number
2. Address of a semaphore object
3. File descriptor number
4. Always 0

In the C code it looks like the following:
```C
tx_trace_user_event_insert(5000, __LINE__, (TX_SEMAPHORE *) semPtr, fd, 0);
```
Now parsing it with the `tracex_parser` module:
```python
from tracex_parser.file_parser import parse_tracex_buffer
from tracex_parser.events import tracex_event_factory, CommonArg

customEvent = tracex_event_factory('SomeCustomEvent', 'custEvent', ['line_num', CommonArg.obj_id, 'fd', '_4'])
custom_events = {
    5000: customEvent,
}
events, obj_map = parse_tracex_buffer('./demo_threadx.trx', custom_events_map=custom_events)
```

The parsed event is now shown as:
```
7821:myThread custEvent(line_num=1234,obj_id=fdSem,fd=5)
```

Without the custom event it would be shown as:
```
7821:myThread <TX ID#5000>(arg1=0x4d2,arg2=0x82070000,arg3=0x5,arg4=0x0)
```
