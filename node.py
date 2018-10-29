import sys
import asyncio
import websockets
import json
import blockchain
from threading import Thread

#https://websockets.readthedocs.io/en/stable/intro.html

serverDomain = None
nodes = dict()

if len(sys.argv) > 1 :
    serverDomain = sys.argv[1]

if serverDomain == None:
    serverDomain = "localhost"

this_node_port = 1

print("Starting....")

print(f"First trying to connect to ws host {serverDomain} on port 1 to get all nodes")

async def get_all_nodes():
    print(f"Connecting to ws://{serverDomain}:1...")
    try:
        async with websockets.connect(f"ws://{serverDomain}:1") as websocket:
            await websocket.send('{"msgtype":"all_nodes","msgpayload":""}')
            data_received = await websocket.recv()
            print(f"data_received={data_received}")
            global nodes
            nodes_rec = json.loads(data_received)
            for node in nodes_rec:
                nodes[node] = None
            global this_node_port
            this_node_port = len(nodes_rec) + 1
    except:        
        print(f"Failed to connect to ws://{serverDomain}:1...")
        print("Unexpected error:", sys.exc_info()[0])
    finally:
        print("Continueing to host socket")
    


#-------------------------------------------------------------------------
async def connect_socket(server_domain, node):
    async with websockets.connect(f"ws://{serverDomain}:{node}") as websocket:
        await socket_handler_queue(websocket, f"ws://{serverDomain}:{node}", nodes[node])

async def socket_handler_queue(websocket, path, queue):
    consumer_task = asyncio.create_task(consumer_handler(websocket, path, queue))
    producer_task = asyncio.create_task(producer_handler(websocket, path, queue))
    pending = await asyncio.wait([consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,)
    for task in pending:
        print("cancelling")
        task.cancel()

async def socket_handler(websocket, path):
    queue = asyncio.Queue()
    await socket_handler_queue(websocket, path, queue)

async def consumer_handler(websocket, path, queue):
    try:
        while True:
            async for message in websocket:
                await consumer(message, websocket, queue)
    except:
        print("Unexpected error:", sys.exc_info()[0])

async def producer_handler(websocket, path, queue):
    while True:
        try:
            message = await queue.get()
            print("producer message:", message)
            await websocket.send(message)
        except:
            print("Unexpected error:", sys.exc_info()[0])

transactionsQueue=[]

async def consumer(message, websocket, queue):
    print("consumer message:", message)
    global nodes
    data = json.loads(message)
    print(f'data[msgtype]={data["msgtype"]}   data[msgpayload]={data["msgpayload"]}')
    if data["msgtype"] == "all_nodes":
        return_data = json.dumps(list(nodes.keys()))
        print(return_data)
        await queue.put(return_data)
    elif data["msgtype"] == "new_node":
        nodes[data["msgpayload"]] = None #reserve
    elif data["msgtype"] == "new_transaction":
        transactionsQueue.append(data["msgpayload"])
        print("transactions len:"+len(transactionsQueue))
        if len(transactionsQueue) >=5:
            previous_hash = None
            if len(blockchain.blockchain) > 0:
                previous_hash = blockchain.blockchain[len(blockchain.blockchain)].hash
            block = blockchain.Block(transactionsQueue.__dict__, previous_hash)
            hash, nonce= blockchain.proof_of_work(block, 1)
            print(f"proof of work completed. Hash: {hash} Nonce:{nonce}")
            block.hash = hash
            block.nonce = nonce

async def broadcaster_handler(broadcast_outbox, event_loop):
    while True:
        try:
            message = await broadcast_outbox.get()
            for node in nodes:
                try:
                    if node != this_node_port:
                        if nodes[node] == None:
                            nodes[node] = asyncio.Queue()
                            await nodes[node].put(message)
                            event_loop.create_task(connect_socket(serverDomain, node))
                        else:
                            await nodes[node].put(message)
                except:
                    print(f"Failed to alert node: {node} message:{message}")
                    print("Unexpected error:", sys.exc_info()[0])
        except:
            print("broadcast_outbox.get() - Unexpected error:", sys.exc_info()[0])

async def alert_all_nodes(broadcast_outbox, type, data):
    print(f"alerting all nodes")
    json_obj = {}
    json_obj['msgtype'] = type
    json_obj['msgpayload'] = data
    json_data = json.dumps(json_obj)
    await broadcast_outbox.put(json_data)

nodes[this_node_port] = None

def start_server():
    event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(event_loop)


    event_loop.run_until_complete(get_all_nodes())

    global broadcast_outbox 
    broadcast_outbox= asyncio.Queue()
    event_loop.create_task(broadcaster_handler(broadcast_outbox, event_loop))
    
    event_loop.run_until_complete(alert_all_nodes(broadcast_outbox, "new_node", this_node_port))


    print(f"Serving on port {this_node_port}")

    event_loop.run_until_complete(websockets.serve(socket_handler, serverDomain, this_node_port))
    event_loop.run_forever()

t = Thread(target = start_server)
t.start()