"""本地口语刷题站服务：静态托管 app/ 目录 + /api/score（录音转写 + DeepSeek 评分）。

为什么需要服务（而非纯 HTML 直连）：
  1. 录音需要浏览器麦克风，必须在 localhost/https 下；
  2. 评分 = 录音转文字（faster-whisper）+ 按三维标准打分（DeepSeek），key 留在服务端。

用法：
  python server.py            # 默认 http://localhost:8766（端口见 config.json）
  python server.py --port 9000

依赖：faster-whisper（pytorch 环境）；DeepSeek 调用只用标准库 urllib。
"""
import argparse
import base64
import json
import os
import sys
import tempfile
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import unquote

os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')
from faster_whisper import WhisperModel

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- 配置（key 见仓库根目录 config.json，或环境变量 DEEPSEEK_API_KEY）----
sys.path.insert(0, os.path.dirname(os.path.dirname(ROOT)))   # 仓库根目录
from shared.config import get_secret, get_port

API_KEY = get_secret('deepseek_api_key')
BASE_URL = 'https://api.deepseek.com'   # 没有 /v1
DEFAULT_MODEL = 'deepseek-v4-flash'
DEFAULT_PORT = get_port('speaking', 8766)
WHISPER_MODEL = 'large-v3'   # 唯一已缓存的模型；用纯 int8 显存减半

MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.mp3': 'audio/mpeg',
    '.m4a': 'audio/mp4',
    '.wav': 'audio/wav',
    '.webm': 'audio/webm',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
}

SCORING_SYSTEM = """你是托福口语考官，按 ETS 官方《Take an Interview》评分标准，对考生的口语回答文本打分。

评分维度（满分各 5.0，三项权重均等）：
1. Delivery（对话表达）：自然的对话语速、停顿是否符合交流逻辑、是否有对话感而非背诵感；能否顺畅完成对话，是否需要对方额外费力理解语义。
2. Language Use（语言运用）：语法与词汇的准确性和丰富度，表达精准清晰，符合口语交流的自然语境，避免过度书面化与生硬表达。
3. Topic Development（内容回应）：是否直接回应问题、内容切题、阐述充分具体、逻辑连贯自然；观点类问题需有合理的理由或个人经历支撑。

注：基于文本转写评分，无法评估发音/语调/停顿，Delivery 维度得分仅供参考。

请严格按以下格式输出：
【总分】：X.X/5.0
【Delivery】：X.X/5.0 + 具体评语（含对话流畅度、交流感、节奏合理性分析）
【Language Use】：X.X/5.0 + 具体评语（含典型错误举例及地道表达亮点）
【Topic Development】：X.X/5.0 + 具体评语（含扣题度、回应充分度、观点支撑力分析）
【提分要点】：2-3 条最关键的改进建议（附修改示例句）"""


# ---- 模型（懒加载；--lite 模式下不加载）----
WHISPER = None


def load_whisper():
    global WHISPER
    print(f'loading faster-whisper {WHISPER_MODEL} (cuda/int8) ...', flush=True)
    WHISPER = WhisperModel(WHISPER_MODEL, device='cuda', compute_type='int8')
    print('whisper ready', flush=True)


def call_deepseek(messages, model=DEFAULT_MODEL, temperature=0.3, retries=5):
    body = {'model': model, 'messages': messages, 'stream': False, 'temperature': temperature}
    payload = json.dumps(body).encode('utf-8')
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(BASE_URL + '/chat/completions', payload, {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + API_KEY,
            })
            data = json.loads(urlopen(req, timeout=600).read().decode('utf-8'))
            return data['choices'][0]['message']['content']
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(2 ** (attempt + 1))
    raise last_err


def transcribe(audio_bytes: bytes, mime: str = 'audio/webm') -> str:
    """把录音字节转成文字。"""
    ext = '.mp4' if ('mp4' in mime or 'aac' in mime or 'm4a' in mime) else '.webm'
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as f:
        f.write(audio_bytes)
        tmp = f.name
    try:
        segs, _ = WHISPER.transcribe(tmp, language='en', vad_filter=True)
        return ' '.join(s.text.strip() for s in segs)
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass


class Handler(BaseHTTPRequestHandler):
    server_version = 'toefl-speaking/1.0'

    def log_message(self, fmt, *args):
        sys.stderr.write('  %s %s\n' % (self.command, self.path))

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _json(self, status, obj):
        data = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def _bytes(self, status, data, ctype):
        self.send_response(status)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(data)))
        self._cors()
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = unquote(self.path.split('?', 1)[0])
        if path == '/':
            path = '/practice.html'
        rel = path.lstrip('/')
        full = os.path.normpath(os.path.join(ROOT, rel))
        if not full.startswith(ROOT) or not os.path.isfile(full):
            self.send_error(404, 'Not Found')
            return
        ext = os.path.splitext(full)[1].lower()
        with open(full, 'rb') as f:
            content = f.read()
        self._bytes(200, content, MIME.get(ext, 'application/octet-stream'))

    def do_POST(self):
        path = self.path.split('?', 1)[0]
        if path != '/api/score':
            self.send_error(404, 'Not Found')
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self._json(400, {'error': 'bad request: %s' % e})
            return

        audio_b64 = payload.get('audio_b64')
        question = payload.get('question', '')
        mime = payload.get('mime', 'audio/webm')
        if not audio_b64:
            self._json(400, {'error': 'missing audio_b64'})
            return

        try:
            audio_bytes = base64.b64decode(audio_b64)
        except Exception:
            self._json(400, {'error': 'bad base64'})
            return

        if WHISPER is None:
            self._json(503, {'error': '当前为轻量模式，未加载评分功能；请用完整模式（去掉 --lite）启动'})
            return

        try:
            transcript = transcribe(audio_bytes, mime)
        except Exception as e:
            self._json(500, {'error': '转写失败: %s' % e})
            return

        if not transcript.strip():
            self._json(200, {'transcript': '', 'score': '（未识别到有效语音，请重录）'})
            return

        messages = [
            {'role': 'system', 'content': SCORING_SYSTEM},
            {'role': 'user', 'content': f'题目：{question}\n\n考生回答（转写文本）：\n{transcript}'},
        ]
        try:
            score = call_deepseek(messages)
        except Exception as e:
            self._json(502, {'error': 'DeepSeek 调用失败: %s' % e})
            return

        self._json(200, {'transcript': transcript, 'score': score})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=DEFAULT_PORT)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--lite', action='store_true',
                    help='轻量模式：不加载 whisper 模型，禁用评分（仅跟读/录音回放，无需 GPU）')
    args = ap.parse_args()

    if args.lite:
        print('轻量模式：不加载 whisper 模型，评分功能不可用', flush=True)
    else:
        load_whisper()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    print('=' * 56)
    print('口语刷题站已启动' + ('（轻量模式）' if args.lite else ''))
    print('请打开以下网址开始练习：')
    print('   http://%s:%d/practice.html' % (args.host, args.port))
    if args.lite:
        print('   评分功能已禁用；跟读 / 录音回放可用')
    print('按 Ctrl+C 退出')
    print('=' * 56)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
