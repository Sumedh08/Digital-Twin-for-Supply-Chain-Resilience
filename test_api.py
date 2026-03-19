"""Full CarbonShip API verification test"""
import urllib.request, json, sys

API = 'http://127.0.0.1:8000'
passed = 0
failed = 0

def test_get(ep, name):
    global passed, failed
    try:
        r = urllib.request.urlopen(f'{API}{ep}', timeout=15)
        data = json.loads(r.read())
        print(f'  ✅ GET {name}')
        passed += 1
        return data
    except Exception as e:
        print(f'  ❌ GET {name}: {str(e)[:60]}')
        failed += 1
        return None

def test_post(ep, name, body):
    global passed, failed
    try:
        req = urllib.request.Request(f'{API}{ep}', 
            data=json.dumps(body).encode(),
            headers={'Content-Type': 'application/json'})
        r = urllib.request.urlopen(req, timeout=15)
        data = json.loads(r.read())
        print(f'  ✅ POST {name}')
        passed += 1
        return data
    except Exception as e:
        print(f'  ❌ POST {name}: {str(e)[:60]}')
        failed += 1
        return None

print("=== ETS Price ===")
ets = test_get('/ets/live-price', 'ETS Price')
if ets: print(f'     Price: €{ets["price"]["current_eur"]}')

print("\n=== Calculator Reference Data ===")
test_get('/cbam/products', 'Products')
test_get('/cbam/routes', 'Routes')
test_get('/cbam/countries', 'Countries')
test_get('/cbam/ship-types', 'Ship Types')

print("\n=== CBAM Calculation ===")
calc = test_post('/cbam/calculate', 'Calculate', {
    'product_type': 'steel_hot_rolled', 'weight_tonnes': 100,
    'route': 'INMUN_NLRTM_SUEZ', 'origin_country': 'india',
    'ship_type': 'container_ship'
})
if calc:
    e = calc['data']['emissions']
    t = calc['data']['cbam_tax']
    print(f'     Scope 1: {e["manufacturing_co2"]}t | Scope 2: {e["electricity_co2"]}t | Scope 3: {e["transport_co2"]}t')
    print(f'     Total: {e["total_co2"]}t | CBAM Tax: €{t["eur"]}')

print("\n=== Route Analyst ===")
route = test_get('/route/analyze?route_code=INMUN_NLRTM_SUEZ', 'Route Analysis')
if route: print(f'     Risk: {route.get("risk_score","?")}')

print("\n=== AI Legal Advisor ===")
legal = test_post('/ai/legal', 'Legal Advisor', {'query': 'Does CBAM apply to steel?'})
if legal: print(f'     Response: {legal.get("answer","?")[:80]}...')

print("\n=== Blockchain ===")
chain = test_get('/blockchain/chain', 'Get Chain')
if chain: print(f'     Blocks: {chain["chain_length"]}, Valid: {chain["is_valid"]}')

block = test_post('/blockchain/execute', 'Execute Contract', {
    'shipment_id': 'VERIFY-001', 'exporter': 'Test',
    'product_type': 'steel_hot_rolled', 'weight_tonnes': 100,
    'origin_port': 'Mundra', 'destination_port': 'Rotterdam',
    'distance_km': 11265, 'transport_mode': 'container_ship'
})
if block: print(f'     Hash: {block["receipt"]["block_hash"][:20]}...')

print(f'\n=== RESULTS: {passed} passed, {failed} failed ===')
