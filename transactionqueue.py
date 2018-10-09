from blockchain import Block, Transaction, proof_of_work
from flask import Flask, request, render_template
import json
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
    hash, nonce= proof_of_work(Block(json.dumps(transaction.__dict__), None), 1)
    print(f"Hash: {hash} Nonce:{nonce}")
    return "OK"

if __name__ == "__main__":
    app.run()
