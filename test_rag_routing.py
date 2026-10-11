"""Fast unit checks for Knowledge Vault answer routing."""
import io
import json
import urllib.error
from unittest.mock import patch

import rag


class Response(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


FOUND = {'sources': [{'name':'notes.txt','page':1,'text':'Local evidence.',
                       'document_id':'a'*32,'score':1.0}], 'ranking':'test'}
REPLY = json.dumps({'choices':[{'message':{'content':'Answer [1]'}}]}).encode()


def run(model, expected_prefix):
    requests = []

    def open_request(request, timeout=0):
        requests.append(request)
        return Response(REPLY)

    with patch.object(rag, 'search', return_value=FOUND), \
         patch.object(rag, 'models', return_value=[{'id':'profile-a'}]), \
         patch.object(rag.urllib.request, 'urlopen', side_effect=open_request):
        result = rag.ask('What is in my notes?', model)
    assert result['answer'] == 'Answer [1]'
    assert requests[0].full_url == expected_prefix + '/v1/chat/completions'
    body = json.loads(requests[0].data)
    assert body.get('model') == model if model else 'model' not in body


run(None, rag.ACTIVE_BACKEND)
run('profile-a', rag.PROFILE_ROUTER)

requests = []
def unavailable_then_ready(request, timeout=0):
    requests.append(request)
    if len(requests) == 1:
        raise urllib.error.URLError('no active backend')
    return Response(REPLY)
with patch.object(rag, 'search', return_value=FOUND), \
     patch.object(rag.urllib.request, 'urlopen', side_effect=unavailable_then_ready):
    rag.ask('What is in my notes?')
assert [request.full_url for request in requests] == [
    rag.ACTIVE_BACKEND + '/v1/chat/completions',
    rag.PROFILE_ROUTER + '/v1/chat/completions']

print('RAG default and explicit-model routing passed.')
