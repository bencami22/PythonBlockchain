import sys
import hashlib
import node
import datetime

class Block(object):
    def __init__(self, index, timestamp, data, previous_hash):
        self.index = index
        self.timestamp = datetime.datetime.now()
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.hash_block()
  
    def hash_block(self):
        sha = hashlib.sha256()
        sha.update(str(self.index) + 
            str(self.timestamp) + 
            str(self.data) + 
            str(self.previous_hash))
        return sha.hexdigest()

class Transaction(object):
    def __init__(self, from_acc, to_acc, amount):
        self.from_acc = from_acc
        self.to_acc = to_acc
        self.amount = amount
