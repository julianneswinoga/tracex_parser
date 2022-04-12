from typing import *


class CommonArgsMap:
    obj_id = 'obj_id'
    stack_ptr = 'stack_ptr'
    thread_ptr = 'thread_ptr'


class TraceXEvent:
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
            arg_str = ', '.join(f'{num}={hex(arg)}' for num, arg in enumerate(self.args))
        else:
            arg_str = self.args
        return f'{self.timestamp}:{thread_str} {fn_str}({arg_str})'

    def _generate_arg_dict(self, arg_names: List[str]) -> Dict[str, Any]:
        return {k: v for k, v in zip(arg_names, self.args)}

    def apply_object_registry(self, object_registry: List):
        # This can be done for all objects
        if self.thread_ptr == 0xFFFFFFFF:
            self.thread_name = 'INTERRUPT'
        else:
            for obj in object_registry:
                if self.thread_ptr == obj['thread_registry_entry_object_pointer']:
                    self.thread_name = obj['thread_registry_entry_object_name'].decode('ASCII')


class SemPutEvent(TraceXEvent):
    function_name = 'semPut'

    def apply_object_registry(self, object_registry: List):
        super().apply_object_registry(object_registry)
        self.function_name = SemPutEvent.function_name
        self.mapped_args = self._generate_arg_dict([CommonArgsMap.obj_id, 'timeout', 'cur_cnt', 'stack_ptr'])
        self.args = f"sem_id={hex(self.mapped_args[CommonArgsMap.obj_id])}, stack_ptr={hex(self.mapped_args['stack_ptr'])}"


class SemGetEvent(TraceXEvent):
    function_name = 'semGet'

    def apply_object_registry(self, object_registry: List):
        super().apply_object_registry(object_registry)
        self.function_name = SemGetEvent.function_name
        self.mapped_args = self._generate_arg_dict([CommonArgsMap.obj_id, 'cur_cnt', 'suspend_cnt', 'ceiling'])
        self.args = f"sem_id={hex(self.mapped_args[CommonArgsMap.obj_id])}, cur_cnt={hex(self.mapped_args['cur_cnt'])}"


def convert_event(raw_event) -> TraceXEvent:
    id_map = {
        # 3: EventRemaps.isrEnter,
        # 4: EventRemaps.isrExit,
        # 5: EventRemaps.timeSlice,
        # 52: EventRemaps.mtxGet,
        # 57: EventRemaps.mtxPut,
        80: SemPutEvent,
        83: SemGetEvent,
        # 103: EventRemaps.threadIdentify,
        # 107: EventRemaps.threadPreemptionChange,
        # 120: EventRemaps.timeGet,
    }
    event_id = raw_event['event_id']
    raw_event_args = [raw_event['information_field_1'], raw_event['information_field_2'],
                      raw_event['information_field_3'], raw_event['information_field_4']]
    args = [raw_event['thread_pointer'], raw_event['thread_priority'], event_id,
            raw_event['time_stamp'], raw_event_args]
    if event_id in id_map:
        return id_map[event_id](*args)
    else:
        return TraceXEvent(*args)
