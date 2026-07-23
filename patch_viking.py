"""Patch Viking stock_api: add requestBody to all GET endpoints + x-bazaar to decision POST."""
import os

filepath = 'stock_api/main.py'
with open(filepath) as f:
    content = f.read()

patches = []

# decision POST: add x-bazaar + requestBody
patches.append((
    '''            "protocols": [{"x402": {}}]
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query(''',
    '''            "protocols": [{"x402": {}}]
        },
        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL"}}, "required": []},
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
                        "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def decision(symbol: str = Query('''
))

# signals GET
patches.append((
    '''        "x-bazaar": {
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
def signals(timeframe: str = Query(''',
    '''        "x-bazaar": {
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
def signals(timeframe: str = Query('''
))

# audit GET
patches.append((
    '''        "x-bazaar": {
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
def audit''',
    '''        "x-bazaar": {
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
))

# forecast GET
patches.append((
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast''',
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}}, "required": []},
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
                        "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def forecast'''
))

# risk GET
patches.append((
    '''        "x-bazaar": {
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
def risk''',
    '''        "x-bazaar": {
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
))

# preflight GET
patches.append((
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight(symbol: str = Query(''',
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}}, "required": []},
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
                        "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}},
                        "required": []
                    }
                }
            }
        }
    },
    responses={402: {"description": "Payment Required"}}
)
def preflight(symbol: str = Query('''
))

# history GET
patches.append((
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}, "limit": {"type": "integer", "description": "Number of records to return", "example": 10}}, "required": []},
                    "output": {"type": "object", "properties": {}}
                },
                "type": "object"
            }
        },
    },
    responses={402: {"description": "Payment Required"}}
)
def history''',
    '''        "x-bazaar": {
            "schema": {
                "properties": {
                    "input": {"type": "object", "properties": {"symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"}, "limit": {"type": "integer", "description": "Number of records to return", "example": 10}}, "required": []},
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
                            "symbol": {"type": "string", "description": "Stock ticker e.g. SPY, QQQ, AAPL", "example": "SPY"},
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
))

for old, new in patches:
    if old in content:
        content = content.replace(old, new, 1)
        name = old.split('\n')[1].strip()[:20]
        print(f'patched: {name}')
    else:
        print(f'NOT FOUND: {old[:50]}')

with open(filepath, 'w') as f:
    f.write(content)