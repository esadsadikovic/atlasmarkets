"""Patch Viking stock_api: add requestBody + x-bazaar."""
with open('stock_api/main.py') as f:
    content = f.read()

# signals GET - unique function signature
old = '"x-bazaar": {\n            "schema": {\n                "properties": {\n                    "input": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}}, "required": []},\n                    "output": {"type": "object", "properties": {}}\n                },\n                "type": "object"\n            }\n        },\n    },\n    responses={402: {"description": "Payment Required"}}\n)\ndef signals(timeframe: str = Query(..., description="Timeframe for signals'
new = '"x-bazaar": {\n            "schema": {\n                "properties": {\n                    "input": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}}, "required": []},\n                    "output": {"type": "object", "properties": {}}\n                },\n                "type": "object"\n            }\n        },\n        "requestBody": {\n            "content": {\n                "application/json": {\n                    "schema": {\n                        "type": "object",\n                        "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}},\n                        "required": []\n                    }\n                }\n            }\n        }\n    },\n    responses={402: {"description": "Payment Required"}}\n)\ndef signals(timeframe: str = Query(..., description="Timeframe for signals'

if old in content:
    content = content.replace(old, new, 1)
    print('signals: OK')
else:
    print('signals: MISS')

with open('stock_api/main.py', 'w') as f:
    f.write(content)