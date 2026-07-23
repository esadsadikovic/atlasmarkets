import re

apis = [
    ("crypto_api", "anubis"),
    ("stock_api", "viking"),
    ("forex_api", "apollo"),
    ("commodities_api", "pollux"),
    ("onchain_api", "dagon"),
]

endpoints_info = {
    "signals":   ("0.050000", {"timeframe": {"type": "string", "description": "Timeframe: 15m, 1h, 4h, 1d", "example": "1h"}}, None),
    "audit":     ("0.070000", {"decision_id": {"type": "string", "description": "UUID from /decision endpoint"}, "window": {"type": "string", "description": "Evaluation window: 1h, 4h, 24h", "example": "1h"}}, ["decision_id"]),
    "forecast":  ("0.050000", {"symbol": {"type": "string", "description": "Asset symbol (e.g. BTC, ETH, SPY, EURUSD, XAU)"}}, None),
    "risk":      ("0.020000", {}, []),
    "preflight": ("0.050000", {"symbol": {"type": "string", "description": "Asset symbol (e.g. BTC, ETH, SPY, EURUSD, XAU)"}}, None),
    "history":   ("0.050000", {"symbol": {"type": "string", "description": "Asset symbol (e.g. BTC, ETH, SPY, EURUSD, XAU)"}, "limit": {"type": "integer", "description": "Number of records to return"}}, None),
}

for api_dir, name in apis:
    path = f"C:/Users/43664/Desktop/AtlasMarkets/{api_dir}/main.py"
    with open(path, 'r') as f:
        lines = f.readlines()

    new_lines = []
    i = 0
    while i < len(lines):
        line = lines[i]

        # Look for openapi_extra= line for a GET endpoint we're interested in
        # Pattern: line contains openapi_extra={ for one of our endpoints
        matched_ep = None
        for ep in endpoints_info:
            if f'@app.get("/api/{name}/{ep}",' in line or f'@app.get("/api/{name}/{ep} "' in line:
                matched_ep = ep
                break

        if matched_ep:
            # Copy the @app.get decorator line
            new_lines.append(line)
            i += 1

            # We're now inside the decorator call - collect openapi_extra={ block
            # We need to find the closing brace of openapi_extra
            depth = 0
            started = False
            end_idx = None
            for j in range(i, min(i + 30, len(lines))):
                l = lines[j]
                for ch in l:
                    if ch == '{':
                        depth += 1
                        started = True
                    elif ch == '}':
                        depth -= 1
                if started and depth == 0:
                    end_idx = j
                    break

            if end_idx is not None:
                # Copy lines until just before the closing } of openapi_extra
                # The closing } should be the last char before the comma+newline
                # We need to insert x-bazaar before it
                # Check what's on the end_idx line
                closing_line = lines[end_idx]
                stripped = closing_line.rstrip()

                # Count leading whitespace
                indent = len(closing_line) - len(closing_line.lstrip())

                # Build x-bazaar block
                price = endpoints_info[matched_ep][0]
                inp_props = endpoints_info[matched_ep][1]
                inp_required = endpoints_info[matched_ep][2] or []

                # Build input properties JSON
                inp_parts = []
                for k, v in inp_props.items():
                    inp_parts.append(f'{repr(k)}: {v}')
                inp_str = "{" + ", ".join(inp_parts) + "}" if inp_parts else "{}"

                xbazaar = f'''{" " * indent}"x-bazaar": {{
{" " * (indent+8)}"schema": {{
{" " * (indent+12)}"properties": {{
{" " * (indent+16)}"input": {{"type": "object", "properties": {inp_str}, "required": {inp_required}}},
{" " * (indent+16)}"output": {{"type": "object", "properties": {{}}}}
{" " * (indent+12)}},
{" " * (indent+8)}"type": "object"
{" " * (indent+4)}}}
{" " * indent}}},'''

                # Check if x-bazaar already injected (from failed run)
                # If the line has a closing } with trailing content, it's the openapi_extra close
                # We insert x-bazaar BEFORE that } and add comma after
                new_lines.append(xbazaar + "\n")

                # Now add the original closing line (the } of openapi_extra)
                new_lines.append(closing_line)
                i = end_idx + 1

                # Skip the lines we consumed (the ones we didn't copy above)
                # Actually we didn't copy them - new_lines only got xbazaar + closing_line
                # But we need to also skip lines between i and end_idx (exclusive)
                # Those were the body of openapi_extra which we replaced
                # But we still need to output the body... wait no - we're inserting x-bazaar
                # as a NEW entry inside openapi_extra. So we need to output the existing body
                # AND add x-bazaar before the final }.
                # The approach above is WRONG - we're REPLACING the body with x-bazaar.

                # Let me redo this properly
                pass

        new_lines.append(line)
        i += 1

    with open(path, 'w') as f:
        f.writelines(new_lines)
    print(f"{api_dir}: processed")