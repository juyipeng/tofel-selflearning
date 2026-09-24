"""本地刷题站服务：静态托管 practice/ 目录 + /grade 代理转发 DeepSeek 打分。

为什么需要这个服务（而不是纯 HTML 直连 DeepSeek）：
  1. 浏览器直连 DeepSeek 有 CORS 限制，且 API key 会暴露在页面里；
  2. 这里 key 只留在服务端，HTML 通过同源 /grade 请求打分。

用法：
  python server.py            # 默认 http://localhost:8765（端口见 config.json）
  python server.py --port 9000

只用 Python 标准库，无第三方依赖。key 从仓库根目录 config.json 或环境变量读取。
"""
import argparse
import json
import os
import re
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.abspath(__file__))

# ---- 配置（key 见仓库根目录 config.json，或环境变量 DEEPSEEK_API_KEY）----
sys.path.insert(0, os.path.dirname(os.path.dirname(ROOT)))   # 仓库根目录
from shared.config import get_secret, get_port

API_KEY = get_secret('deepseek_api_key')
BASE_URL = 'https://api.deepseek.com'   # 没有 /v1
DEFAULT_MODEL = 'deepseek-v4-flash'
DEFAULT_PORT = get_port('writing', 8765)

RECORDS_FILE = os.path.join(ROOT, 'data', 'records.json')  # 做题记录保存在服务端同目录下
MATERIALS_FILE = os.path.join(ROOT, 'data', 'materials.json')  # 素材库
QUESTIONS_FILE = os.path.join(ROOT, 'data', 'questions.json')  # 题库（自动总结素材用）
MIME = {
    '.html': 'text/html; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
}


def call_deepseek(messages, model=DEFAULT_MODEL, temperature=0.3, retries=5):
    body = {
        'model': model,
        'messages': messages,
        'stream': False,
        'temperature': temperature,
    }
    payload = json.dumps(body).encode('utf-8')
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(
                BASE_URL + '/chat/completions',
                payload,
                {
                    'Content-Type': 'application/json',
                    'Authorization': 'Bearer ' + API_KEY,
                },
            )
            resp = urlopen(req, timeout=600)
            data = json.loads(resp.read().decode('utf-8'))
            return data['choices'][0]['message']['content']
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                # 网络/SSL/连接拒绝等偶发错误，指数退避重试（2s、4s、8s、16s）
                time.sleep(2 ** (attempt + 1))
    raise last_err


def extract_json(text):
    """从 LLM 输出里稳健地提取 JSON 数组（去掉围栏，取第一个 [ 到最后一个 ]）。"""
    text = re.sub(r'```[a-zA-Z]*', '', text).strip()
    s, e = text.find('['), text.rfind(']')
    if s == -1 or e <= s:
        return []
    try:
        return json.loads(text[s:e + 1])
    except Exception:
        return []


def extract_topics():
    """从题库提取主题关键词（只取主题词，不含原题正文，供自动总结用）。"""
    disc, email = [], []
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, encoding='utf-8') as f:
            q = json.load(f)
        for s in q.get('sets', []):
            d = s.get('discussion') or {}
            m = re.search(r'teaching a class on (.*?)\.', d.get('instruction', ''))
            if m:
                disc.append(m.group(1).strip())
            e = s.get('email') or {}
            ctx = (e.get('context') or e.get('task') or '').strip()
            if ctx:
                email.append(' '.join(ctx.split()[:8]))
    return list(dict.fromkeys(disc)), list(dict.fromkeys(email))


def build_summarize_prompt(disc, email):
    return (
        '你是托福写作素材专家。素材 = 用于支撑观点的【具体例子】，不是观点本身。'
        '例如谈到环保，可以用「种树活动」这个具体经历，或「《Silent Spring》这本书」作为例子。\n\n'
        '以下是托福写作题库里的主题（学术讨论主题 + 邮件场景主题）：\n'
        '学术讨论主题：' + (', '.join(disc) if disc else '（无）') + '\n\n'
        '邮件场景主题（截断）：' + (', '.join(email[:20]) if email else '（无）') + '\n\n'
        '请为这些主题归纳出能覆盖尽可能多题目的通用【例子素材】（约 8-12 个）。每个素材是一个具体的例子：'
        '一本书、一个活动/事件、一项研究、一个具体数据/事实、或一个具体人物，而不是泛泛的观点。\n'
        '要求：\n'
        '1. 例子的英文要具体、地道、准确，可直接写进作文。\n'
        '2. 每个素材含：中文主题名 topic、中文适用说明 note、若干角度 angles。'
        '角度 label 要贴合例子类型（书：书名/作者/一句话/详细讲/意义；活动：一句话/详细讲/意义；研究：一句话/数据/意义），英文 text。\n'
        '3. 只输出一个 JSON 数组，不要解释、不要 markdown 代码块，格式：\n'
        '[{"topic":"...","note":"...","angles":[{"label":"书名","text":"..."},{"label":"意义","text":"..."}]}]'
    )


class Handler(BaseHTTPRequestHandler):
    server_version = 'toefl-writing/1.0'

    def log_message(self, fmt, *args):  # 精简日志
        sys.stderr.write('  %s %s\n' % (self.command, self.path))

    # ---- CORS 头（同源用不到，但留作保险）----
    def _cors(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        path = unquote(self.path.split('?', 1)[0])
        if path == '/':
            path = '/practice.html'
        # 做题记录：从服务端读取
        if path == '/records':
            if os.path.exists(RECORDS_FILE):
                with open(RECORDS_FILE, encoding='utf-8') as f:
                    content = f.read()
            else:
                content = '[]'
            self._bytes(200, content.encode('utf-8'), 'application/json; charset=utf-8')
            return
        # 素材库：从服务端读取
        if path == '/materials':
            if os.path.exists(MATERIALS_FILE):
                with open(MATERIALS_FILE, encoding='utf-8') as f:
                    content = f.read()
            else:
                content = '{"materials":[]}'
            self._bytes(200, content.encode('utf-8'), 'application/json; charset=utf-8')
            return
        # 防目录穿越
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
        # 做题记录：保存到服务端 data/records.json
        if path == '/records':
            try:
                length = int(self.headers.get('Content-Length', 0))
                payload = self.rfile.read(length)
                json.loads(payload.decode('utf-8'))  # 校验是否为合法 JSON
                os.makedirs(os.path.dirname(RECORDS_FILE), exist_ok=True)
                with open(RECORDS_FILE, 'wb') as f:
                    f.write(payload)
                self._json(200, {'ok': True})
            except Exception as e:
                self._json(400, {'error': 'save failed: %s' % e})
            return
        # 素材库：保存
        if path == '/materials':
            try:
                length = int(self.headers.get('Content-Length', 0))
                payload = self.rfile.read(length)
                json.loads(payload.decode('utf-8'))
                os.makedirs(os.path.dirname(MATERIALS_FILE), exist_ok=True)
                with open(MATERIALS_FILE, 'wb') as f:
                    f.write(payload)
                self._json(200, {'ok': True})
            except Exception as e:
                self._json(400, {'error': 'save materials failed: %s' % e})
            return
        # 自动总结素材（基于题库主题，不泄露原题）
        if path == '/summarize':
            try:
                disc, email = extract_topics()
                prompt = build_summarize_prompt(disc, email)
                content = call_deepseek(
                    [{'role': 'system', 'content': '你是托福写作素材专家，只输出 JSON。'},
                     {'role': 'user', 'content': prompt}],
                    temperature=0.3)
                data = extract_json(content)
                self._json(200, {'materials': data})
            except Exception as e:
                self._json(502, {'error': '总结失败: %s' % e})
            return
        if path != '/grade':
            self.send_error(404, 'Not Found')
            return
        try:
            length = int(self.headers.get('Content-Length', 0))
            payload = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self._json(400, {'error': 'bad request: %s' % e})
            return

        messages = payload.get('messages')
        model = payload.get('model') or DEFAULT_MODEL
        temperature = payload.get('temperature', 0.3)
        if not messages:
            self._json(400, {'error': 'missing "messages"'})
            return

        try:
            content = call_deepseek(messages, model=model, temperature=temperature)
            self._json(200, {'content': content})
        except Exception as e:
            self._json(502, {'error': 'DeepSeek 调用失败: %s' % e})

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=DEFAULT_PORT)
    ap.add_argument('--host', default='127.0.0.1')
    args = ap.parse_args()

    httpd = ThreadingHTTPServer((args.host, args.port), Handler)
    base = 'http://%s:%d' % (args.host, args.port)
    print('写作刷题站：   %s/practice.html' % base)
    print('素材库：       %s/materials.html' % base)
    print('按 Ctrl+C 退出')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('\n已停止')


if __name__ == '__main__':
    main()
