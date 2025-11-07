"""Test script for OpenAI-compatible API."""

import requests
import json


BASE_URL = "http://localhost:8000/v1"


def test_list_models():
    """Test listing available models."""
    print("=" * 70)
    print("Test 1: List Models")
    print("=" * 70)

    response = requests.get(f"{BASE_URL}/models")
    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Models found: {len(data['data'])}")
        for model in data["data"]:
            print(f"  - {model['id']}")
        print("✓ Test passed\n")
        return True
    else:
        print(f"✗ Test failed: {response.text}\n")
        return False


def test_chat_completion():
    """Test chat completion."""
    print("=" * 70)
    print("Test 2: Chat Completion (Non-streaming)")
    print("=" * 70)

    payload = {
        "model": "rag-smart",
        "messages": [
            {"role": "user", "content": "What is a RAGSystem?"}
        ],
        "stream": False,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Model: {data['model']}")
        print(f"Response ID: {data['id']}")
        print(f"Answer: {data['choices'][0]['message']['content'][:200]}...")
        print(f"Tokens: {data['usage']['total_tokens']}")

        if data.get('rag_metadata'):
            print(f"Confidence: {data['rag_metadata'].get('confidence')}")
            print(f"Query type: {data['rag_metadata'].get('classification', {}).get('type')}")

        print("✓ Test passed\n")
        return True
    else:
        print(f"✗ Test failed: {response.text}\n")
        return False


def test_chat_completion_streaming():
    """Test streaming chat completion."""
    print("=" * 70)
    print("Test 3: Chat Completion (Streaming)")
    print("=" * 70)

    payload = {
        "model": "rag-smart",
        "messages": [
            {"role": "user", "content": "What is a RAGSystem?"}
        ],
        "stream": True,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
        stream=True,
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        print("Streaming response:")
        chunk_count = 0

        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: '):
                    data_str = line_str[6:]  # Remove 'data: ' prefix

                    if data_str == '[DONE]':
                        break

                    try:
                        chunk = json.loads(data_str)
                        delta = chunk['choices'][0]['delta']

                        if delta.get('content'):
                            print(delta['content'], end='', flush=True)
                            chunk_count += 1
                    except json.JSONDecodeError:
                        pass

        print(f"\n\nReceived {chunk_count} chunks")
        print("✓ Test passed\n")
        return True
    else:
        print(f"✗ Test failed: {response.text}\n")
        return False


def test_custom_parameters():
    """Test custom RAG parameters."""
    print("=" * 70)
    print("Test 4: Custom Parameters")
    print("=" * 70)

    payload = {
        "model": "rag-smart",
        "messages": [
            {"role": "user", "content": "show me query method"}
        ],
        "expand_detail": True,
        "top_k": 3,
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        print(f"Model: {data['model']}")
        answer = data['choices'][0]['message']['content']
        print(f"Answer length: {len(answer)} characters")
        print(f"First 200 chars: {answer[:200]}...")
        print("✓ Test passed\n")
        return True
    else:
        print(f"✗ Test failed: {response.text}\n")
        return False


def test_system_message():
    """Test system message support."""
    print("=" * 70)
    print("Test 5: System Message")
    print("=" * 70)

    payload = {
        "model": "rag-smart",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Be very concise."
            },
            {
                "role": "user",
                "content": "What is RAGSystem?"
            }
        ],
    }

    response = requests.post(
        f"{BASE_URL}/chat/completions",
        json=payload,
        headers={"Content-Type": "application/json"},
    )

    print(f"Status: {response.status_code}")

    if response.status_code == 200:
        data = response.json()
        answer = data['choices'][0]['message']['content']
        print(f"Answer: {answer[:300]}...")
        print("✓ Test passed\n")
        return True
    else:
        print(f"✗ Test failed: {response.text}\n")
        return False


def main():
    """Run all tests."""
    print("\n")
    print("=" * 70)
    print("OpenAI-Compatible API Tests")
    print("=" * 70)
    print(f"Base URL: {BASE_URL}")
    print()
    print("Make sure the RAG server is running:")
    print("  python -m rag_server.server")
    print()

    # Run tests
    results = []
    results.append(("List Models", test_list_models()))
    results.append(("Chat Completion", test_chat_completion()))
    results.append(("Streaming", test_chat_completion_streaming()))
    results.append(("Custom Parameters", test_custom_parameters()))
    results.append(("System Message", test_system_message()))

    # Summary
    print("=" * 70)
    print("Test Summary")
    print("=" * 70)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"{name}: {status}")

    print()
    print(f"Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! OpenAI API is working correctly.")
        print("\nYou can now connect Open WebUI or LibreChat:")
        print("  API Base URL: http://localhost:8000/v1")
        print("  Available models: rag-smart, rag-standard, rag-enhanced")
    else:
        print("\n⚠️  Some tests failed. Check the output above for details.")


if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("\n❌ Error: Could not connect to server.")
        print("Make sure the RAG server is running:")
        print("  python -m rag_server.server")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
