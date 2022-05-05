# TraceX Parser
This package parses ThreadX trace buffers into both human and machine-readable formats.
More documentation about ThreadX trace buffers [here](https://docs.microsoft.com/en-us/azure/rtos/tracex/chapter5)

## Install
`pip install tracex-parser`

## Examples
```python
from tracex_parser.file_parser import parse_tracex_buffer
events, obj_map = parse_tracex_buffer('./demo_threadx.trx')
```
