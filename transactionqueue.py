"""REST API using Quart thats hosts a single endpoint POST /tx.
This will be hosted on every single node, using a port between 5000-6000."""
import random
from quart import Quart, request
from blockchain import Transaction
import node

APP = Quart(__name__)

@APP.route('/')
def index():
    """Simple HTTP GET to return "OK" for health check."""
    return "OK"

@APP.route('/tx', methods=['POST'])
async def transaction():
    """HTTP POST endpoint to submit a new transaction to the blockchain."""
    new_tx: str = await request.get_json()
    print(f"New transaction FROM: {new_tx['from']} TO: {new_tx['to']} AMOUNT: {new_tx['amount']}\n")

    #TODO:VALIDATION HERE

    tran: Transaction = Transaction(str(new_tx['from']), str(new_tx['to']), str(new_tx['amount']))

    try:
        await node.add_transaction(node.broadcast_outbox, tran)
    except Exception as ex:
        print("Error '{0}' occured. Arguments {1}.".format(ex, ex.args))
    return "OK"

if __name__ == "__main__":
    APP.run(port=random.randint(5000, 6000))
    #app.run(port=5000)
