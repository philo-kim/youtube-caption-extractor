import json

def handler(request):
    try:
        body = request.get_json()
        url = body.get('url', '')
        
        # 간단한 응답으로 테스트
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"test": "working", "url": url})
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({"error": str(e)})
        }
