import requests, json, time

# Write test file
with open('data/test_e2e.txt', 'w') as f:
    f.write('The ImmersiveRAG framework enables local document indexing with FastEmbed and Qdrant. It supports multi-tenant semantic search.')

# Upload
with open('data/test_e2e.txt', 'rb') as f:
    r = requests.post('http://127.0.0.1:8000/admin/ingest',
        files={'file': ('test_e2e.txt', f, 'text/plain')},
        data={'tenant_id': 'default', 'collection_id': 'default', 'extraction_mode': 'local_markdown', 'embedding_mode': 'local_fastembed'})

print('Ingest:', json.dumps(r.json(), indent=2))
job_id = r.json().get('job_id')

# Poll status
for i in range(12):
    time.sleep(3)
    s = requests.get(f'http://127.0.0.1:8000/admin/ingest/{job_id}/status')
    d = s.json()
    status = d.get('status')
    msg = d.get('message', '')[:70]
    print(f'[{(i+1)*3}s] {status} | {msg}')
    if status in ('complete', 'failed'):
        break

# Check vectors
v = requests.get('http://127.0.0.1:8000/admin/debug/vectors', params={'limit': 2})
result = v.json()
print('\nVectors result:')
print(json.dumps(result, indent=2)[:800])
