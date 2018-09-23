import sys
import asyncio
import websockets
import hashlib
import json
#https://websockets.readthedocs.io/en/stable/intro.html


serverDomain = None
nodes = dict()

if len(sys.argv) > 1 :
    serverDomain = sys.argv[1]

if serverDomain == None:
    serverDomain = "localhost"

this_node_port = 1

print("Starting....")

print(f"First trying to connect to ws host '{serverDomain} on port 1 to get all nodes")

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
            this_node_port = len(nodes) + 1
    except:        
        print(f"Failed to connect to ws://{serverDomain}:1...")
        print("Unexpected error:", sys.exc_info()[0])
    finally:
        print("Continueing to host socket")
    
asyncio.get_event_loop().run_until_complete(get_all_nodes())

#-------------------------------------------------------------------------

outbox = asyncio.Queue()
broadcast_outbox = asyncio.Queue()

async def socket_handler(websocket, path):
    consumer_task = asyncio.ensure_future(consumer_handler(websocket, path))
    producer_task = asyncio.ensure_future(producer_handler(websocket, path))
    done, pending = await asyncio.wait([consumer_task, producer_task],
        return_when=asyncio.FIRST_COMPLETED,)
    for task in pending:
        task.cancel()


async def consumer_handler(websocket, path):
    async for message in websocket:
        await consumer(message, websocket)

async def producer_handler(websocket, path):
    while True:
        message = await outbox.get()
        await websocket.send(message)

async def consumer(message, websocket):
    print("consumer message:", message)

    data = json.loads(message)
    print(f'data[msgtype]={data["msgtype"]}   data[msgpayload]={data["msgpayload"]}')
    if data["msgtype"] == "all_nodes":
        return_data = json.dumps(list(nodes.keys()))
        print(return_data)
        await outbox.put(return_data)
    elif data["msgtype"] == "new_node":
        nodes[data["msgpayload"]] = websocket

async def broadcaster_handler():
    while True:
        message = await broadcast_outbox.get()
        for node in nodes:
            try:
                if node != this_node_port:
                    if nodes[node] == None or nodes[node].closed == True:
                        async with websockets.connect(f"ws://{serverDomain}:{node}") as websocket:
                            await websocket.send(message)
                            nodes[node] = websocket
                    else:
                        await nodes[node].send(message)
            except:
                print(f"Failed to alert node: {node} message:{message}")
                print("Unexpected error:", sys.exc_info()[0])

asyncio.ensure_future(broadcaster_handler())

async def alert_all_nodes(type, data):
    print(f"alerting all nodes")
    json_obj = {}
    json_obj['msgtype'] = type
    json_obj['msgpayload'] = data
    json_data = json.dumps(json_obj)
    await broadcast_outbox.put(json_data)

nodes[this_node_port] = None
asyncio.get_event_loop().run_until_complete(alert_all_nodes("new_node", this_node_port))
asyncio.get_event_loop().run_until_complete(alert_all_nodes("new_node", this_node_port))

print(f"Serving on port {this_node_port}")
start_server = websockets.serve(socket_handler, serverDomain, this_node_port)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()


  
     