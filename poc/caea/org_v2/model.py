"""Local information, provenance and non-oracular dependency valuation."""
from dataclasses import dataclass,field
from copy import deepcopy
from collections import defaultdict
import hashlib,json,math,random
from caea.core import Action,PublicState,entropy,information,generate_case


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()


def posterior(records,k):
    odds=[0.0]*k; groups=defaultdict(dict);seen=set()
    for r in records:
        if r['eid'] in seen:continue
        seen.add(r['eid'])
        if r['kind']=='direct':
            odds[r['h']]+=(2*r['bit']-1)*math.log(r['reliability']/(1-r['reliability']))
        elif r['kind']=='share':groups[r['pair']][r['slot']]=r
    for g in groups.values():
        a=next(iter(g.values()));parts=a.get('parts',2)
        if set(g)!=set(range(parts)):continue
        if any(r['h']!=a['h'] or r['reliability']!=a['reliability'] or r.get('parts',2)!=parts for r in g.values()):continue
        bit=0
        for r in g.values():bit^=r['bit']
        odds[a['h']]+=(2*bit-1)*math.log(a['reliability']/(1-a['reliability']))
    return [1/(1+math.exp(-max(-60,min(60,v)))) for v in odds]


@dataclass(frozen=True)
class EpisodeConfig:
    organization:str
    policy:str='caea'
    agents:int=3
    budget:float=72
    delay:int=0
    @classmethod
    def validate(cls,config):
        obj=cls(**{k:config[k] for k in cls.__dataclass_fields__ if k in config})
        if obj.organization not in ('CENT','P2P','COAL','MKT') or obj.agents<1 or obj.budget<=0 or obj.delay<0:
            raise ValueError('invalid episode configuration')
        caps=config.get('capacities',[3]*obj.agents)
        if len(caps)!=obj.agents or any(v<=0 for v in caps):raise ValueError('invalid capacities')
        if not 0<=config.get('drop_rate',0)<=1:raise ValueError('invalid drop rate')
        return obj


@dataclass(frozen=True)
class Obligation:
    source:str
    path:tuple
    h:int
    pair:str


@dataclass
class AgentKnowledge(PublicState):
    events:set=field(default_factory=set)
    def probabilities(self):return posterior(self.records,self.k)
    def detached(self):return deepcopy(self)
    def integrate(self,event):
        if event['id'] in self.events:return False
        self.events.add(event['id']); self.version+=1
        op=event['action']['op'];node=event['action']['node']
        if op=='discover':
            self.expanded.add(node)
            self.known.update(deepcopy(event['children']))
        elif op=='load':self.opened.add(node)
        else:
            self.read.add(node)
            record=event.get('record')
            if record and record['eid'] not in {r['eid'] for r in self.records}:
                self.records.append(deepcopy(record))
        return True
    def obligations(self):
        result=[]
        for r in self.records:
            if r['kind']=='external':
                for mention in r.get('mentions',[]):
                    for nid,m in self.known.items():
                        if m['type']=='device' and mention==m.get('filename') and nid not in self.expanded:
                            result.append(Obligation(r['eid'],tuple(m['path']),0,'external:'+mention))
                continue
            if r['kind']!='share':continue
            paths=r.get('target_paths',[]) or ([r['target_path']] if r.get('target_path') else [])
            for path in paths:
                if path[-1] not in self.read:result.append(Obligation(r['eid'],tuple(path),r['h'],r['pair']))
        return result


@dataclass(frozen=True)
class Proposal:
    agent:int
    action:Action
    score:float
    version:int


@dataclass(frozen=True)
class Assignment:
    worker:int
    action:Action
    authority:int


@dataclass(frozen=True)
class Message:
    id:str
    sender:int
    recipient:int
    kind:str
    payload:dict
    due:int


class AcquisitionCore:
    """All arguments are local observations; there is no Environment reference."""
    def __init__(self,policy='caea',bonus=1.0,informed=True):
        if policy not in ('joint','myopic','caea','costpath'):raise ValueError(policy)
        self.policy,self.bonus,self.informed=policy,bonus,informed
    def score(self,a,s,reserved=()):
        meta=s.known[a.node];p=s._score_p if hasattr(s,'_score_p') else s.probabilities();topic=meta.get('topic')
        unresolved=1 if topic is None else information(p[topic],.85)/information(.5,.85)
        value=.16*unresolved/s.cost(a) if a.op=='read' else (.055 if meta['type']=='folder' else .035 if a.op=='load' else .045)
        if self.informed and a.op=='read' and topic is None:value=0
        if self.policy!='joint':
            for ob in (s._score_obligations if hasattr(s,'_score_obligations') else s.obligations()):
                if a.node not in ob.path or (self.policy=='myopic' and a.op!='read'):continue
                dist=len(ob.path)-ob.path.index(a.node)
                if self.policy=='costpath':
                    # Known steps use public costs. Unknown terminal size has prior mean 1.75.
                    left=ob.path[ob.path.index(a.node):];dist=0
                    for nid in left:
                        m=s.known.get(nid)
                        if m is None:dist+=1.75 if nid==ob.path[-1] else 1
                        elif m['type']=='doc':dist+=m['size']
                        elif m['type']=='device':dist+=int(nid not in s.opened)+int(nid not in s.expanded)
                        else:dist+=int(nid not in s.expanded)
                    denom=max(s.cost(a),dist)
                else:denom=dist+s.cost(a)
                value+=self.bonus*information(p[ob.h],.85)/denom
        for chosen in reserved:
            if topic is not None and s.known[chosen.node].get('topic')==topic:value*=.6
        return value
    def proposals(self,s,worker,capacity,seed,round_id,limit=3,reserved=()):
        # Hash tie-break is independent of candidate enumeration and hidden truth.
        candidates=[a for a in s.actions() if a.op!='read' or s.cost(a)<=capacity]
        s._score_p=s.probabilities();s._score_obligations=s.obligations()
        scored=[(self.score(a,s,reserved),digest([seed,round_id,worker,a.op,a.node]),a) for a in candidates]
        scored.sort(key=lambda row:row[:2],reverse=True)
        return [Proposal(worker,a,value,s.version) for value,_,a in scored[:limit]]


def make_case(seed,**params):
    """Version-2 generator: independent channels with arbitrary XOR sharing."""
    depth=params.pop('depth',3);parts=params.pop('parts',2);wrong=params.pop('wrong_refs',0)
    if depth<2 or parts<2:raise ValueError('invalid structural parameters')
    # Build empty legal tree using legacy layout, then independently assign channels.
    case=generate_case(seed,**params);rng=random.Random(seed+71983);nodes=case['nodes']
    if depth!=3:
        for fid in [n for n in list(nodes) if nodes[n]['meta']['type']=='folder']:
            parent=fid
            # depth=2 removes the folder level; depth>3 inserts nested folders.
            if depth==2:
                device=nodes[fid]['meta']['path'][1]
                nodes[device]['children'].remove(fid)
                nodes[device]['children'].extend(nodes[fid]['children'])
                for leaf in nodes[fid]['children']:nodes[leaf]['meta']['path'].remove(fid)
                del nodes[fid]
            else:
                children=nodes[fid]['children'];path=list(nodes[fid]['meta']['path'])
                for j in range(depth-3):
                    child=f'{fid}/L{j}';nodes[parent]['children']=[child];path=path+[child]
                    nodes[child]={'meta':{'type':'folder','size':0,'topic':None,'path':list(path)},'children':[]};parent=child
                nodes[parent]['children']=children
                for leaf in children:nodes[leaf]['meta']['path']=path+[leaf]
    leaves=[nid for nid,n in nodes.items() if n['meta']['type']=='doc']
    for nid in leaves:
        nodes[nid]['record']={'eid':nid,'kind':'noise'}
        nodes[nid]['text']=f'Routine inventory record {seed} {nid}. No case observation is reported.'
        nodes[nid]['meta']['topic']=rng.randrange(case['k']) if rng.random()<.5 else None
    pairs=params.get('pair_fraction',.65);quality=params.get('reference_quality',1);cue=params.get('cue_quality',.8)
    available=rng.sample(leaves,len(leaves));cursor=0
    for h in range(case['k']):
        for j in range(params.get('signal_count',4)):
            bit=case['truth'][h] if rng.random()<.85 else 1-case['truth'][h]
            count=parts if rng.random()<pairs else 1
            selected=available[cursor:cursor+count];cursor+=count
            if len(selected)!=count:raise ValueError('insufficient document slots')
            bits=[rng.randrange(2) for _ in range(count-1)];last=bit
            for v in bits:last^=v
            bits.append(last)
            for slot,nid in enumerate(selected):
                r={'eid':nid,'kind':'direct' if count==1 else 'share','h':h,'bit':bits[slot],'reliability':.85}
                if count>1:
                    r.update(pair=f'P{h}-{j}',slot=slot,parts=count)
                    if rng.random()<quality:
                        target=selected[(slot+1)%count]
                        if rng.random()<wrong:target=rng.choice([v for v in leaves if v not in selected])
                        r['target_path']=list(nodes[target]['meta']['path'])
                nodes[nid]['record']=r;nodes[nid]['meta']['topic']=h if rng.random()<cue else rng.randrange(case['k'])
                text=(f'Question H{h}. Export fragment P{h}-{j}, part {slot}, contains binary value {bits[slot]}. ' if count>1 else f'Question H{h}. The recorded indicator is {bit}. ')
                text+='The source channel reliability is 0.85. '
                if r.get('target_path'):text+='The companion export is stored at '+' > '.join(r['target_path'])+'. '
                nodes[nid]['text']=text
    case['schema']=2;case['parameters'].update(depth=depth,parts=parts,wrong_refs=wrong)
    case.pop('sha256',None);case['sha256']=digest(case)
    return case
