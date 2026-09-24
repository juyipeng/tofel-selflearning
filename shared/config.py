"""统一的密钥与配置读取。

取值优先级：环境变量 > 仓库根目录的 config.json。

  config.json 不入库（见 .gitignore），模板见 config.example.json。
  首次使用：cp config.example.json config.json，再把 key 填进去。

各模块通过下面两行把仓库根目录加进 sys.path 后即可导入本模块：

  sys.path.insert(0, <仓库根目录>)
  from shared.config import get_secret, get
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT / 'config.json'

# 配置项名 -> 对应的环境变量名
ENV_MAP = {
    'deepseek_api_key': 'DEEPSEEK_API_KEY',
    'aliyun_ocr_appcode': 'ALIYUN_OCR_APPCODE',
}

_cache = None


def _load():
    """读取并缓存 config.json（不存在则视为空配置，全部走环境变量）。"""
    global _cache
    if _cache is None:
        if CONFIG_FILE.exists():
            _cache = json.loads(CONFIG_FILE.read_text(encoding='utf-8'))
        else:
            _cache = {}
    return _cache


def get_secret(name, default=None, required=True):
    """读一个密钥。环境变量优先，其次 config.json。"""
    env = ENV_MAP.get(name, name.upper())
    value = os.environ.get(env) or _load().get(name)
    if value:
        return value
    if required:
        raise RuntimeError(
            '缺少配置项 %s。\n'
            '  方式一：设置环境变量 %s\n'
            '  方式二：在 %s 里填 "%s": "你的值"\n'
            '  （没有该文件时先执行：cp config.example.json config.json）'
            % (name, env, CONFIG_FILE, name)
        )
    return default


def get(name, default=None):
    """读一个非敏感配置项（端口等）。"""
    return _load().get(name, default)


def get_port(module, default):
    """读某模块的服务端口。"""
    return int((_load().get('ports') or {}).get(module, default))
