from flask import Flask, request, Response
import requests
import logging
from urllib.parse import urlparse
import socket

app = Flask(__name__)

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# プロキシ対象のホスト
ALLOWED_HOSTS = [
    'www.youtube.com',
    'youtube.com',
    'i.ytimg.com',
    'www.google.com',
    'googlevideo.com',
    'm.youtube.com',
    'ytimg.com',
    'yt3.ggpht.com',
    'yt3.googleusercontent.com'
]

def is_allowed_host(hostname):
    """ホストが許可されているかチェック"""
    if not hostname:
        return False
    return any(
        hostname == host or hostname.endswith('.' + host)
        for host in ALLOWED_HOSTS
    )

@app.route('/health')
@app.route('/')
def health():
    """ヘルスチェックエンドポイント"""
    return {
        'status': 'ok', 
        'service': 'YouTube Proxy',
        'version': '1.0'
    }, 200

@app.route('/<path:url>', methods=['GET', 'POST', 'HEAD', 'CONNECT'])
def proxy_request(url):
    """HTTPプロキシとして動作"""
    
    # CONNECTメソッド（HTTPS tunnel）の処理
    if request.method == 'CONNECT':
        logger.info(f"CONNECT request to: {url}")
        # CONNECTは通常のHTTPプロキシで必要だがyt-dlpでは使わない
        return Response('CONNECT not supported in this proxy', status=405)
    
    # URLの解析
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    # ホストチェック
    if not is_allowed_host(hostname):
        logger.warning(f"Blocked request to non-YouTube host: {hostname}")
        return {'error': 'Only YouTube requests are allowed'}, 403
    
    logger.info(f"Proxying {request.method} request to: {url}")
    
    # ヘッダーの準備
    headers = {}
    for key, value in request.headers.items():
        if key.lower() not in ['host', 'connection', 'content-length', 
                               'transfer-encoding', 'proxy-connection']:
            headers[key] = value
    
    # User-Agentの設定
    if 'User-Agent' not in headers:
        headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    # Accept-Encodingの設定
    if 'Accept-Encoding' not in headers:
        headers['Accept-Encoding'] = 'gzip, deflate'
    
    try:
        # リクエストの実行
        resp = requests.request(
            method=request.method,
            url=url,
            headers=headers,
            data=request.get_data() if request.method in ['POST', 'PUT', 'PATCH'] else None,
            allow_redirects=False,
            timeout=30,
            stream=True,
            verify=True
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
        
        response_headers = {}
        for name, value in resp.headers.items():
            if name.lower() not in excluded_headers:
                response_headers[name] = value
        
        # レスポンスの作成
        def generate():
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    yield chunk
        
        logger.info(f"Response status: {resp.status_code} for {url}")
        
        return Response(
            generate(),
            status=resp.status_code,
            headers=response_headers,
            direct_passthrough=True
        )
        
    except requests.exceptions.Timeout:
        logger.error(f"Timeout for URL: {url}")
        return {'error': 'Request timeout'}, 504
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for {url}: {str(e)}")
        return {'error': f'Proxy error: {str(e)}'}, 502
        
    except Exception as e:
        logger.error(f"Unexpected error for {url}: {str(e)}")
        return {'error': 'Internal proxy error'}, 500

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 3007))
    logger.info(f"Starting YouTube Proxy Server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
