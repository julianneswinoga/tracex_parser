from typing import *


class CommonArgsMap:
    obj_id = 'obj_id'
    stack_ptr = 'stack_ptr'
    thread_ptr = 'thread_ptr'
    timeout = 'timeout'


class TraceXEvent:
    fn_name: Optional[str] = None
    arg_map: Optional[List] = None

    def __init__(self, thread_ptr: int, thread_priority: int, event_id: int, timestamp: int, fn_args: List[int]):
        self.thread_ptr = thread_ptr
        self.thread_priority = thread_priority
        self.id = event_id
        self.timestamp = timestamp
        self.args: Union[List, str] = fn_args

        self.thread_name: Optional[str] = None
        self.function_name: Optional[str] = None
        self.mapped_args: Optional[Dict] = None

    def __repr__(self):
        thread_str = self.thread_name if self.thread_name is not None else self.thread_ptr
        fn_str = self.function_name if self.function_name is not None else self.id
        if isinstance(self.args, list):
            # No processing was done
            if self.arg_map is None:
                arg_str = ','.join(f'{arg_num}={hex(arg_val)}' for arg_num, arg_val in enumerate(self.args))
            else:
                arg_str = ','.join(f'{arg_name}={hex(arg_val)}' for arg_name, arg_val in zip(self.arg_map, self.args))
        else:
            arg_str = self.args
        return f'{self.timestamp}:{thread_str} {fn_str}({arg_str})'

    def _generate_arg_dict(self, arg_names: List[str]) -> Dict[str, Any]:
        return {k: v for k, v in zip(arg_names, self.args)}

    def apply_object_registry(self, object_registry: List):
        # This can be done for all objects
        self.function_name = self.fn_name
        if self.arg_map:
            self.mapped_args = self._generate_arg_dict(self.arg_map)

        if self.thread_ptr == 0xFFFFFFFF:
            self.thread_name = 'INTERRUPT'
        else:
            for obj in object_registry:
                if self.thread_ptr == obj['thread_registry_entry_object_pointer']:
                    self.thread_name = obj['thread_registry_entry_object_name'].decode('ASCII')


"""
see tx_trace.h for all these mappings
"""


class SemPutEvent(TraceXEvent):
    fn_name = 'semPut'
    arg_map = [CommonArgsMap.obj_id, 'timeout', 'cur_cnt', 'stack_ptr']

    def apply_object_registry(self, object_registry: List):
        super().apply_object_registry(object_registry)
        self.args = f"sem_id={hex(self.mapped_args[CommonArgsMap.obj_id])}, stack_ptr={hex(self.mapped_args['stack_ptr'])}"


class SemGetEvent(TraceXEvent):
    fn_name = 'semGet'
    arg_map = [CommonArgsMap.obj_id, 'cur_cnt', 'suspend_cnt', 'ceiling']

    def apply_object_registry(self, object_registry: List):
        super().apply_object_registry(object_registry)
        self.args = f"sem_id={hex(self.mapped_args[CommonArgsMap.obj_id])}, cur_cnt={hex(self.mapped_args['cur_cnt'])}"


class ISREnterEvent(TraceXEvent):
    fn_name = 'isrEnter'
    arg_map = [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']


class ISRExitEvent(TraceXEvent):
    fn_name = 'isrExit'
    arg_map = [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']


class TimeSliceEvent(TraceXEvent):
    fn_name = 'timeSlice'
    arg_map = ['nxt_thread', 'sys_state', 'preempt_disable', CommonArgsMap.stack_ptr]


class MtxGetEvent(TraceXEvent):
    fn_name = 'mtxGet'
    arg_map = [CommonArgsMap.obj_id, CommonArgsMap.timeout, '_3', '_4']


class MtxPutEvent(TraceXEvent):
    fn_name = 'mtxPut'
    arg_map = [CommonArgsMap.obj_id, 'owning_thread', 'own_cnt', CommonArgsMap.stack_ptr]


class ThreadIdEvent(TraceXEvent):
    fn_name = 'threadIdentify'
    arg_map = ['_1', '_2', '_3', '_4']


class ThreadPreemptionChangeEvent(TraceXEvent):
    fn_name = 'preemptionChange'
    arg_map = ['next_ctx', 'new_thresh', 'old_thresh', 'thread_state']


class TimeGetEvent(TraceXEvent):
    fn_name = 'getTicks'
    arg_map = ['cur_ticks', 'next_ctx', '_3', '_4']


def convert_event(raw_event, custom_events_map) -> TraceXEvent:
    id_map = {
        3: ISREnterEvent,
        4: ISRExitEvent,
        5: TimeSliceEvent,
        52: MtxGetEvent,
        57: MtxPutEvent,
        80: SemPutEvent,
        83: SemGetEvent,
        103: ThreadIdEvent,
        107: ThreadPreemptionChangeEvent,
        120: TimeGetEvent,
    }
    event_id = raw_event['event_id']
    raw_event_args = [raw_event['information_field_1'], raw_event['information_field_2'],
                      raw_event['information_field_3'], raw_event['information_field_4']]
    args = [raw_event['thread_pointer'], raw_event['thread_priority'], event_id,
            raw_event['time_stamp'], raw_event_args]
    if event_id in id_map:
        return id_map[event_id](*args)
    elif event_id in custom_events_map:
        return custom_events_map[event_id](*args)
    else:
        return TraceXEvent(*args)


def convert_events(raw_events: List, object_registry: List, custom_events_map: Dict[int, TraceXEvent]) -> List[TraceXEvent]:
    x_events = []
    for raw_event in raw_events:
        x_event = convert_event(raw_event, custom_events_map)
        x_event.apply_object_registry(object_registry)
        x_events.append(x_event)
    return x_events
