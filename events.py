from typing import *


class CommonArgsMap:
    """
    This holds string mappings for common arguments so that we can
    reference this mapping in TraceXEvent, instead of a raw string.
    """
    stack_ptr = 'stack_ptr'
    queue_ptr = 'queue_ptr'
    timeout = 'timeout'
    # The following will attempted to be looked up in the object registry and mapped to strings
    obj_id = 'obj_id'
    thread_ptr = 'thread_ptr'
    next_thread = 'next_thread'


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
        self.mapped_args: Dict[str, Union[int, str]] = self._generate_arg_dict(self.arg_map)

    def __repr__(self):
        thread_str = self.thread_name if self.thread_name is not None else self.thread_ptr
        fn_str = self.fn_name if self.fn_name is not None else f'<TX ID#{self.id}>'
        arg_strs = []
        for arg_name, arg_val in self.mapped_args.items():
            if arg_name.startswith('_'):
                # Don't print arg names that start with an underscore
                continue
            if isinstance(arg_val, int):
                # For this printing always convert raw integers to hex
                arg_strs.append(f'{arg_name}={hex(arg_val)}')
            else:
                arg_strs.append(f'{arg_name}={arg_val}')
        arg_str = ','.join(arg_strs)
        return f'{self.timestamp}:{thread_str} {fn_str}({arg_str})'

    def _generate_arg_dict(self, arg_names: List[str]) -> Dict[str, Any]:
        if len(self.arg_map) != 4:
            raise Exception(f'{self.__class__.__name__} arg map must have exactly 4 entries: {self.arg_map}')
        return {k: v for k, v in zip(arg_names, self.raw_args)}

    def _map_ptr_to_obj_reg_name(self, object_registry: List, key_ptr: int) -> Optional[str]:
        for obj in object_registry:
            if key_ptr == obj['thread_reg_entry_obj_pointer']:
                raw_obj_name = obj['thread_reg_entry_obj_name']
                try:
                    return raw_obj_name.decode('ASCII')
                except UnicodeDecodeError:
                    print(f'{self.__class__.__name__}: Could not decode {raw_obj_name} into ascii')
                    return None
        print(f'Cant find {key_ptr} in objreg')
        return None

    def apply_object_registry(self, object_registry: List):
        # This can be done for all objects

        # Change mapped arguments to strings if they can be found in the registry
        args_to_map = [CommonArgsMap.obj_id, CommonArgsMap.thread_ptr, CommonArgsMap.next_thread]
        for arg_to_map in args_to_map:
            if arg_to_map in self.mapped_args.keys():
                obj_reg_name = self._map_ptr_to_obj_reg_name(object_registry, self.mapped_args[arg_to_map])
                if obj_reg_name is not None:
                    self.mapped_args[arg_to_map] = obj_reg_name

        # Make the thread names nicer
        if self.thread_ptr == 0xFFFFFFFF:
            self.thread_name = 'INTERRUPT'
        else:
            # Try to find time slice thread_ptr in the registry
            obj_reg_name = self._map_ptr_to_obj_reg_name(object_registry, self.thread_ptr)
            if obj_reg_name is not None:
                self.thread_name = obj_reg_name

        # Make timeouts nicer
        if CommonArgsMap.timeout in self.mapped_args.keys():
            # Replace if it's in the lookup, no replacement otherwise
            self.mapped_args[CommonArgsMap.timeout] = {
                0: 'NoWait',
                0xFFFFFFFF: 'WaitForever',
            }.get(self.mapped_args[CommonArgsMap.timeout], self.mapped_args[CommonArgsMap.timeout])


def tracex_event_factory(event_name: str, fn_name: str, arg_map: List) -> ClassVar:
    return type(event_name, (TraceXEvent,), {
        'fn_name': fn_name,
        'arg_map': arg_map,
    })


# see tx_trace.h for all these mappings
id_map = {
    1: tracex_event_factory('ThreadResumeEvent', 'threadResume',
                            [CommonArgsMap.thread_ptr, 'prev_state', CommonArgsMap.stack_ptr, CommonArgsMap.next_thread]),
    2: tracex_event_factory('ThreadSuspendEvent', 'threadSuspend',
                            [CommonArgsMap.thread_ptr, 'new_state', CommonArgsMap.stack_ptr, CommonArgsMap.next_thread]),
    3: tracex_event_factory('ISREnterEvent', 'isrEnter',
                            [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']),
    4: tracex_event_factory('ISRExitEvent', 'isrExit',
                            [CommonArgsMap.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']),
    5: tracex_event_factory('TimeSliceEvent', 'timeSlice',
                            ['nxt_thread', 'sys_state', 'preempt_disable', CommonArgsMap.stack_ptr]),
    6: tracex_event_factory('RunningEvent', 'running',
                            ['_1', '_2', '_3', '_4']),  # No args that we care about
    10: tracex_event_factory('BlockAllocateEvent', 'blockAlloc',
                             ['pool_ptr', 'mem_ptr', CommonArgsMap.timeout, 'rem_blocks']),
    17: tracex_event_factory('BlockReleaseEvent', 'blockRelease',
                             ['pool_ptr', 'mem_ptr', 'suspended', CommonArgsMap.stack_ptr]),
    27: tracex_event_factory('ByteReleaseEvent', 'byteRelease',
                             ['pool_ptr', 'mem_ptr', 'suspended', 'avail_bytes']),
    32: tracex_event_factory('FlagsGetEvent', 'flagsGet',
                             ['group_ptr', 'req_flags', 'cur_flags', 'get_opt']),
    36: tracex_event_factory('FlagsSetEvent', 'flagsSet',
                             ['group_ptr', 'flags', 'set_opt', 'suspend_cnt']),
    52: tracex_event_factory('MtxGetEvent', 'mtxGet',
                             [CommonArgsMap.obj_id, CommonArgsMap.timeout, '_3', '_4']),
    56: tracex_event_factory('MtxPrioritizeEvent', 'mtxPrioritize',
                             [CommonArgsMap.obj_id, 'suspend_cnt', CommonArgsMap.stack_ptr, '_4']),
    57: tracex_event_factory('MtxPutEvent', 'mtxPut',
                             [CommonArgsMap.obj_id, 'owning_thread', 'own_cnt', CommonArgsMap.stack_ptr]),
    68: tracex_event_factory('QueueReceiveEvent', 'queueReceive',
                             [CommonArgsMap.queue_ptr, 'dst_ptr', CommonArgsMap.timeout, 'enqueued']),
    69: tracex_event_factory('QueueSendEvent', 'queueSend',
                             [CommonArgsMap.queue_ptr, 'src_ptr', CommonArgsMap.timeout, 'enqueued']),
    80: tracex_event_factory('SemPutEvent', 'semPut',
                             [CommonArgsMap.obj_id, 'cur_cnt', 'suspend_cnt', 'ceiling']),
    82: tracex_event_factory('SemDeleteEvent', 'semDel',
                             [CommonArgsMap.obj_id, CommonArgsMap.stack_ptr, '_3', '_4']),
    83: tracex_event_factory('SemGetEvent', 'semGet',
                             [CommonArgsMap.obj_id, CommonArgsMap.timeout, 'cur_cnt', CommonArgsMap.stack_ptr]),
    101: tracex_event_factory('ThreadDeleteEvent', 'threadDelete',
                              [CommonArgsMap.thread_ptr, CommonArgsMap.stack_ptr, '_3', '_4']),
    103: tracex_event_factory('ThreadIdEvent', 'threadIdentify',
                              ['_1', '_2', '_3', '_4']),  # No args that we care about
    107: tracex_event_factory('ThreadPreemptionChangeEvent', 'preemptionChange',
                              ['next_ctx', 'new_thresh', 'old_thresh', 'thread_state']),
    109: tracex_event_factory('ThreadRelinquishEvent', 'threadRelinquish',
                              [CommonArgsMap.stack_ptr, CommonArgsMap.next_thread, '_3', '_4']),
    112: tracex_event_factory('ThreadSleepEvent', 'threadSleep',
                              ['sleep_val', 'thread_state', CommonArgsMap.stack_ptr, '_4']),
    115: tracex_event_factory('ThreadTerminateEvent', 'threadTerminate',
                              [CommonArgsMap.thread_ptr, 'thread_state', CommonArgsMap.stack_ptr, '_4']),
    120: tracex_event_factory('TimeGetEvent', 'getTicks',
                              ['cur_ticks', 'next_ctx', '_3', '_4']),
}


def convert_event(raw_event, custom_events_map: Optional[Dict] = None) -> TraceXEvent:
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


def convert_events(raw_events: List, object_registry: List,
                   custom_events_map: Optional[Dict[int, TraceXEvent]] = None) -> List[TraceXEvent]:
    x_events = []
    for raw_event in raw_events:
        x_event = convert_event(raw_event, custom_events_map)
        x_event.apply_object_registry(object_registry)
        x_events.append(x_event)
    return x_events
