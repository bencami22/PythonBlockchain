
"""Definition of a Block and a Transaction. Proof of work function defined."""
import hashlib
import json
from typing import List, Tuple

class Block:
    """Data structure for a block."""
    def __init__(self, data: str, previous_hash: str, index: int = None, timestamp: str = None,
                 hash_value: str = None, nonce: int = None):
        self.index = index
        self.data = data
        self.previous_hash = previous_hash
        self.timestamp = timestamp
        self.hash_value = hash_value
        self.nonce = nonce

class Transaction:
    """Data structure for a Transaction."""
    def __init__(self, from_acc: str, to_acc: str, amount: float):
        self.from_acc = from_acc
        self.to_acc = to_acc
        self.amount = amount

def proof_of_work(block: Block, nonce: int) -> Tuple[str, int]:
    """The proof of work algorithm used to sign blocks"""
    hash_digest: str = hashlib.sha256(json.dumps(block.__dict__).encode('utf-8')).hexdigest()
    print(f"hash_digest:{str(hash_digest)}")
    hash_int_format: str = ''
    for char in hash_digest:
        hash_int_format += str(ord(str(char)))
    hash_int: int = int(hash_int_format) + nonce
    if hash_int % 2 == 0:
        return (hash_digest, nonce)
    return proof_of_work(block, nonce + 1)

BLOCKCHAIN: List[Block] = []
