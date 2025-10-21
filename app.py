from flask import Flask, request, jsonify
import redis
import secrets
import json
import os
from dataclasses import dataclass
from typing import Literal
import time

app = Flask(__name__)

# Конфигурация из переменных окружения
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6380'))
TTL = int(os.environ.get('TTL', '300'))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
    db=0
)

@dataclass
class BeaverShare:
    a: int
    b: int
    c: int

class BeaverTTP:
    def __init__(self, redis_client: redis.Redis, ttl: int = TTL):
        self.redis = redis_client
        self.ttl = ttl
    
    def _triple_key(self, session_id: str, triple_id: int) -> str:
        return f"triple:{session_id}:{triple_id}"
    
    def _request_key(self, session_id: str, triple_id: int, party_id: int) -> str:
        return f"request:{session_id}:{triple_id}:{party_id}"
    
    def _generate_random_triple(self, ring: Literal["Z2^64", "Z2"]) -> tuple[BeaverShare, BeaverShare]:
        if ring == "Z2^64":
            modulus = 2**64
        elif ring == "Z2":
            modulus = 2
        else:
            raise ValueError(f"Invalid ring: {ring}")
        
        a = secrets.randbelow(modulus)
        b = secrets.randbelow(modulus)
        c = (a * b) % modulus
        
        a0 = secrets.randbelow(modulus)
        a1 = (a - a0) % modulus
        
        b0 = secrets.randbelow(modulus)
        b1 = (b - b0) % modulus
        
        c0 = secrets.randbelow(modulus)
        c1 = (c - c0) % modulus
        
        share0 = BeaverShare(a=a0, b=b0, c=c0)
        share1 = BeaverShare(a=a1, b=b1, c=c1)
        
        return share0, share1
    
    def get_share(self, session_id: str, triple_id: int, party_id: int, ring: str) -> BeaverShare:
        if party_id not in [0, 1]:
            raise ValueError(f"party_id must be 0 or 1, got {party_id}")

        request_key = self._request_key(session_id, triple_id, party_id)
        if not self.redis.set(request_key, "1", nx=True, ex=self.ttl):
            raise PermissionError(f"DOUBLE_REQUEST: party {party_id} already requested triple {triple_id}")

        triple_key = self._triple_key(session_id, triple_id)

        # Fast path: check if data is already there
        cached_data = self.redis.get(triple_key)
        if cached_data and cached_data != "generating":
            shares = json.loads(cached_data)
            share_data = shares[f"share{party_id}"]
            return BeaverShare(**share_data)
            
        # Data is not there, we need to generate it. Let's race to get the lock.
        # The lock is the triple_key itself.
        # Set a temporary placeholder value, only if the key does not exist. Expire after 10s to prevent deadlocks.
        lock_acquired = self.redis.set(triple_key, "generating", nx=True, ex=10)

        if lock_acquired:
            # We got the lock. We are responsible for generating the triple.
            share0, share1 = self._generate_random_triple(ring)
            shares = {
                "ring": ring,
                "share0": {"a": share0.a, "b": share0.b, "c": share0.c},
                "share1": {"a": share1.a, "b": share1.b, "c": share1.c}
            }
            # Atomically replace the placeholder with the actual data and final TTL.
            self.redis.setex(triple_key, self.ttl, json.dumps(shares))
            
            # Now the data is generated, we can proceed to return the share.
            share_data = shares[f"share{party_id}"]
            return BeaverShare(**share_data)
        else:
            # We didn't get the lock. Someone else is generating. We must wait.
            for _ in range(20): # Wait for up to 10 seconds
                cached_data = self.redis.get(triple_key)
                if cached_data and cached_data != "generating":
                    # The data is ready!
                    shares = json.loads(cached_data)
                    share_data = shares[f"share{party_id}"]
                    return BeaverShare(**share_data)
                time.sleep(0.5)
            
            # If we are here, the other process failed to generate the data in time.
            raise TimeoutError("Waited for triple generation, but it timed out.")

ttp = BeaverTTP(redis_client)

@app.route('/api/beaver/share', methods=['POST'])
def get_share():
    try:
        data = request.get_json()
        
        session_id = data['session_id']
        party_id = int(data['party_id'])
        triple_id = int(data['triple_id'])
        ring = data['ring']
        
        if ring not in ['Z2^64', 'Z2']:
            return jsonify({"error": "ring must be 'Z2^64' or 'Z2'"}), 400
        
        share = ttp.get_share(session_id, triple_id, party_id, ring)
        
        return jsonify({
            "session_id": session_id,
            "triple_id": triple_id,
            "party_id": party_id,
            "share": {
                "a": str(share.a),
                "b": str(share.b),
                "c": str(share.c)
            }
        }), 200
        
    except PermissionError as e:
        return jsonify({
            "error": "DOUBLE_REQUEST",
            "message": str(e)
        }), 403
        
    except KeyError as e:
        return jsonify({
            "error": "MISSING_ring",
            "message": f"Missing required ring: {e}"
        }), 400
        
    except ValueError as e:
        return jsonify({
            "error": "INVALID_VALUE",
            "message": str(e)
        }), 400
        
    except Exception as e:
        return jsonify({
            "error": "INTERNAL_ERROR",
            "message": str(e)
        }), 500

@app.route('/api/health', methods=['GET'])
def health():
    try:
        redis_client.ping()
        return jsonify({
            "status": "healthy",
            "redis": "connected"
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "redis": "disconnected",
            "error": str(e)
        }), 503

@app.route('/api/stats', methods=['GET'])
def stats():
    try:
        triple_keys = redis_client.keys("triple:*")
        request_keys = redis_client.keys("request:*")
        
        return jsonify({
            "active_triples": len(triple_keys),
            "active_requests": len(request_keys),
            "ttl_seconds": TTL,
            "note": "All data auto-expires after TTL"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8090, debug=False)