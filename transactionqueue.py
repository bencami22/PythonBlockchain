import sys
from quart import Quart, request, render_template
from blockchain import Transaction
import json
import node 
import random
import asyncio

app = Quart(__name__)

@app.route('/')
def index():
    return "OK"

@app.route('/tx', methods=['POST'])
async def transaction():
    new_tx = await request.get_json()
    print(f"New transaction FROM: {new_tx['from']} TO: {new_tx['to']} AMOUNT: {new_tx['amount']}\n")
    #TODO:VALIDATION HERE
    transaction = Transaction(str(new_tx['from']), str(new_tx['to']), str(new_tx['amount']))
    try:
        await node.AddTransaction(node.broadcast_outbox, transaction)
    except:
        print("Unexpected error:", sys.exc_info()[0], sys.exc_info()[1])
    return "OK"

if __name__ == "__main__":
    app.run(port=random.randint(5000,6000))
    #app.run(port=5000)