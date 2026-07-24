"""
test_college_search_api.py — Tests the REST API for college autocomplete.
"""
import requests

queries = ['sri', 'tirupati', 'IIT', 'SVCE', 'VIT', 'Prakasam', 'Andhra Pradesh']
base_url = "http://localhost:8000/api/colleges/search"

print("==========================================================================")
print("             TESTING REST API /api/colleges/search                        ")
print("==========================================================================")

for q in queries:
    res = requests.get(f"{base_url}?q={q}")
    data = res.json()
    print(f"\nQuery: '{q}' | Status: {res.status_code} | Count: {len(data)}")
    if data:
        print(f"Top Result: {data[0]['college_name']} ({data[0].get('district') or ''}, {data[0]['state']})")
    else:
        print("No results returned!")
