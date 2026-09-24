"""统一入口：一个命令启动任意刷题模块。

用法：
  python start.py                     # 列出所有模块
  python start.py writing             # 写作刷题站 + 素材库（起服务）
  python start.py speaking            # 口语刷题站（起服务，需 faster-whisper）
  python start.py speaking --lite     # 口语轻量模式：不加载模型，仅跟读/录音回放
  python start.py reading             # 阅读刷题页（自包含，直接开浏览器）
  python start.py flashcards          # 词汇闪卡（自包含）
  python start.py listening           # 听力刷题页（自包含）
  python start.py sentence            # 组句练习（自包含）

  python start.py writing --port 9000 # 临时换端口

端口默认值来自根目录 config.json 的 ports 段；
speaking/writing 需要的 Python 解释器可在 config.json 的 python 段指定
（例如口语要在装了 faster-whisper 的 conda 环境里跑）。
"""
import argparse
import json
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from shared.config import get_port   # noqa: E402


def _configured_python(module):
    """config.json 的 python 段可给某模块指定解释器；没有就用当前解释器。"""
    cfg_file = ROOT / 'config.json'
    if cfg_file.exists():
        try:
            cfg = json.loads(cfg_file.read_text(encoding='utf-8'))
            exe = (cfg.get('python') or {}).get(module)
            if exe and Path(exe).exists():
                return exe
        except (json.JSONDecodeError, OSError):
            pass
    return sys.executable


# name -> 说明、类型
#   static: 自包含 HTML，直接用浏览器打开
#   server: 需要起本地服务
MODULES = {
    'flashcards': {
        'label': '词汇闪卡',
        'kind': 'static',
        'file': 'flashcards.html',
        'hint': '1012 词，含音标/释义/例句，支持背诵与标记',
    },
    'reading': {
        'label': '阅读刷题站',
        'kind': 'static',
        'file': 'reading/quiz.html',
        'hint': '填词题 + 阅读选择 + 句子插入，做完即对答案',
    },
    'listening': {
        'label': '听力刷题站',
        'kind': 'static',
        'file': 'listening/app/index.html',
        'hint': '音频已内嵌，单文件自包含',
    },
    'sentence': {
        'label': '组句 Build a Sentence',
        'kind': 'static',
        'file': 'writing/build-a-sentence/quiz.html',
        'hint': '写作题型之一：打散的词重组成正确句子',
    },
    'writing': {
        'label': '写作刷题站 + 素材库',
        'kind': 'server',
        'script': 'writing/practice/server.py',
        'url': 'http://127.0.0.1:{port}/practice.html',
        'also': 'http://127.0.0.1:{port}/materials.html',
        'hint': 'Write an Email / Academic Discussion，AI 打分',
    },
    'speaking': {
        'label': '口语刷题站',
        'kind': 'server',
        'script': 'speaking/app/server.py',
        'url': 'http://127.0.0.1:{port}/practice.html',
        'hint': 'Listen and Repeat + Take an Interview，按 ETS 三维评分',
    },
}


def list_modules():
    print('\n可用模块：\n')
    for name, m in MODULES.items():
        kind = '自包含网页' if m['kind'] == 'static' else '需本地服务'
        print(f'  {name:<11} {m["label"]:<18} [{kind}]  {m["hint"]}')
    print('\n用法：python start.py <模块名>  例：python start.py writing\n')


def open_static(name, m):
    path = ROOT / m['file']
    if not path.exists():
        print(f'找不到 {path}')
        print('该页面需要先用对应的 build 脚本生成，见 README。')
        return 1
    print(f'打开 {m["label"]}：{path}')
    webbrowser.open(path.as_uri())
    return 0


def run_server(name, m, argv):
    base = [_configured_python(name), str(ROOT / m['script'])]
    if '--port' in argv:                      # 命令行指定的端口优先
        port = int(argv[argv.index('--port') + 1])
        cmd = base + argv
    else:
        port = get_port(name, 8765 if name == 'writing' else 8766)
        cmd = base + argv + ['--port', str(port)]

    print(f'启动 {m["label"]} …')
    print(f'  {m["url"].format(port=port)}')
    if m.get('also'):
        print(f'  {m["also"].format(port=port)}')
    print('  按 Ctrl+C 退出\n')

    proc = subprocess.Popen(cmd)
    time.sleep(1.5)
    if proc.poll() is None:
        webbrowser.open(m['url'].format(port=port))
    try:
        return proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
        return 0


def main():
    ap = argparse.ArgumentParser(description='托福刷题站统一入口')
    ap.add_argument('module', nargs='?', help='模块名，留空则列出全部')
    args, rest = ap.parse_known_args()

    if not args.module:
        list_modules()
        return 0

    name = args.module.lower()
    if name not in MODULES:
        print(f'未知模块：{name}')
        list_modules()
        return 1

    m = MODULES[name]
    if m['kind'] == 'static':
        return open_static(name, m)
    return run_server(name, m, rest)


if __name__ == '__main__':
    sys.exit(main())
