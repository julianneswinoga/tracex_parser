Command Line Interface
======================

The ``file_parser`` module can also be run as a script, which will provide simple statistics on the trace as well as dumping all the events in the trace:

.. code-block:: console

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

