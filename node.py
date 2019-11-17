"""Node implementation - communication between online blockchain node using web sockets."""
import sys
import asyncio
from datetime import datetime
from threading import Thread
import json
import websockets
import blockchain

#https://websockets.readthedocs.io/en/stable/intro.html

SERVER_DOMAIN = None
NODES = dict()

#server domain can be passed through as arg
if len(sys.argv) > 1:
    SERVER_DOMAIN = sys.argv[1]

if SERVER_DOMAIN is None:
    SERVER_DOMAIN = "localhost"

__THIS_NODE_PORT = 1

class Payload:
    """Data wrapper that all websocket data will use."""
    def __init__(self, jsonString=None, **kwargs):
        if jsonString is not None:
            json_obj = json.loads(jsonString)
            self.msgtype = json_obj['msgtype']
            self.msgpayload = json_obj['msgpayload']
        elif 'msgtype' not in kwargs or 'msgpayload' not in kwargs:
            raise ValueError('msgtype and msgpayload must be populated.')
        else:
            self.msgtype = kwargs['msgtype']
            self.msgpayload = kwargs['msgpayload']
    def to_json(self):
        """Converts the payload to a json string."""
        return json.dumps(self.__dict__)

print("Starting....")

print(f"First trying to connect to ws host {SERVER_DOMAIN} on port 1 to get all nodes")

async def get_all_nodes():
    """Gets all online nodes in the blockchain."""
    print(f"Connecting to ws://{SERVER_DOMAIN}:1...")
    try:
        async with websockets.connect(f"ws://{SERVER_DOMAIN}:1") as websocket:
            await websocket.send(Payload(msgtype="all_nodes", msgpayload="").to_json())
            data_received = await websocket.recv()
            print(f"data_received={data_received}")
            #global nodes
            nodes_rec = json.loads(data_received)
            for node in nodes_rec:
                NODES[node] = None
            global __THIS_NODE_PORT
            __THIS_NODE_PORT = len(nodes_rec) + 1
    except:
        print(f"Failed to connect to ws://{SERVER_DOMAIN}:1...")
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
    finally:
        print("Continueing to host socket")

#-------------------------------------------------------------------------
async def connect_socket(node):
    """Connect to a node."""
    async with websockets.connect(f"ws://{SERVER_DOMAIN}:{node}") as websocket:
        await socket_handler_queue(websocket, NODES[node])

async def socket_handler_queue(websocket, queue):
    """Web Socket initialization."""
    consumer_task = asyncio.create_task(consumer_handler(websocket, queue))
    producer_task = asyncio.create_task(producer_handler(websocket, queue))
    pending = await asyncio.wait([consumer_task, producer_task],
                                 return_when=asyncio.FIRST_COMPLETED,)
    for task in pending:
        print("cancelling")
        task.cancel()

async def socket_handler(websocket):
    """Web Socket handler."""
    queue = asyncio.Queue()
    await socket_handler_queue(websocket, queue)

async def consumer_handler(websocket, queue):
    """Consumer handler for the web socket communication between nodes."""
    try:
        while True:
            async for message in websocket:
                await consumer(message, websocket, queue)
    except:
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])

async def producer_handler(websocket, queue):
    """Producer handler for the web socket communication between nodes."""
    while True:
        try:
            message = await queue.get()
            print("producer message:", message)
            await websocket.send(message)
        except:
            #print("Unexpected error:", sys.exc_info()[0])
            pass

TRANSACTIONS_QUEUE = []

async def add_transaction(broadcast_outbox, transaction):
    """Adds a transaction to a block in the blockchain."""
    TRANSACTIONS_QUEUE.append(transaction.__dict__)
    print("transactions len:", len(TRANSACTIONS_QUEUE))
    if len(TRANSACTIONS_QUEUE) >= 5:
        previous_hash: str = None
        if len(blockchain.blockchain) > 0:
            previous_hash = blockchain.blockchain[len(blockchain.blockchain)-1].hash
        block = blockchain.Block(json.dumps(TRANSACTIONS_QUEUE), previous_hash)
        hash_value, nonce = blockchain.proof_of_work(block, 1)
        print(f"proof of work completed. Hash: {hash_value} Nonce:{nonce}")
        block.hash_value = hash_value
        block.nonce = nonce
        block.timestamp = datetime.utcnow().strftime("%y/%m/%d %H:%M")
        blockchain.blockchain.append(block)
        await alert_all_nodes(broadcast_outbox, "new_block", block.__dict__)
        TRANSACTIONS_QUEUE.clear()

async def consumer(message, websocket, queue):
    """Consumer implementation for when a web socket message is received."""
    print("consumer message:", message)
    global NODES
    payload = Payload(message)
    if payload.msgtype == "all_nodes":
        return_data = json.dumps(list(NODES.keys()))
        print(return_data)
        await queue.put(return_data)
    elif payload.msgtype == "new_node":
        NODES[payload.msgpayload] = None #reserve
        blockchain_json = json.dumps([b.__dict__ for b in blockchain.blockchain])
        full_message = Payload(msgtype="full_blockchain", msgpayload=blockchain_json).to_json()
        await websocket.send(full_message)
    elif payload.msgtype == "full_blockchain":
        try:
            json_obj = json.loads(payload.msgpayload)

            for block in json_obj:
                block = blockchain.Block(block['data'], block['previous_hash'], block['index'],
                                         block['timestamp'], block['hash'], block['nonce'])
                blockchain.blockchain.append(block)
        except:
            blockchain.blockchain = []
            print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])

        print('received full blockchain')
    elif payload.msgtype == "new_block":
        json_obj = payload.msgpayload
        block = blockchain.Block(json_obj['data'], json_obj['previous_hash'],
                                 json_obj['index'], json_obj['timestamp'], json_obj['hash'],
                                 json_obj['nonce'])
        blockchain.blockchain.append(block)
    else:
        print("Unknown msgtype received: ", payload.msgtype)


async def broadcaster_handler(broadcast_outbox, event_loop):
    """The Web socket broadcaster to send data to all online nodes."""
    while True:
        try:
            message = await broadcast_outbox.get()
            print('broadcasting: ', message)
            for node in NODES:
                try:
                    if node is not __THIS_NODE_PORT:
                        if NODES[node] is None:
                            NODES[node] = asyncio.Queue()
                            await NODES[node].put(message)
                            event_loop.create_task(connect_socket(node))
                        else:
                            await NODES[node].put(message)
                    print('broadcasted: ', message)
                except:
                    print(f"Failed to broadcast to node: {node} message:{message}")
                    #print("Unexpected error:", sys.exc_info()[0])
        except:
            #temp = str(sys.exc_info()[0])
            #print(temp)
            if str(sys.exc_info()[0]) != "<class 'asyncio.queues.QueueEmpty'>":
                print("broadcast_outbox.get() - Unexpected error:",
                      sys.exc_info()[0], sys.exc_info()[1])

async def alert_all_nodes(broadcast_outbox, type, data):
    """Send data to all online nodes."""
    print(f"alerting all nodes")
    payload = Payload(msgtype=type, msgpayload=data)
    json_data = payload.to_json()
    await broadcast_outbox.put(json_data)

NODES[__THIS_NODE_PORT] = None
EVENT_LOOP = None
BROADCAST_OUTBOX = None

def start_server():
    """Start the web socket server."""
    global EVENT_LOOP

    EVENT_LOOP = asyncio.new_event_loop()

    asyncio.set_event_loop(EVENT_LOOP)

    global BROADCAST_OUTBOX
    BROADCAST_OUTBOX = asyncio.Queue()

    EVENT_LOOP.run_until_complete(get_all_nodes())
    print('get_all_nodes done')

    EVENT_LOOP.create_task(alert_all_nodes(BROADCAST_OUTBOX, "new_node", __THIS_NODE_PORT))
    EVENT_LOOP.create_task(broadcaster_handler(BROADCAST_OUTBOX, EVENT_LOOP))

    print(f"Serving on port {__THIS_NODE_PORT}")
    EVENT_LOOP.run_until_complete(websockets.serve(socket_handler, SERVER_DOMAIN, __THIS_NODE_PORT))

    EVENT_LOOP.run_forever()

thread: Thread = Thread(target=start_server)
thread.start()
