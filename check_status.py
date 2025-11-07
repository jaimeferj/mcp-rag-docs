"""Quick status check for Qdrant server."""

import requests

response = requests.get("http://localhost:6333/collections/documents")
data = response.json()

print("✓ Qdrant Server Status:")
print(f"  Points (chunks): {data['result']['points_count']}")
print(f"  Status: {data['result']['status']}")
print(f"  Segments: {data['result']['segments_count']}")
