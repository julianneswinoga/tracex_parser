Python Module Interface
#######################

Simple Usage
************

The main interface to this module is through the ``parse_tracex_buffer()`` function in the ``file_parser`` module.

.. code-block:: python

    from tracex_parser.file_parser import parse_tracex_buffer

TODO: Add more docs here

Custom User Event Parsing
*************************

This module also allows you to specify the format of user events such that they can automatically be parsed from their raw form.

Create the event with ``events.tracex_event_factory()``
=======================================================

Arguments:

* ``class_name``: A unique name to represent the event (internally it is the name of the returned class)
* ``fn_name``: A nice name that will be shown in the trace output
* ``arg_map``: A list of exactly 4 argument names to apply to the event.

    * Names prefixed with an underscore (``_``) will not be shown by default
    * See :ref:`events_CommonArg` for special handling of arguments

* ``class_name_is_fn_name``: If ``True`` you do not have to specify a ``fn_name`` and the ``class_name`` will be used instead

.. _events_CommonArg:

``events.CommonArg``
--------------------

Some attributes under this class have special meaning to the parsing logic:

* ``events.CommonArg.timeout``: Will replace the raw number with:

    * ``0`` → ``'NoWait'``
    * ``0xFFFFFFFF`` → ``'WaitForever'``

* ``events.CommonArg.obj_id``: Will look in the object registry for an object with the same memory address and replace the raw number with that object's name
* ``events.CommonArg.thread_ptr``: Same as ``events.CommonArg.obj_id``, but for thread names
* ``events.CommonArg.next_thread``: Same as ``events.CommonArg.thread_ptr``

Use custom events with ``parse_tracex_buffer()``
================================================

Once the custom event is created with ``events.tracex_event_factory()`` you need to assign it to an event id.
This is done by creating a dictionary with the key corresponding to the event id and the value being the custom event.
Then that dictionary is passed to the ``custom_events_map`` parameter of ``parse_tracex_buffer()``.

Custom Events Example
=====================

In this example we are going to parse event #5000, which I have compiled into my TraceX application using ``tx_trace_user_event_insert()``.
I've passed following arguments to event #5000:

#. Line number
#. Address of a semaphore object
#. File descriptor number
#. Always 0

In the C code it looks like the following:

.. code-block:: C

    tx_trace_user_event_insert(5000, __LINE__, (TX_SEMAPHORE *) semPtr, fd, 0);

Now parsing it with the `tracex_parser` module:

.. literalinclude:: /../../examples/custom_event.py
    :caption: examples/custom_event.py
    :lines: 2-

The parsed event is now shown as:

.. code-block:: text

    7821:myThread custEvent(line_num=1234,obj_id=fdSem,fd=5)

Without the custom event it would be shown as:

.. code-block:: text

    7821:myThread <TX ID#5000>(arg1=0x4d2,arg2=0x82070000,arg3=0x5,arg4=0x0)
