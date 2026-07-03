"""
Redis Stream → Elasticsearch 消费者
"""
import json
import time
import os
import sys
import logging
import requests
import redis

logger = logging.getLogger(__name__)

STREAM = 'ai-platform-logs'
ES_URL = 'http://elasticsearch:9200'
INDEX = 'ai-platform-logs'
CONSUMER_GROUP = 'es-indexer'
CONSUMER_NAME = 'es-consumer-1'
BATCH_SIZE = 50
FLUSH_INTERVAL = 5

REDIS_HOST = os.getenv('REDIS_HOST', 'redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))


def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def ensure_index():
    """确保 ES 索引存在"""
    try:
        resp = requests.head(f'{ES_URL}/{INDEX}', timeout=3)
        if resp.status_code == 404:
            requests.put(f'{ES_URL}/{INDEX}', json={
                'mappings': {
                    'properties': {
                        'timestamp': {'type': 'date'},
                        'level': {'type': 'keyword'},
                        'logger': {'type': 'keyword'},
                        'message': {'type': 'text'},
                        'module': {'type': 'keyword'},
                        'path': {'type': 'keyword'},
                        'status': {'type': 'integer'},
                        'duration_ms': {'type': 'float'},
                    }
                }
            }, timeout=5)
            logger.info(f'ES index {INDEX} created')
    except Exception as e:
        logger.warning(f'ES not ready: {e}')


def ensure_group(redis_client):
    """确保消费者组存在"""
    try:
        redis_client.xgroup_create(STREAM, CONSUMER_GROUP, id='0', mkstream=True)
    except Exception:
        pass  # 组已存在


def bulk_index(batch: list):
    """批量写入 ES（处理双重 JSON 编码）"""
    if not batch:
        return
    body = ''
    for entry_id, data in batch:
        raw = data.get('data', '{}')
        try:
            doc = json.loads(raw)
            if isinstance(doc, str):
                doc = json.loads(doc)  # 双重解码
        except Exception:
            doc = {'raw': raw}
        body += json.dumps({'index': {'_index': INDEX}}) + '\n'
        body += json.dumps(doc) + '\n'
    try:
        resp = requests.post(f'{ES_URL}/_bulk', data=body,
                            headers={'Content-Type': 'application/x-ndjson'}, timeout=10)
        if resp.status_code != 200:
            logger.error(f'ES bulk error: {resp.text[:200]}')
    except Exception as e:
        logger.error(f'ES bulk failed: {e}')


def run():
    """主循环 — 持续消费 Redis Stream → ES"""
    print(f'Redis→ES Consumer: {STREAM} → {ES_URL}/{INDEX}')
    sys.stdout.flush()
    time.sleep(5)  # 等 ES 就绪

    redis_client = get_redis()
    ensure_index()
    ensure_group(redis_client)

    batch = []
    last_flush = time.time()

    while True:
        try:
            # 从消费者组读取
            results = redis_client.xreadgroup(
                CONSUMER_GROUP, CONSUMER_NAME,
                {STREAM: '>'}, count=BATCH_SIZE, block=2000
            )

            for stream_name, messages in results:
                for msg_id, data in messages:
                    batch.append((msg_id, data))

            # 达到批量阈值或超时 → 写入 ES
            if len(batch) >= BATCH_SIZE or (batch and time.time() - last_flush > FLUSH_INTERVAL):
                bulk_index(batch)
                redis_client.xack(STREAM, CONSUMER_GROUP, *[m[0] for m in batch])
                batch = []
                last_flush = time.time()

        except Exception as e:
            logger.error(f'Consumer error: {e}')
            time.sleep(3)


if __name__ == '__main__':
    run()
