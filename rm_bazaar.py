"""Remove x-bazaar blocks from all 5 APIs using re.sub."""
import re

for api in ['crypto_api', 'stock_api', 'forex_api', 'commodities_api', 'onchain_api']:
    filepath = f'{api}/main.py'
    with open(filepath) as f:
        content = f.read()

    # Remove x-bazaar: { ... }, pattern (including trailing comma)
    # The block is at the openapi_extra level, preceded by }, and possibly newline+indent
    before = content
    for _ in range(10):  # safety limit
        new_content, n = re.subn(
            r'\n\s+"x-bazaar": \{\n(?:.*?\n)*?(?=\n\s+\}\,)',
            '\n',
            before,
            flags=re.DOTALL
        )
        if n == 0:
            break
        before = new_content

    # Also remove any orphaned commas left after removal
    # Pattern: ,\n\n        }  becomes just }\n\n
    new_content = re.sub(r',\n(\n\s+\})', r'\n\1', new_content)

    count = content.count('"x-bazaar"')
    with open(filepath, 'w') as f:
        f.write(new_content)
    print(f'{api}: removed {count} x-bazaar line(s)')