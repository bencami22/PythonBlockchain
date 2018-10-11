import sys
import hashlib
import datetime
import json

blockchain = []

class Block(object):
    def __init__(self, data, previous_hash):    
        self.index = None    
        self.data = data
        self.previous_hash = previous_hash
        self.timestamp = None
        self.hash = None
  
class Transaction(object):
    def __init__(self, from_acc, to_acc, amount):
        self.from_acc = from_acc
        self.to_acc = to_acc
        self.amount = amount

def proof_of_work(block, nonce):
    hash_digest = hashlib.sha256(json.dumps(block.__dict__).encode('utf-8')).hexdigest()
    print(f"hash_digest:{str(hash_digest)}")
    hash_int_format = ''
    for char in hash_digest:
        hash_int_format += str(ord(str(char)))
    hash_int = int(hash_int_format) + nonce
    if hash_int % 2 == 0:
        return (hash_digest, nonce)
    return proof_of_work(block, nonce + 1)
