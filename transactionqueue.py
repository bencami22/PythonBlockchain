from flask import Flask, request
from flask import render_template

app = Flask(__name__)

@app.route('/')
def index():
    return "OK"

@app.route('/tx', methods=['POST'])
def transaction():
  if request.method == 'POST':
    new_tx = request.get_json()
    print(f"""New transaction
            FROM: {new_tx['from']}
            TO: {new_tx['to']}
            AMOUNT: {new_tx['amount']}\n
            """)

    return "OK"

if __name__ == "__main__":
    app.run()
