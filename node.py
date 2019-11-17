import sys
import asyncio
import websockets
import json
import blockchain
from threading import Thread
from collections import namedtuple
from datetime import datetime

#https://websockets.readthedocs.io/en/stable/intro.html

serverDomain = None
nodes = dict()

#server domain can be passed through as arg
if len(sys.argv) > 1 :
    serverDomain = sys.argv[1]

if serverDomain == None:
    serverDomain = "localhost"

__this_node_port = 1

class Payload(object):
    def __init__(self, jsonString = None, **kwargs):
        if jsonString != None:
            jsonObj = json.loads(jsonString)
            self.msgtype = jsonObj['msgtype']
            self.msgpayload = jsonObj['msgpayload']
        elif 'msgtype' not in kwargs or 'msgpayload' not in kwargs:
            raise ValueError('msgtype and msgpayload must be populated.')
        else:
            self.msgtype=kwargs['msgtype']
            self.msgpayload=kwargs['msgpayload']
    def toJson(self):
        return json.dumps(self.__dict__)

print("Starting....")

print(f"First trying to connect to ws host {serverDomain} on port 1 to get all nodes")

async def get_all_nodes():
    print(f"Connecting to ws://{serverDomain}:1...")
    try:
        async with websockets.connect(f"ws://{serverDomain}:1") as websocket:
            await websocket.send(Payload(msgtype="all_nodes", msgpayload="").toJson())
            data_received = await websocket.recv()
            print(f"data_received={data_received}")
            #global nodes
            nodes_rec = json.loads(data_received)
            for node in nodes_rec:
                nodes[node] = None
            global __this_node_port
            __this_node_port = len(nodes_rec) + 1
    except:        
        print(f"Failed to connect to ws://{serverDomain}:1...")
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
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
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])

async def producer_handler(websocket, path, queue):
    while True:
        try:
            message = await queue.get()
            print("producer message:", message)
            await websocket.send(message)
        except:
            #print("Unexpected error:", sys.exc_info()[0])
            pass

transactionsQueue=[]

async def AddTransaction(broadcast_outbox : Queue, transaction : Transaction):
    transactionsQueue.append(transaction.__dict__)
    print("transactions len:", len(transactionsQueue))
    if len(transactionsQueue) >= 5:
        previous_hash : str = None
        if len(blockchain.blockchain) > 0:
            previous_hash = blockchain.blockchain[len(blockchain.blockchain)-1].hash
        block = blockchain.Block(json.dumps(transactionsQueue), previous_hash)
        hash, nonce = blockchain.proof_of_work(block, 1)
        print(f"proof of work completed. Hash: {hash} Nonce:{nonce}")
        block.hash = hash
        block.nonce = nonce
        block.timestamp=datetime.utcnow().strftime("%y/%m/%d %H:%M")
        blockchain.blockchain.append(block)
        await alert_all_nodes(broadcast_outbox, "new_block", block.__dict__)
        transactionsQueue.clear()

async def consumer(message, websocket, queue):
    print("consumer message:", message)
    global nodes
    payload = Payload(message)
    if payload.msgtype == "all_nodes":
        return_data = json.dumps(list(nodes.keys()))
        print(return_data)
        await queue.put(return_data)
    elif payload.msgtype == "new_node":
        nodes[payload.msgpayload] = None #reserve
        blockchain_json = json.dumps([b.__dict__ for b in blockchain.blockchain])
        full_message = Payload(msgtype="full_blockchain",msgpayload=blockchain_json).toJson()
        await websocket.send(full_message)
    elif payload.msgtype == "full_blockchain":
        try: 
            jsonObj=json.loads(payload.msgpayload)

            for b in jsonObj:
                block = blockchain.Block(b['data'], b['previous_hash'], b['index'], b['timestamp'], b['hash'], b['nonce'])
                blockchain.blockchain.append(block)
        except: 
            blockchain.blockchain = []
            print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
        
        print('received full blockchain')
    elif payload.msgtype == "new_block":
        jsonObj = payload.msgpayload
        block = blockchain.Block(jsonObj['data'], jsonObj['previous_hash'], jsonObj['index'], jsonObj['timestamp'], jsonObj['hash'], jsonObj['nonce'])
        blockchain.blockchain.append(block)
    else:
        print("Unknown msgtype received: ", payload.msgtype)
        

async def broadcaster_handler(broadcast_outbox, event_loop):
    while True:
        try:
            message = await broadcast_outbox.get()
            print('broadcasting: ', message)
            for node in nodes:
                try:
                    if node != __this_node_port:
                        if nodes[node] == None:
                            nodes[node] = asyncio.Queue()
                            await nodes[node].put(message)
                            event_loop.create_task(connect_socket(serverDomain, node))
                        else:
                            await nodes[node].put(message)
                    print('broadcasted: ', message)
                except:
                    print(f"Failed to broadcast to node: {node} message:{message}")
                    #print("Unexpected error:", sys.exc_info()[0])            
        except:
            #temp = str(sys.exc_info()[0])
            #print(temp)
            if str(sys.exc_info()[0])!="<class 'asyncio.queues.QueueEmpty'>":
                print("broadcast_outbox.get() - Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
            pass
            
async def alert_all_nodes(broadcast_outbox, type, data):
    print(f"alerting all nodes")
    payload = Payload(msgtype=type, msgpayload=data)
    json_data = payload.toJson()
    await broadcast_outbox.put(json_data)

nodes[__this_node_port] = None

def start_server():
    
    global event_loop
    
    event_loop = asyncio.new_event_loop()

    asyncio.set_event_loop(event_loop)

    global broadcast_outbox 
    broadcast_outbox= asyncio.Queue()

    event_loop.run_until_complete(get_all_nodes())
    print('get_all_nodes done')

    event_loop.create_task(alert_all_nodes(broadcast_outbox, "new_node", __this_node_port))
    event_loop.create_task(broadcaster_handler(broadcast_outbox, event_loop))

    print(f"Serving on port {__this_node_port}")
    event_loop.run_until_complete(websockets.serve(socket_handler, serverDomain, __this_node_port))

    event_loop.run_forever()

t = Thread(target = start_server)
t.start()