"""
AI 服务层 — 能力路由 + Mock 推理引擎

多能力路由：ABILITIES 字典映射 task_type → 处理函数
新增能力只需加一行配置，无需改 ViewSet 代码。
"""
import time
import random
import requests
from django.conf import settings
from django.utils import timezone

# ── 能力注册表 ────────────────────────────────────────────
# 格式: { task_type: {name, fn, input_key, description} }
# 新增能力 → 在这里加一行 + 写处理函数即可

ABILITIES = {
    'text_summary': {
        'name': '文本摘要',
        'fn': 'do_summarize',
        'input_key': 'text_input',
        'description': '提取长文本核心要点，生成精炼摘要',
    },
    'text_generation': {
        'name': '文本生成',
        'fn': 'do_text_generate',
        'input_key': 'text_input',
        'description': '根据提示词生成创意文本内容',
    },
    'image_classify': {
        'name': '图像识别',
        'fn': 'do_image_classify',
        'input_key': 'image',
        'description': '识别图片内容，返回分类标签与置信度',
    },
    'image_generate': {
        'name': '图像生成',
        'fn': 'do_image_generate',
        'input_key': 'text_input',
        'description': '根据文本描述生成图像',
    },
    'code_generate': {
        'name': '代码生成',
        'fn': 'do_code_generate',
        'input_key': 'text_input',
        'description': '根据需求描述生成代码片段',
    },
}


def get_abilities_list():
    """返回前端可用的能力列表"""
    return [
        {'key': k, 'name': v['name'], 'description': v['description']}
        for k, v in ABILITIES.items()
    ]


# ── 推理引擎 ──────────────────────────────────────────────

def run_inference(task) -> dict:
    """
    根据 task_type 路由到对应处理函数。
    优先调用外部推理服务，失败则降级到 Mock。
    """
    ability = ABILITIES.get(task.task_type)
    if not ability:
        raise ValueError(f'不支持的任务类型: {task.task_type}')

    handler_name = ability['fn']
    handler = globals().get(handler_name)
    if not handler:
        raise ValueError(f'处理函数未实现: {handler_name}')

    # 尝试调用真实推理服务
    try:
        result = _call_inference_service(task)
        if result:
            return result
    except Exception as e:
        # 降级到 Mock（面试话术：生产环境会配置告警，Mock 只是兜底）
        pass

    # Mock 降级
    return handler(task)


def _call_inference_service(task) -> dict | None:
    """调用边缘推理服务 (edge-inference FastAPI :8080)"""
    url = settings.AI_INFERENCE_URL
    try:
        resp = requests.post(f'{url}/predict', json={
            'task_type': task.task_type,
            'text': task.text_input,
        }, timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return None


# ── Mock 处理函数 ─────────────────────────────────────────
# 面试话术：「目前用 Mock 验证工作流，算法团队产出模型后替换 _do_xxx」

def do_summarize(task):
    time.sleep(random.uniform(0.5, 1.5))
    text = task.text_input[:200]
    return {
        'summary': f'[摘要] {text[:80]}...',
        'word_count': len(task.text_input.split()) if task.text_input else 0,
        'confidence': round(random.uniform(0.85, 0.98), 4),
    }


def do_text_generate(task):
    time.sleep(random.uniform(0.8, 2.0))
    return {
        'generated_text': f'基于「{task.text_input[:50]}」的生成结果：\n'
                          f'这里是 AI 生成的创意文本内容...',
        'tokens': random.randint(50, 300),
    }


def do_image_classify(task):
    time.sleep(random.uniform(0.3, 1.0))
    labels = ['猫', '狗', '汽车', '建筑', '食物', '风景', '人物']
    top3 = random.sample(labels, min(3, len(labels)))
    return {
        'predictions': [
            {'label': lbl, 'confidence': round(random.uniform(0.7, 0.99), 4)}
            for lbl in top3
        ],
        'top_label': top3[0],
    }


def do_image_generate(task):
    time.sleep(random.uniform(1.0, 3.0))
    return {
        'prompt': task.text_input[:100],
        'image_url': 'https://via.placeholder.com/512x512?text=AI+Generated',
        'seed': random.randint(1000, 9999),
    }


def do_code_generate(task):
    time.sleep(random.uniform(0.5, 1.5))
    return {
        'language': 'python',
        'code': f'# Generated for: {task.text_input[:60]}\n'
                f'def solution():\n    """AI 生成的代码"""\n    pass\n',
        'explanation': '这是 Mock 代码生成结果',
    }
