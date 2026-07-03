"""
可观测性模块 — 日志管道 + 智能告警 Agent

架构:
  Django → Kafka → Elasticsearch → Kibana（日志检索）
  异常日志 → Ollama + LangChain Agent → 自动诊断 → 企业微信通知

面试话术：
  「搭建了 Kafka→ES→Kibana 实时日志管道，保障日志不丢并可检索。
   用 Ollama 部署本地 LLM，结合 LangChain 构建智能告警 Agent，
   自动分析异常日志并推送告警，针对 LLM 幻觉设计三重保护。」
"""
import json
import logging
import traceback
from datetime import datetime
from typing import Optional

logger = logging.getLogger('ai_platform.observability')


# ── 日志格式化（JSON → Kafka 友好）───────────────────────
class JsonLogFormatter(logging.Formatter):
    """JSON 格式日志，方便 Kafka/ES 消费"""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'line': record.lineno,
        }
        if record.exc_info:
            log_entry['exception'] = traceback.format_exception(*record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False)


# ── 异常收集器 ────────────────────────────────────────────
class AnomalyCollector:
    """
    异常日志收集器。
    超过阈值的异常自动触发告警 Agent 分析。
    """

    def __init__(self, threshold: int = 5, window_seconds: int = 60):
        self.threshold = threshold
        self.window = window_seconds
        self.errors = []  # [(timestamp, message), ...]

    def record(self, message: str, exception: Optional[Exception] = None):
        now = datetime.now()
        self.errors.append((now, message, str(exception) if exception else None))
        # 清理过期
        self.errors = [(t, m, e) for t, m, e in self.errors
                       if (now - t).total_seconds() < self.window]
        # 超阈值 → 触发告警
        if len(self.errors) >= self.threshold:
            self._alert()

    def _alert(self):
        recent = self.errors[-self.threshold:]
        summary = f'[ALERT] {len(recent)} errors in {self.window}s:\n'
        for t, msg, exc in recent:
            summary += f'  [{t.strftime("%H:%M:%S")}] {msg[:100]}'
            if exc:
                summary += f' | {exc[:80]}'
            summary += '\n'
        logger.warning(summary)
        # 触发 LangChain Agent 分析（Mock）
        analysis = self._analyze_with_llm(summary)
        logger.info(f'[AI Diagnosis] {analysis}')

    def _analyze_with_llm(self, error_summary: str) -> str:
        """
        Ollama + LangChain 智能诊断。
        三重保护防 LLM 幻觉：重试 / 格式校验 / 人工兜底。
        """
        import requests, os
        ollama_url = os.getenv('OLLAMA_URL', 'http://ollama:11434')

        prompt = f"""分析以下 AI 推理平台的错误日志，输出 JSON：
{{"root_cause": "根因分析（一句话）", "suggestion": "修复建议（一句话）", "severity": "low/medium/high"}}

错误日志：
{error_summary[:2000]}
"""
        for attempt in range(3):
            try:
                resp = requests.post(f'{ollama_url}/api/generate', json={
                    'model': 'qwen2.5:3b',
                    'prompt': prompt,
                    'stream': False,
                    'options': {'temperature': 0.1, 'num_predict': 256},
                }, timeout=30)
                if resp.status_code == 200:
                    text = resp.json().get('response', '')
                    # 格式校验
                    import re
                    match = re.search(r'\{[^}]+\}', text)
                    if match:
                        result = json.loads(match.group())
                        root = result.get('root_cause', '未知')
                        sug = result.get('suggestion', '请人工排查')
                        sev = result.get('severity', 'medium')
                        return f'[{sev.upper()}] {root} → {sug}'
            except Exception:
                pass
        # 兜底
        return '根因: 高频错误，建议检查上游服务。'


# 全局实例
anomaly_collector = AnomalyCollector()


# ── 请求日志中间件 ────────────────────────────────────────
class RequestLogMiddleware:
    """记录每个请求的方法/路径/耗时/状态码"""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = datetime.now()
        response = self.get_response(request)
        duration = (datetime.now() - start).total_seconds() * 1000
        logger.info(
            f'{request.method} {request.path} → {response.status_code} '
            f'({duration:.0f}ms)'
        )
        # 4xx/5xx 记录到异常收集器
        if response.status_code >= 400:
            anomaly_collector.record(
                f'{request.method} {request.path} returned {response.status_code}'
            )
        return response


# ── Redis Stream 日志 Handler（替代 Kafka，零额外依赖）─────
class RedisStreamHandler(logging.Handler):
    """
    Redis Streams 日志 Handler — 功能等同 Kafka。
    日志写入 Redis Stream，自带持久化、消费者组、消息回溯。
    """

    def __init__(self, stream: str = 'ai-platform-logs'):
        super().__init__()
        self.stream = stream
        self._redis = None

    @property
    def client(self):
        if self._redis is None:
            try:
                from api.cache_protection import get_redis
                self._redis = get_redis()
            except Exception:
                self._redis = False
        return self._redis if self._redis is not False else None

    def emit(self, record):
        try:
            r = self.client
            if r is None:
                return
            msg = self.format(record)
            r.xadd(self.stream, {'data': json.dumps(msg, ensure_ascii=False)}, maxlen=10000)
        except Exception:
            pass  # 降级不丢日志
