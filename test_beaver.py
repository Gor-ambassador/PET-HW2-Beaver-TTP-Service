import pytest
from app import app, redis_client

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client
    redis_client.flushdb()

def test_basic_flow(client):
    resp0 = client.post('/api/beaver/share', json={
        "session_id": "test-1",
        "party_id": 0,
        "triple_id": 0,
        "ring": "Z2^64"
    })
    assert resp0.status_code == 200
    
    resp1 = client.post('/api/beaver/share', json={
        "session_id": "test-1",
        "party_id": 1,
        "triple_id": 0,
        "ring": "Z2^64"
    })
    assert resp1.status_code == 200
    
    data0 = resp0.get_json()
    data1 = resp1.get_json()
    
    modulus = 2**64
    a = (int(data0['share']['a']) + int(data1['share']['a'])) % modulus
    b = (int(data0['share']['b']) + int(data1['share']['b'])) % modulus
    c = (int(data0['share']['c']) + int(data1['share']['c'])) % modulus
    
    assert c == (a * b) % modulus

def test_double_request(client):
    client.post('/api/beaver/share', json={
        "session_id": "test-2",
        "party_id": 0,
        "triple_id": 0,
        "ring": "Z2^64"
    })
    
    resp = client.post('/api/beaver/share', json={
        "session_id": "test-2",
        "party_id": 0,
        "triple_id": 0,
        "ring": "Z2^64"
    })
    
    assert resp.status_code == 403