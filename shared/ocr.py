"""本地 GLM-OCR 调用（走 Ollama）。

原本有四处各写了一份近乎相同的实现（reading/ocr_read.py、make-a-sentence/ocr_glm.py、
make-a-sentence/reocr_abnormal.py、writing/practice/extract.py 的 _ocr_b64），这里合并。

分两层：
  ocr_b64()   —— 底层，收 base64 图，只管调 Ollama
  ocr_image() —— 走文件路径，负责等比缩放后交给 ocr_b64

调用方各自负责解析返回文本（各题型的解析逻辑不同，不在此合并）。

提示词经验：用简单提示词，不要用结构化提示词——0.9B 的小模型会因此变笨（约 28% 出错）。
结构在 Python 里解析。
"""
import base64
import io
import json
import time
from urllib.request import Request, urlopen

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'glm-ocr:q8_0'
PROMPT = 'Transcribe all the text in this image, preserving line breaks and layout.'

# GLM-OCR 对超宽图（>1600px）会识别失败，返回占位符或空，先缩小
MAX_WIDTH = 1600


def ocr_b64(b64, prompt=PROMPT, model=MODEL, retries=3, timeout=600):
    """对一张 base64 图片调 OCR，返回识别文本；重试耗尽返回 None。"""
    body = {'model': model, 'prompt': prompt, 'images': [b64], 'stream': False}
    last_err = None
    for attempt in range(retries):
        try:
            req = Request(OLLAMA_URL, json.dumps(body).encode('utf-8'),
                          {'Content-Type': 'application/json'})
            r = urlopen(req, timeout=timeout)
            return json.loads(r.read().decode('utf-8')).get('response', '')
        except Exception as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(3)
    print(f'  OCR FAILED ({last_err})')
    return None


def to_b64(im):
    """PIL Image -> JPEG base64 字符串。"""
    buf = io.BytesIO()
    im.save(buf, format='JPEG')
    return base64.b64encode(buf.getvalue()).decode('utf-8')


def ocr_image(img_path, prompt=PROMPT, model=MODEL, retries=3,
              strip=False, timeout=600, max_width=MAX_WIDTH):
    """打开图片 → 等比缩小到 max_width 内 → OCR。返回文本；失败返回 None。

    strip=True 去掉首尾空白（reading 侧用法；组句题侧要保留原始换行）。
    """
    from PIL import Image  # 延迟导入：只在真正跑 OCR 时才需要 Pillow

    im = Image.open(img_path).convert('RGB')
    w, h = im.size
    if w > max_width:
        im = im.resize((max_width, max(1, int(h * max_width / w))))
    text = ocr_b64(to_b64(im), prompt=prompt, model=model,
                   retries=retries, timeout=timeout)
    if text is None:
        return None
    return text.strip() if strip else text
