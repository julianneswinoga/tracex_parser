from typing import *


class CommonArgsMap:
    obj_id = 'obj_id'
    stack_ptr = 'stack_ptr'
    thread_ptr = 'thread_ptr'
    queue_ptr = 'queue_ptr'
    timeout = 'timeout'


class TraceXEvent:
    """
    Base class for TraceX events. It can be instantiated directly but
    the function and argument names will not be meaningful.
    """
    fn_name: Optional[str] = None
    # Underscore in the arg map means don't print it, by default print all args
    arg_map: List[str] = ['arg1', 'arg2', 'arg3', 'arg4']

    def __init__(self, thread_ptr: int, thread_priority: int, event_id: int, timestamp: int, fn_args: List[int]):
        self.thread_ptr = thread_ptr
        self.thread_priority = thread_priority
        self.id = event_id
        self.timestamp = timestamp
        self.raw_args: List[int] = fn_args

        self.thread_name: Optional[str] = None
        self.mapped_args: Dict = self._generate_arg_dict(self.arg_map)

    def __repr__(self):
        thread_str = self.thread_name if self.thread_name is not None else self.thread_ptr
        fn_str = self.fn_name if self.fn_name is not None else f'<TX ID#{self.id}>'
        arg_strs = []
        for arg_name, arg_val in zip(self.arg_map, self.raw_args):
            if not arg_name.startswith('_'):
                # Don't print arg names that start with an underscore
                arg_strs.append(f'{arg_name}={hex(arg_val)}')
        arg_str = ','.join(arg_strs)
        return f'{self.timestamp}:{thread_str} {fn_str}({arg_str})'

    def _generate_arg_dict(self, arg_names: List[str]) -> Dict[str, Any]:
        if len(self.arg_map) != 4:
            raise Exception(f'{self.__class__.__name__} arg map must have exactly 4 entries: {self.arg_map}')
        return {k: v for k, v in zip(arg_names, self.raw_args)}

    def _decode_registry_obj_name(self, raw_obj_name) -> Optional[str]:
        try:
            return raw_obj_name.decode('ASCII')
        except UnicodeDecodeError:
            print(f'{self.__class__.__name__}: Could not decode {raw_obj_name} into ascii')
            return None

    def apply_object_registry(self, object_registry: List):
        # This can be done for all objects

        if CommonArgsMap.obj_id in self.mapped_args:
            # Try to find obj_id in the registry
            for obj in object_registry:
                if self.mapped_args[CommonArgsMap.obj_id] == obj['thread_reg_entry_obj_pointer']:
                    decoded_name = self._decode_registry_obj_name(obj['thread_reg_entry_obj_name'])
                    if decoded_name is not None:
                        self.mapped_args[CommonArgsMap.obj_id] = decoded_name
                    break

        # Make the thread names nicer
        if self.thread_ptr == 0xFFFFFFFF:
            self.thread_name = 'INTERRUPT'
        else:
            # Try to find thread_ptr in the registry
            for obj in object_registry:
                if self.thread_ptr == obj['thread_reg_entry_obj_pointer']:
                    decoded_name = self._decode_registry_obj_name(obj['thread_reg_entry_obj_name'])
                    if decoded_name is not None:
                        self.thread_name = decoded_name
                    break


"""
see tx_trace.h for all these mappings
"""


class ThreadResumeEvent(TraceXEvent):
    fn_name = 'threadResume'
    arg_map = [CommonArgsMap.thread_ptr, 'previous_state', CommonArgsMap.stack_ptr, 'next_thread']


class ISREnterEvent(TraceXEvent):
    fn_name = 'isrEnter'
    arg_map = [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']


class ISRExitEvent(TraceXEvent):
    fn_name = 'isrExit'
    arg_map = [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']


class TimeSliceEvent(TraceXEvent):
    fn_name = 'timeSlice'
    arg_map = ['nxt_thread', 'sys_state', 'preempt_disable', CommonArgsMap.stack_ptr]


class RunningEvent(TraceXEvent):
    fn_name = 'running'
    arg_map = ['_1', '_2', '_3', '_4']  # No args that we care about


class MtxGetEvent(TraceXEvent):
    fn_name = 'mtxGet'
    arg_map = [CommonArgsMap.obj_id, CommonArgsMap.timeout, '_3', '_4']


class MtxPutEvent(TraceXEvent):
    fn_name = 'mtxPut'
    arg_map = [CommonArgsMap.obj_id, 'owning_thread', 'own_cnt', CommonArgsMap.stack_ptr]


class QueueReceiveEvent(TraceXEvent):
    fn_name = 'queueReceive'
    arg_map = [CommonArgsMap.queue_ptr, 'dst_ptr', CommonArgsMap.timeout, 'enqueued']


class QueueSendEvent(TraceXEvent):
    fn_name = 'queueSend'
    arg_map = [CommonArgsMap.queue_ptr, 'src_ptr', CommonArgsMap.timeout, 'enqueued']


class SemPutEvent(TraceXEvent):
    fn_name = 'semPut'
    arg_map = [CommonArgsMap.obj_id, 'cur_cnt', 'suspend_cnt', 'ceiling']


class SemGetEvent(TraceXEvent):
    fn_name = 'semGet'
    arg_map = [CommonArgsMap.obj_id, CommonArgsMap.timeout, 'cur_cnt', CommonArgsMap.stack_ptr]


class ThreadIdEvent(TraceXEvent):
    fn_name = 'threadIdentify'
    arg_map = ['_1', '_2', '_3', '_4']  # No args that we care about


class ThreadPreemptionChangeEvent(TraceXEvent):
    fn_name = 'preemptionChange'
    arg_map = ['next_ctx', 'new_thresh', 'old_thresh', 'thread_state']


class TimeGetEvent(TraceXEvent):
    fn_name = 'getTicks'
    arg_map = ['cur_ticks', 'next_ctx', '_3', '_4']


def convert_event(raw_event, custom_events_map: Optional[Dict] = None) -> TraceXEvent:
    id_map = {
        1: ThreadResumeEvent,
        3: ISREnterEvent,
        4: ISRExitEvent,
        5: TimeSliceEvent,
        6: RunningEvent,
        52: MtxGetEvent,
        57: MtxPutEvent,
        68: QueueReceiveEvent,
        69: QueueSendEvent,
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
    if custom_events_map and event_id in custom_events_map:
        # Check custom events first
        return custom_events_map[event_id](*args)
    elif event_id in id_map:
        return id_map[event_id](*args)
    else:
        # We don't have a lookup, create a base event
        return TraceXEvent(*args)


def convert_events(raw_events: List, object_registry: List, custom_events_map: Optional[Dict[int, TraceXEvent]] = None) -> List[TraceXEvent]:
    x_events = []
    for raw_event in raw_events:
        x_event = convert_event(raw_event, custom_events_map)
        x_event.apply_object_registry(object_registry)
        x_events.append(x_event)
    return x_events
