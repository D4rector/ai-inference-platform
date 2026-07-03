import requests, json, re, os

# 从 git-credentials 读 token
creds = os.path.expanduser("~/.git-credentials")
token = None
with open(creds) as f:
    for line in f:
        m = re.search(r'https://[^:]+:([^@]+)@', line)
        if m:
            token = m.group(1)
            break

if not token:
    print("No token found")
    exit(1)

headers = {"Authorization": f"token {token}", "Content-Type": "application/json"}
data = {
    "name": "ai-inference-platform",
    "description": "生产级AI推理平台 - Django+Vue3+PG+Redis+Celery+Kafka+ES+Kibana+Ollama",
    "private": False
}
r = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
d = r.json()
if "html_url" in d:
    print(f"CREATED: {d['html_url']}")
else:
    print(f"ERROR: {d.get('message', d)}")
