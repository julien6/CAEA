"""Stateless Ollama raw prompts with explicit Qwen chat template and exact tokenizer.

Every invocation is logged. No retry hides failures; malformed outputs abstain.
Memoization is optional and separated by model/context/document, never case truth.
"""
import hashlib
import json
import os
import time
import urllib.request
from pathlib import Path


class Extractor:
    def __init__(self,config,out):
        from transformers import AutoTokenizer
        self.config=config; self.out=out; self.episode=''
        self.tokenizer=AutoTokenizer.from_pretrained(config['tokenizer_path'],local_files_only=True)
        self.log=open(out/'llm_calls.jsonl','a',buffering=1)
        self.n=0; self.errors=0; self.tokens_in=0; self.tokens_out=0; self.cache={}; self.hits=0
        self.system=('Parse forensic export text into JSON. Classification rules: "Export fragment" means '
                     'kind="share"; "recorded indicator" means kind="direct"; "Routine inventory" means '
                     'kind="noise". h is the integer after H. bit follows "binary value" or "indicator is". '
                     'reliability is the stated decimal. For shares, pair is only the ID such as P2-3, '
                     'and slot is the integer after "part". target_path must be a JSON array of strings, '
                     'Omit fields absent from the source. Example: Export fragment P2-3, part 0, '
                     'contains binary value 1. Question H2. Reliability 0.85. => '
                     '{"kind":"share","h":2,"pair":"P2-3","slot":0,"bit":1,"reliability":0.85}. '
                     'For routine inventory output only {"kind":"noise"}. Return JSON, no explanation.')

        if config.get('strict_schema',False):
            self.system=self.system.replace('Omit fields absent from the source.',
                'Always include every schema field. For absent pair use an empty string, '
                'absent slot use 0 and absent path use [].')
            self.system=self.system.replace('For routine inventory output only {"kind":"noise"}.',
                'For routine inventory set kind to noise, h and bit and slot to 0, '
                'reliability to 0.85, pair to an empty string and target_path to [].')

        if config.get('document_mode')=='identity_join':
            self.system=('Extract a forensic record as JSON with ALL schema fields. Quality class S means reliability 0.85. '
                'h is the integer in Question H. identity_directory is kind share, slot 0: bit is the account digit U0->0, U1->1. '
                'audit_event is kind share, slot 1: bit is ONE MINUS the actor account digit (U0->1, U1->0). '
                'For a share, pair is the Correlation key. Split Related export path on > into target_path strings, remove final period. '
                'witness_statement is kind direct: bit=1 if the event occurred, bit=0 if it did not occur; pair="", slot=0, target_path=[]. '
                'Ordinary office mail or invoices without these record types are kind noise. For noise use h=0, bit=0, reliability=0.85, '
                'pair="", slot=0, target_path=[]. Never decide whether a single share proves the hypothesis. Return JSON only.')

    def __call__(self,node,agent,version):
        text=node['text']; eid=node['meta']['path'][-1]
        key=hashlib.sha256((text+json.dumps(self.config,sort_keys=True)).encode()).hexdigest()
        if self.config.get('cache',False) and key in self.cache:
            self.hits+=1
            self.log.write(json.dumps({'episode':self.episode,'agent':agent,'version':version,
                                       'eid':eid,'cache_hit':key})+'\n')
            return self.cache[key]
        prompt=self.tokenizer.apply_chat_template([{'role':'system','content':self.system},
                         {'role':'user','content':text}],tokenize=False,add_generation_prompt=True)
        token_ids=self.tokenizer.encode(prompt,add_special_tokens=False)
        limit=self.config['context']; reserve=self.config.get('output_tokens',160)
        if len(token_ids)+reserve>limit:
            self.errors+=1
            self.log.write(json.dumps({'episode':self.episode,'eid':eid,'error':'context_overflow',
                                       'input_tokens':len(token_ids),'reserve':reserve,'context':limit})+'\n')
            return None
        req={'model':self.config['model'],'prompt':prompt,'raw':True,'stream':False,
             'format':{'type':'object','properties':{
                 'kind':{'type':'string','enum':['noise','direct','share']},
                 'h':{'type':'integer'},'bit':{'type':'integer','enum':[0,1]},
                 'reliability':{'type':'number'},'pair':{'type':'string'},
                 'slot':{'type':'integer','enum':[0,1]},
                 'target_path':{'type':'array','items':{'type':'string'}}},
                 'required':['kind'],'additionalProperties':False},'options':{'num_ctx':limit,'num_predict':reserve,'temperature':0,
                                       'seed':self.config.get('seed',42)},'keep_alive':'15m'}
        if self.config.get('strict_schema',False):
            req['format']['required']=list(req['format']['properties'])
        started=time.time(); response={}; error=None; parsed=None
        try:
            request=urllib.request.Request('http://'+os.environ.get('OLLAMA_HOST','127.0.0.1:18543')+'/api/generate',
                         data=json.dumps(req).encode(),headers={'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=180) as r: response=json.load(r)
            # Raw template avoids hidden system tokens. Treat unexpected truncation as failure.
            if abs(response.get('prompt_eval_count',0)-len(token_ids))>2:
                raise ValueError('token count mismatch')
            raw=json.loads(response['response'])
            kind=raw.get('kind')
            if kind not in ('noise','direct','share'): raise ValueError('invalid kind')
            parsed={'eid':eid,'kind':kind}
            if kind!='noise':
                h=raw['h']; bit=raw['bit']; rel=raw['reliability']
                if type(h)!=int or not 0<=h<4 or type(bit)!=int or bit not in (0,1):
                    raise ValueError('invalid h/bit')
                if not isinstance(rel,(int,float)) or not .5<rel<1: raise ValueError('invalid reliability')
                parsed.update(h=h,bit=bit,reliability=rel)
                if kind=='share':
                    if raw.get('slot') not in (0,1) or not isinstance(raw.get('pair'),str):
                        raise ValueError('invalid share')
                    parsed.update(slot=raw['slot'],pair=raw['pair'])
                path=raw.get('target_path')
                if path:
                    if not isinstance(path,list) or not all(isinstance(v,str) for v in path):
                        raise ValueError('invalid path')
                    # Require literal source support for the reference.
                    if ' > '.join(path) not in text: raise ValueError('unsupported reference')
                    parsed['target_path']=path
        except Exception as exc:
            error=f'{type(exc).__name__}: {exc}'; parsed=None; self.errors+=1
        self.n+=1
        self.tokens_in+=response.get('prompt_eval_count',0)
        self.tokens_out+=response.get('eval_count',0)
        self.log.write(json.dumps({'episode':self.episode,'agent':agent,'version':version,'eid':eid,
                         'cache_key':key,'request':req,'requested_input_tokens':len(token_ids),
                         'response':response,'parsed':parsed,'error':error,'wall_seconds':time.time()-started})+'\n')
        self.cache[key]=parsed
        return parsed

    def summary(self):
        return {'calls':self.n,'errors':self.errors,'input_tokens':self.tokens_in,
                'output_tokens':self.tokens_out,'cache_hits':self.hits,'config':self.config}
