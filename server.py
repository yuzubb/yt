from flask import Flask, request, Response
import requests
import logging
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

# ロギング設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# プロキシ対象のホスト
ALLOWED_HOSTS = [
    'www.youtube.com',
    'youtube.com',
    'i.ytimg.com',
    'www.google.com',
    'googlevideo.com',
    'm.youtube.com',
    'ytimg.com'
]

def is_allowed_host(url):
    """URLが許可されたホストかチェック"""
    parsed = urlparse(url)
    hostname = parsed.hostname or ''
    return any(
        hostname == host or hostname.endswith('.' + host)
        for host in ALLOWED_HOSTS
    )

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>', methods=['GET', 'POST', 'HEAD', 'PUT', 'DELETE', 'PATCH'])
def proxy(path):
    """全てのリクエストをプロキシ"""
    
    # ヘルスチェック用エンドポイント
    if path == 'health' or path == '':
        return {'status': 'ok', 'service': 'YouTube Proxy'}, 200
    
    # リクエストURLの構築
    target_url = request.url.replace(request.host_url, 'https://www.youtube.com/')
    
    # クエリパラメータの保持
    if request.query_string:
        target_url = f"{target_url.split('?')[0]}?{request.query_string.decode()}"
    
    # ホストチェック
    if not is_allowed_host(target_url):
        logger.warning(f"Blocked request to non-YouTube host: {target_url}")
        return {'error': 'Only YouTube requests are allowed'}, 403
    
    logger.info(f"Proxying {request.method} request to: {target_url}")
    
    # ヘッダーの準備
    headers = {
        key: value for key, value in request.headers.items()
        if key.lower() not in ['host', 'connection', 'content-length']
    }
    
    # User-Agentを追加（YouTubeが要求する場合がある）
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    
    try:
        # リクエストの実行
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.get_data(),
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30,
            stream=True
        )
        
        # レスポンスヘッダーの準備
        excluded_headers = [
            'content-encoding', 
            'content-length', 
            'transfer-encoding', 
            'connection',
            'keep-alive',
            'proxy-authenticate',
            'proxy-authorization',
            'te',
            'trailers',
            'upgrade'
        ]
        
        response_headers = [
            (name, value) for name, value in resp.raw.headers.items()
            if name.lower() not in excluded_headers
        ]
        
        # レスポンスの作成
        response = Response(
            resp.iter_content(chunk_size=8192),
            status=resp.status_code,
            headers=response_headers
        )
        
        logger.info(f"Response status: {resp.status_code}")
        return response
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for URL: {target_url}")
        return {'error': 'Request timeout'}, 504
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {str(e)}")
        return {'error': f'Proxy error: {str(e)}'}, 502
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {'error': 'Internal proxy error'}, 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 3007))
    app.run(host='0.0.0.0', port=port, debug=False)
