# PythonBlockchain
Beginner in Python with a moderate understanding of Blockchain having a whip at it.

Avoiding the the complexities of existent production blockchain, this implementation:

- Each node has it's own transaction queue which is hosted on HTTP. 
- Nodes communication over web sockets.
- The end user will choose their favourite/ most reliable transaction queue node by URL.
- Each block is communicate to the rest of the network
- New nodes will receive the full blockchain on startup.
- Very simple block integrity checking
