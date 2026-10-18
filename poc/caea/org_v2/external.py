"""Public M57 documentation tasks; no claim to disk-image or judicial validation."""
import json,re,unicodedata,hashlib
from pathlib import Path
from .model import digest


def normalize(text):
    text=unicodedata.normalize('NFKC',text).replace('\xad','')
    return re.sub(r'\s+',' ',text).strip()


# Direct questions cite a single fact; join questions require two distinct source facts.
# The required witness set defines an audit rubric, not an assertion that no alternative proof exists.
TASKS=[
('dev1','When was report 001 written?', [('detectivereport1.pdf',0,'09 December 2009')]),
('dev2','Who called police in report 001?', [('detectivereport1.pdf',0,'Aaron Greene')]),
('dev3','Who was named as seller in report 001?', [('detectivereport1.pdf',0,'Terry Johnson')]),
('dev4','At what time was report 001 written?', [('detectivereport1.pdf',0,'11:30 AM')]),
('test01','Which company was believed to own the computer in report 002?', [('detectivereport2.pdf',0,'M57 Patents')]),
('test02','Who was the user mentioned without surname in report 002?', [('detectivereport2.pdf',0,'named Jo')]),
('test03','Who was identified as company owner in report 002?', [('detectivereport2.pdf',0,'Pat McGoo')]),
('test04','At what time was report 002 written?', [('detectivereport2.pdf',0,'09:30 AM')]),
('test05','Which detectives met the company owner in report 003?', [('detectivereport3.pdf',0,'Friday and Gannon')]),
('test06','What did the owner want before authorizing search in report 003?', [('detectivereport3.pdf',0,'speak with a lawyer')]),
('test07','At what time was report 004 written?', [('detectivereport4.pdf',0,'5:00 PM')]),
('test08','Which device did report 004 request authority to seize?', [('detectivereport4.pdf',0,'USB thumb drive')]),
('test09','Connect the owner identified in report 002 to the meeting in report 003.', [('detectivereport2.pdf',0,'Pat McGoo'),('detectivereport3.pdf',0,'met with McGoo')]),
('test10','Connect the unnamed-surname user in report 002 to the full name targeted by the warrant.', [('detectivereport2.pdf',0,'named Jo'),('m57-affidavit-warrant-final.pdf',1,'Jo Smith')]),
('test11','Connect the device seizure request in report 004 to the warrant property list.', [('detectivereport4.pdf',0,'USB thumb drive'),('m57-affidavit-warrant-final.pdf',1,"All USB thumb drives in Jo Smith's possession")]),
('test12','Compare the reported suspicion of theft with the description of purchase in the affidavit.', [('detectivereport3.pdf',0,'probably stolen'),('m57-affidavit-warrant-final.pdf',2,'purchased it from Terry Johnson')]),
('test13','Connect the possible original owner in report 002 to the company address in the warrant.', [('detectivereport2.pdf',0,'M57 Patents'),('m57-affidavit-warrant-final.pdf',0,"123 Old Fisherman's Drive")]),
('test14','Connect the seller named in the affidavit to that employee\'s electronic identity in the scenario slides.', [('m57-affidavit-warrant-final.pdf',2,'Terry Johnson'),('M57-Patents-Illegal.pdf',5,'terry@m57.biz')]),
('test15','Connect the warrant target\'s full name to the corresponding scenario email identity.', [('m57-affidavit-warrant-final.pdf',1,'Jo Smith'),('M57-Patents-Illegal.pdf',5,'jo@m57.biz')]),
('test16','Connect the company owner identified in report 002 to the president\'s scenario email identity.', [('detectivereport2.pdf',0,'Pat McGoo'),('M57-Patents-Illegal.pdf',5,'pat@m57.biz')]),
]


def prepare(root,output):
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((root/'manifest.json').read_text());pages={m['name']:[normalize(t) for t in json.loads((root/(m['name']+'.json')).read_text())] for m in manifest if 'error' not in m}
    # Hyphen variants are normalized for deterministic witness checks only.
    def canon(s):return re.sub('[‐‑–−]','-',normalize(s)).lower()
    audits=[]
    for tid,question,witnesses in TASKS:
        supports=[];answers=[];proof=[]
        for name,page,span in witnesses:
            text=pages[name][page]
            needle=canon(span);hay=canon(text)
            if needle not in hay:raise ValueError((tid,name,page,span,'witness not present'))
            start=hay.index(needle);proof.append({'file':name,'page':page+1,'quote':span,'normalized_offset':start,'text_sha256':digest(text),'pdf_sha256':next(m['sha256'] for m in manifest if m['name']==name)})
            supports.append(f'{name}/page-{page+1}');answers.append(span)
        nodes={'root':{'meta':{'type':'root','size':0,'topic':None,'path':['root']},'children':[]}}
        # Each original PDF is an access container, pages its artifacts. This is an explicitly constructed access layout.
        for name,texts in pages.items():
            nodes['root']['children'].append(name)
            nodes[name]={'meta':{'type':'device','size':0,'topic':None,'path':['root',name],'filename':name},'children':[]}
            for idx,text in enumerate(texts):
                nid=f'{name}/page-{idx+1}';nodes[name]['children'].append(nid)
                nodes[nid]={'meta':{'type':'doc','size':max(1,min(3,(len(text)+1499)//1500)),'topic':None,'path':['root',name,nid],'filename':name,'page':idx+1},'children':[],'text':text,'record':{'eid':nid,'kind':'external','quotes':[],'mentions':[]}}
        case={'schema':2,'external':True,'seed':int(re.sub(r'\D','',tid)),'k':1,'nodes':nodes,'question':question,'task_id':tid,'support_sets':[supports],'answer':answers,'provenance_group':'M57-Patents-single-scenario','witnesses':proof}
        case['sha256']=digest(case);(output/(tid+'.json')).write_text(json.dumps(case,indent=2))
        audits.append({'id':tid,'split':'development' if tid.startswith('dev') else 'test','question':question,'support_sets':[supports],'witnesses':proof,'case_sha256':case['sha256']})
    (output/'annotation_audit.json').write_text(json.dumps({'tasks':audits,'all_spans_verified':True,'human_validation':False,'unit':'single external scenario; questions are dependent','metric':'required witness-set acquisition coverage; not binary-channel entropy'},indent=2))
    return audits
