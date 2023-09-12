Command Line Interface
======================

The ``file_parser`` module can also be run as a script, which will provide simple statistics on the trace as well as dumping all the events in the trace.
It can be run by either:

* Running the module manually: ``python3 -m tracex_parser.file_parser``
* Using the newly installed command: ``parse-trx``

Both run methods are identical.

.. code-block:: console

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

