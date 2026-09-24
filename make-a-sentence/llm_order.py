"""Process agent batches via DeepSeek (structured batch output) instead of subagents.

Reads data/agent_batches/batch_XXX.json, asks the LLM to output a JSON array of
{"answers":[...]} in input order, parses and writes batch_XXX_result.json.

Only processes batches whose result file is missing (resume-safe).
"""
import json
import re
import sys
import time
import argparse
from pathlib import Path
from langchain_openai import ChatOpenAI

ROOT = Path(__file__).parent
BATCHES_DIR = ROOT / 'data' / 'agent_batches'

sys.path.insert(0, str(ROOT.parent))   # 仓库根目录
from shared.config import get_secret

BASE_URL = 'https://api.deepseek.com'
API_KEY = get_secret('deepseek_api_key')   # config.json 或环境变量 DEEPSEEK_API_KEY
MODEL = 'deepseek-v4-flash'

SYSTEM = (
    '你是英文造句题解析器。给定一个 JSON 数组，每题一个对象 {"p","s","o"}：'
    'p 是提示句（上下文，不参与填空）；s 是待填句，null 表示空位，其余是固定词（含标点）；'
    'o 是待选词，被打散成单个词（顺序打乱，可能混入干扰词）。'
    '你的任务：把 o 里的词组织成正确词组、按正确顺序填入 s 的空位，输出 answers 数组。'
)


def build_prompt(questions):
    user = (
        '对下面每道题输出 {"answers":["词组1","词组2",...]}。规则：\n'
        '1. answers 长度 = s 里 null 的个数；\n'
        '2. 每个元素是填入对应空位的词组（多个词用空格连接）；\n'
        '3. 拼起来（固定词 + answers 按位置填入）应是一句语法正确的完整英文句；\n'
        '4. o 里可能有干扰词（如 none/stopped/will 等多余词），跳过它们，只选能组成正确句子的词；\n'
        '5. o 里只有占位符（如 "____"）无法组句时输出 {"answers":[]}；\n'
        '6. 严格按输入顺序，只输出一个 JSON 数组（每题一个对象），不要任何解释、不要 markdown 代码块。\n\n'
        '输入：\n' + json.dumps(questions, ensure_ascii=False) + '\n\n'
        '输出（仅 JSON 数组）：'
    )
    return user


def extract_json(text):
    """Extract the first JSON array from the LLM output."""
    text = re.sub(r'```[a-zA-Z]*', '', text).strip()
    start = text.find('[')
    end = text.rfind(']')
    if start == -1 or end == -1 or end <= start:
        return None
    return json.loads(text[start:end + 1])


def process_batch(batch_file, llm, retries=3):
    questions = json.load(open(batch_file, encoding='utf-8'))
    prompt = build_prompt(questions)
    for attempt in range(retries):
        try:
            resp = llm.invoke(prompt)
            data = extract_json(resp.content)
            if data is None:
                raise ValueError('no JSON array in output')
            if len(data) != len(questions):
                raise ValueError(f'len {len(data)} != {len(questions)}')
            return data
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', type=str, default=None, help='comma-separated batch nums (e.g. 000,002)')
    args = parser.parse_args()

    llm = ChatOpenAI(base_url=BASE_URL, api_key=API_KEY, model=MODEL, temperature=0, request_timeout=1800, max_retries=2)

    batch_files = sorted(BATCHES_DIR.glob('batch_*.json'))
    batch_files = [f for f in batch_files if 'result' not in f.name]

    if args.only:
        nums = set(args.only.split(','))
        batch_files = [f for f in batch_files if f.stem.replace('batch_', '') in nums]

    todo = [f for f in batch_files if not (BATCHES_DIR / (f.stem + '_result.json')).exists()]
    print(f'total batches {len(batch_files)}, todo {len(todo)}')

    for f in todo:
        try:
            data = process_batch(f, llm)
            out = BATCHES_DIR / (f.stem + '_result.json')
            json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False)
            print(f'{f.name} -> {len(data)} ok')
        except Exception as e:
            print(f'{f.name} FAILED: {e}')


if __name__ == '__main__':
    main()
