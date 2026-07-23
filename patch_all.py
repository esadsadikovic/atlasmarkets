"""Patch all 5 APIs: add requestBody to decision POST endpoints (POST needs it, GET uses parameters)."""
import re, os

# Each API: (directory, prefix, symbol description for decision)
APIS = [
    ('crypto_api',     'anubis', '"Crypto symbol e.g. BTC, ETH"'),
    ('stock_api',      'viking', '"Stock ticker e.g. SPY, QQQ, AAPL"'),
    ('forex_api',      'apollo', '"Forex pair e.g. EURUSD, GBPUSD, USDJPY"'),
    ('commodities_api','pollux', '"Commodity name (XAU, XAG, WTI, NG, HG)"'),
    ('onchain_api',    'dagon',  '"ETH or BTC"'),
]

for api_dir, prefix, sym_desc in APIS:
    filepath = f'{api_dir}/main.py'
    with open(filepath) as f:
        content = f.read()

    count = 0

    # decision POST: add requestBody (no x-bazaar, no parameters needed for POST)
    # Find the openapi_extra block for decision endpoint and add requestBody after x-payment-info
    old = f'''        "x-payment-info": {{
            "price": {{"mode": "fixed", "currency": "USD", "amount": "0.150000"}},
            "protocols": [{{"x402": {{}}}}]
        }}
    }},
    responses={{402: {{"description": "Payment Required"}}}}
)
def decision(symbol: str = Query(..., description={sym_desc})):'''

    new = f'''        "x-payment-info": {{
            "price": {{"mode": "fixed", "currency": "USD", "amount": "0.150000"}},
            "protocols": [{{"x402": {{}}}}]
        }},
        "requestBody": {{
            "content": {{
                "application/json": {{
                    "schema": {{
                        "type": "object",
                        "properties": {{"symbol": {{"type": "string", "description": {sym_desc}}}}},
                        "required": ["symbol"]
                    }}
                }}
            }}
        }}
    }},
    responses={{402: {{"description": "Payment Required"}}}}
)
def decision(symbol: str = Query(..., description={sym_desc})):'''

    if old in content:
        content = content.replace(old, new, 1)
        print(f'{api_dir} decision: OK')
        count += 1
    else:
        print(f'{api_dir} decision: MISS')

    with open(filepath, 'w') as f:
        f.write(content)

    # Verify compile
    r = os.system(f'python -m py_compile {filepath}')
    if r:
        print(f'{api_dir}: COMPILE ERROR')
        break
    else:
        print(f'{api_dir}: compile OK')