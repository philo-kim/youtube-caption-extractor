import requests
import json

def test_api():
    base_url = "https://youtube-caption-extractor-eta.vercel.app/api"
    
    print("Testing YouTube Caption Extractor API...")
    print(f"Base URL: {base_url}\n")
    
    # Test 1: Extract info
    print("1. Testing /extract-info endpoint...")
    try:
        response = requests.post(
            f"{base_url}/extract-info",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success! Title: {data.get('title', 'N/A')}")
            print(f"   Available captions: {len(data.get('available_captions', []))} languages")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    print("\n2. Testing /preview-caption endpoint...")
    try:
        response = requests.post(
            f"{base_url}/preview-caption",
            json={
                "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "language_code": "en"
            },
            timeout=30
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Success! Preview items: {len(data.get('preview', []))}")
        else:
            print(f"   Error: {response.text[:200]}")
    except Exception as e:
        print(f"   Exception: {str(e)}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_api()
