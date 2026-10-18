import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from caea.llm import Extractor


class FakeTokenizer:
    def apply_chat_template(self,messages,**kw):return 'bounded prompt'
    def encode(self,prompt,**kw):return [1]*40


class ExtractionContract(unittest.TestCase):
    def build(self,root,context=256):
        with patch('transformers.AutoTokenizer.from_pretrained',return_value=FakeTokenizer()):
            return Extractor({'model':'dummy','tokenizer_path':'dummy','context':context,'output_tokens':80},Path(root))

    def node(self):return {'text':'Artifact H0. Companion root > D0.', 'meta':{'path':['root','D0','D0/N0']}}

    def response(self,payload,count=40):
        mocked=MagicMock()
        mocked.__enter__.return_value.read.return_value=json.dumps({'prompt_eval_count':count,
                      'eval_count':20,'response':json.dumps(payload)}).encode()
        return mocked

    def test_overflow_refuses_without_http(self):
        with tempfile.TemporaryDirectory() as root:
            e=self.build(root,100)
            with patch('urllib.request.urlopen') as http:
                self.assertIsNone(e(self.node(),0,0));http.assert_not_called()
            self.assertIn('context_overflow',Path(root,'llm_calls.jsonl').read_text())
            e.log.close()

    def test_token_mismatch_and_unsupported_reference_abstain(self):
        payload={'kind':'direct','h':0,'bit':1,'reliability':.85,'target_path':['root','D9']}
        with tempfile.TemporaryDirectory() as root:
            e=self.build(root)
            with patch('urllib.request.urlopen',return_value=self.response(payload,30)):
                self.assertIsNone(e(self.node(),0,0))
            with patch('urllib.request.urlopen',return_value=self.response(payload)):
                self.assertIsNone(e(self.node(),0,1))
            log=Path(root,'llm_calls.jsonl').read_text()
            self.assertIn('token count mismatch',log);self.assertIn('unsupported reference',log)
            e.log.close()

    def test_provenance_is_bound_to_acquired_document(self):
        with tempfile.TemporaryDirectory() as root:
            e=self.build(root)
            payload={'kind':'direct','h':0,'bit':1,'reliability':.85,'eid':'invented'}
            with patch('urllib.request.urlopen',return_value=self.response(payload)):
                parsed=e(self.node(),0,0)
            self.assertEqual(parsed['eid'],'D0/N0')
            self.assertEqual(parsed['bit'],1)
            e.log.close()
