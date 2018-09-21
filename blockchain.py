import sys
import asyncio
import websockets
import hashlib
import json
#https://websockets.readthedocs.io/en/stable/intro.html
nodes = dict()
serverDomain = None

if len(sys.argv) > 1 :
    serverDomain = sys.argv[1]

if serverDomain == None:
    serverDomain = "localhost"

this_node_port = 1

print("Starting....")

print("First trying to connect to ws host '{serverDomain} on port 1 to get all nodes")

async def client_all_nodes():
    print(f"Connecting to ws://{serverDomain}:1...")
    try:
        async with websockets.connect(f"ws://{serverDomain}:1") as websocket:
            await websocket.send('{"msgtype":"all_nodes","msgpayload":""}')
            data_received = await websocket.recv()
            print(f"data_received={data_received}")
            global nodes
            nodes = json.loads(data_received)
            global this_node_port
            this_node_port = len(nodes) + 1
    except:
        print("Unexpected error:", sys.exc_info()[0])
        print(f"Failed to connect to ws://{serverDomain}:1...")
    finally:
        print("Continueing to host socket")
    
asyncio.get_event_loop().run_until_complete(client_all_nodes())



async def node_socket(websocket, path):
    # Register node
    print(f"WebSocket connection: {websocket}")
    #await register(websocket)
    try:
        #await websocket.send(state_event())
        async for message in websocket:
            data = json.loads(message)
            print(f'data[msgtype]={data["msgtype"]}   data[msgpayload]={data["msgpayload"]}')
            if data["msgtype"] == "all_nodes":
                return_data = json.dumps(nodes)
                print(return_data)
                await websocket.send(return_data)
    except:
        print("Unexpected error:", sys.exc_info()[0])
    finally:
        #await unregister(websocket)
        pass


    #nodes[this_node_port] = websocket
    #try:
    #    print(f"websocket: {websocket} path:{path}")
    #finally:
    #    # Unregister node
    #    del nodes[this_node_port]


print(f"serving on port {len(nodes)+1}")
start_server = websockets.serve(node_socket, serverDomain, this_node_port)

nodes[this_node_port] = None

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()

#hash = hashlib.sha256(b"hello world").hexdigest()
#print (hash)