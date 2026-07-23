"""Patch commodities_api: add requestBody to GET + x-bazaar/requestBody to decision."""
with open('commodities_api/main.py') as f:
    content = f.read()
count = 0

desc = {
    'decision': '"Commodity name (XAU, XAG, WTI, NG, HG)"',
    'signals': '"Timeframe: 15m, 1h, 4h, 1d", "example": "1h"',
    'forecast': '"Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"',
    'risk': 'properties": {}, "required": []',
    'preflight': '"Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"',
}

# 1. decision POST
old = '''        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(..., description="Commodity name (XAU, XAG, WTI, NG, HG)")):'''
new = '''        "x-payment-info": {
            "price": {"mode": "fixed", "currency": "USD", "amount": "0.150000"},
            "protocols": [{"x402": {}}]
        },
        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity name (XAU, XAG, WTI, NG, HG)"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"symbol": {"type": "string", "description": "Commodity name (XAU, XAG, WTI, NG, HG)"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(..., description="Commodity name (XAU, XAG, WTI, NG, HG)")):'''

if old in content:
    content = content.replace(old, new, 1)
    print('decision: OK')
    count += 1
else:
    print('decision: MISS')

# 2. signals GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def signals(timeframe: str = Query(..., description="Timeframe for signals'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def signals(timeframe: str = Query(..., description="Timeframe for signals'''

if old in content:
    content = content.replace(old, new, 1)
    print('signals: OK')
    count += 1
else:
    print('signals: MISS')

# 3. audit GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"decision_id": {"type": "string", "description": "UUID from /decision endpoint"}, "window": {"type": "string", "description": "Evaluation window: 1h, 4h, 24h", "example": "1h"}}, "required": ["decision_id"]},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def audit'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"decision_id": {"type": "string", "description": "UUID from /decision endpoint"}, "window": {"type": "string", "description": "Evaluation window: 1h, 4h, 24h", "example": "1h"}}, "required": ["decision_id"]},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "decision_id": {"type": "string", "description": "UUID from /decision endpoint", "example": "123e4567-e89b-12d3-a456-426614174000"},
                            "window": {"type": "string", "description": "Evaluation window (1h, 4h, 24h)", "example": "1h"}
                        },
                        "required": ["decision_id"]
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def audit'''

if old in content:
    content = content.replace(old, new, 1)
    print('audit: OK')
    count += 1
else:
    print('audit: MISS')

# 4. forecast GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast'''

if old in content:
    content = content.replace(old, new, 1)
    print('forecast: OK')
    count += 1
else:
    print('forecast: MISS')

# 5. risk GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def risk'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {"type": "object", "properties": {}, "required": []}
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def risk'''

if old in content:
    content = content.replace(old, new, 1)
    print('risk: OK')
    count += 1
else:
    print('risk: MISS')

# 6. preflight GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight'''

if old in content:
    content = content.replace(old, new, 1)
    print('preflight: OK')
    count += 1
else:
    print('preflight: MISS')

# 7. history GET
old = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}, "limit": {"type": "integer", "description": "Number of records to return", "example": 10}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def history'''
new = '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"}, "limit": {"type": "integer", "description": "Number of records to return", "example": 10}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
        "requestBody": {
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "Commodity (XAU, XAG, WTI, NG, HG)", "example": "XAU"},
                            "limit": {"type": "integer", "description": "Number of records to return", "example": 10}
                        },
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def history'''

if old in content:
    content = content.replace(old, new, 1)
    print('history: OK')
    count += 1
else:
    print('history: MISS')

with open('commodities_api/main.py', 'w') as f:
    f.write(content)
print(f'Total: {count}')