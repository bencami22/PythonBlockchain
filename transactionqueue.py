from blockchain import Transaction
from flask import Flask, request, render_template
import json
from node import loop, broadcast_outbox
import asyncio

app = Flask(__name__)

@app.route('/')
def index():
    return "OK"

@app.route('/tx', methods=['POST'])
def transaction():
  if request.method == 'POST':
    new_tx = request.get_json()
    print(f"New transaction FROM: {new_tx['from']} TO: {new_tx['to']} AMOUNT: {new_tx['amount']}\n")
    #TODO:VALIDATION HERE
    transaction = Transaction(str(new_tx['from']), str(new_tx['to']), str(new_tx['amount']))
    transaction_json = json.dumps(transaction.__dict__)
    task = loop.create_task(broadcast_outbox.put('{"msgtype":"new_transaction", "msgpayload":"'+transaction_json+'}"}'))
    loop.run_until_complete(task)
    return "OK"

if __name__ == "__main__":
    app.run()