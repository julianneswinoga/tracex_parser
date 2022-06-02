from typing import *

from .helpers import TraceXEventException, CStruct, TextColour


class CommonArg:
    """
    Holds string mappings for common arguments so that we can
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

    def as_str(self, txt_colour: Optional[TextColour] = None):
        # So we don't have to worry about checking if colours are valid
        if txt_colour is None:
            colour = TextColour(False)
        else:
            colour = txt_colour

        thread_str = self.thread_name if self.thread_name is not None else self.thread_ptr
        fn_str = self.fn_name if self.fn_name is not None else f'<TX ID#{self.id}>'
        arg_strs = []
        for arg_name, arg_val in self.mapped_args.items():
            if arg_name.startswith('_'):
                # Don't print arg names that start with an underscore
                continue
            if isinstance(arg_val, int):
                # For this printing always convert raw integers to hex
                arg_strs.append(f'{arg_name}={colour.wte}{hex(arg_val)}{colour.rst}')
            else:
                arg_strs.append(f'{arg_name}={colour.red}{arg_val}{colour.rst}')
        arg_str = ','.join(arg_strs)

        return f'{colour.cya}{self.timestamp}{colour.rst}:' \
               f'{colour.red}{thread_str}{colour.rst} ' \
               f'{colour.yel}{fn_str}{colour.rst}({arg_str})'

    def __repr__(self):
        return self.as_str(None)

    def _generate_arg_dict(self, arg_names: List[str]) -> Dict[str, Any]:
        if len(self.arg_map) != 4:
            raise TraceXEventException(f'{self.__class__.__name__} arg map must have exactly 4 entries: {self.arg_map}')
        return {k: v for k, v in zip(arg_names, self.raw_args)}

    def _map_ptr_to_obj_reg_name(self, obj_reg_map: Dict[int, CStruct], key_ptr: int) -> Optional[str]:
        if key_ptr in obj_reg_map:
            raw_obj_name = obj_reg_map[key_ptr]['thread_reg_entry_obj_name']
            try:
                return raw_obj_name.decode('ASCII')
            except UnicodeDecodeError:
                print(f'{self.__class__.__name__}: Could not decode {raw_obj_name} into ascii')
                return None
        print(f'Cant find {hex(key_ptr)} in objreg')
        return None

    def apply_object_registry(self, obj_reg_map: Dict[int, CStruct]):
        # Change mapped arguments to strings if they can be found in the registry
        args_to_map = [CommonArg.obj_id, CommonArg.thread_ptr, CommonArg.next_thread]
        for arg_to_map in args_to_map:
            if arg_to_map in self.mapped_args.keys():
                obj_reg_name = self._map_ptr_to_obj_reg_name(obj_reg_map, self.mapped_args[arg_to_map])
                if obj_reg_name is not None:
                    self.mapped_args[arg_to_map] = obj_reg_name
                else:
                    print(f'Failed to map {arg_to_map} in {self.__class__.__name__}:{self.mapped_args}')

        # Make the thread names nicer
        if self.thread_ptr == 0xFFFFFFFF:
            # @see https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter11#thread-pointer
            self.thread_name = 'INTERRUPT'
        else:
            # Try to find time slice thread_ptr in the registry
            obj_reg_name = self._map_ptr_to_obj_reg_name(obj_reg_map, self.thread_ptr)
            if obj_reg_name is not None:
                self.thread_name = obj_reg_name
            else:
                print(f'Failed to map thread_ptr in {self.__class__.__name__}:{self.mapped_args}')

        # Make timeouts nicer
        if CommonArg.timeout in self.mapped_args.keys():
            # Replace if it's in the lookup, no replacement otherwise
            self.mapped_args[CommonArg.timeout] = {
                0: 'NoWait',
                0xFFFFFFFF: 'WaitForever',
            }.get(self.mapped_args[CommonArg.timeout], self.mapped_args[CommonArg.timeout])


def tracex_event_factory(class_name: str, fn_name: Optional[str] = None, arg_map: Optional[List] = None,
                         class_name_is_fn_name: bool = False) -> ClassVar:
    # Create the event classes dynamically
    funct_name = class_name if class_name_is_fn_name else fn_name
    if arg_map is not None:
        class_params = {
            'fn_name': funct_name,
            'arg_map': arg_map,
        }
    else:
        class_params = {
            'fn_name': funct_name,
        }
    return type(class_name, (TraceXEvent,), class_params)


# see tx_trace.h for all these mappings
event_id_map = {
    1: tracex_event_factory('ThreadResumeEvent', 'threadResume',
                            [CommonArg.thread_ptr, 'prev_state', CommonArg.stack_ptr, CommonArg.next_thread]),
    2: tracex_event_factory('ThreadSuspendEvent', 'threadSuspend',
                            [CommonArg.thread_ptr, 'new_state', CommonArg.stack_ptr, CommonArg.next_thread]),
    3: tracex_event_factory('ISREnterEvent', 'isrEnter',
                            [CommonArg.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']),
    4: tracex_event_factory('ISRExitEvent', 'isrExit',
                            [CommonArg.stack_ptr, 'isr_num', 'sys_state', 'preempt_dis']),
    5: tracex_event_factory('TimeSliceEvent', 'timeSlice',
                            ['nxt_thread', 'sys_state', 'preempt_disable', CommonArg.stack_ptr]),
    6: tracex_event_factory('RunningEvent', 'running',
                            ['_1', '_2', '_3', '_4']),  # No args that we care about
    10: tracex_event_factory('BlockAllocateEvent', 'blockAlloc',
                             ['pool_ptr', 'mem_ptr', CommonArg.timeout, 'rem_blocks']),
    17: tracex_event_factory('BlockReleaseEvent', 'blockRelease',
                             ['pool_ptr', 'mem_ptr', 'suspended', CommonArg.stack_ptr]),
    27: tracex_event_factory('ByteReleaseEvent', 'byteRelease',
                             ['pool_ptr', 'mem_ptr', 'suspended', 'avail_bytes']),
    32: tracex_event_factory('FlagsGetEvent', 'flagsGet',
                             ['group_ptr', 'req_flags', 'cur_flags', 'get_opt']),
    36: tracex_event_factory('FlagsSetEvent', 'flagsSet',
                             ['group_ptr', 'flags', 'set_opt', 'suspend_cnt']),
    50: tracex_event_factory('MtxCreateEvent', 'mtxCreate',
                             [CommonArg.obj_id, 'inheritance', CommonArg.stack_ptr, '_4']),
    51: tracex_event_factory('MtxDeleteEvent', 'mtxDel',
                             [CommonArg.obj_id, CommonArg.stack_ptr, '_3', '_4']),
    52: tracex_event_factory('MtxGetEvent', 'mtxGet',
                             [CommonArg.obj_id, CommonArg.timeout, '_3', '_4']),
    56: tracex_event_factory('MtxPrioritizeEvent', 'mtxPrioritize',
                             [CommonArg.obj_id, 'suspend_cnt', CommonArg.stack_ptr, '_4']),
    57: tracex_event_factory('MtxPutEvent', 'mtxPut',
                             [CommonArg.obj_id, 'owning_thread', 'own_cnt', CommonArg.stack_ptr]),
    68: tracex_event_factory('QueueReceiveEvent', 'queueReceive',
                             [CommonArg.queue_ptr, 'dst_ptr', CommonArg.timeout, 'enqueued']),
    69: tracex_event_factory('QueueSendEvent', 'queueSend',
                             [CommonArg.queue_ptr, 'src_ptr', CommonArg.timeout, 'enqueued']),
    80: tracex_event_factory('SemCeilPutEvent', 'semCeilPut',
                             [CommonArg.obj_id, 'cur_cnt', 'suspend_cnt', 'ceiling']),
    88: tracex_event_factory('SemPutEvent', 'semPut',
                             [CommonArg.obj_id, 'cur_cnt', 'suspend_cnt', CommonArg.stack_ptr]),
    82: tracex_event_factory('SemDeleteEvent', 'semDel',
                             [CommonArg.obj_id, CommonArg.stack_ptr, '_3', '_4']),
    83: tracex_event_factory('SemGetEvent', 'semGet',
                             [CommonArg.obj_id, CommonArg.timeout, 'cur_cnt', CommonArg.stack_ptr]),
    101: tracex_event_factory('ThreadDeleteEvent', 'threadDelete',
                              [CommonArg.thread_ptr, CommonArg.stack_ptr, '_3', '_4']),
    103: tracex_event_factory('ThreadIdEvent', 'threadIdentify',
                              ['_1', '_2', '_3', '_4']),  # No args that we care about
    107: tracex_event_factory('ThreadPreemptionChangeEvent', 'preemptionChange',
                              ['next_ctx', 'new_thresh', 'old_thresh', 'thread_state']),
    109: tracex_event_factory('ThreadRelinquishEvent', 'threadRelinquish',
                              [CommonArg.stack_ptr, CommonArg.next_thread, '_3', '_4']),
    112: tracex_event_factory('ThreadSleepEvent', 'threadSleep',
                              ['sleep_val', 'thread_state', CommonArg.stack_ptr, '_4']),
    115: tracex_event_factory('ThreadTerminateEvent', 'threadTerminate',
                              [CommonArg.thread_ptr, 'thread_state', CommonArg.stack_ptr, '_4']),
    120: tracex_event_factory('TimeGetEvent', 'getTicks',
                              ['cur_ticks', 'next_ctx', '_3', '_4']),
}


def convert_event(raw_event, custom_events_map: Optional[Dict] = None) -> TraceXEvent:
    event_id = raw_event['event_id']
    raw_event_args = [raw_event['info_field_1'], raw_event['info_field_2'],
                      raw_event['info_field_3'], raw_event['info_field_4']]

    args = [raw_event['thread_ptr'], raw_event['thread_priority'], event_id,
            raw_event['time_stamp'], raw_event_args]
    if custom_events_map and event_id in custom_events_map:
        # Check custom events first
        return custom_events_map[event_id](*args)
    elif event_id in event_id_map:
        return event_id_map[event_id](*args)
    else:
        # We don't have a lookup, create a base event
        return TraceXEvent(*args)


def convert_events(raw_events: List, obj_reg_map: Dict[int, CStruct],
                   custom_events_map: Optional[Dict[int, TraceXEvent]] = None) -> List[TraceXEvent]:
    x_events = []
    for raw_event in raw_events:
        x_event = convert_event(raw_event, custom_events_map)
        x_event.apply_object_registry(obj_reg_map)
        x_events.append(x_event)
    return x_events
