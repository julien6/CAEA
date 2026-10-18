"""Hidden-tree environment, public views, and exact binary-channel evaluator.

Policies receive PublicState only. Nodes and truth remain in Environment.
Document payloads are incremental observations, never a free global index.
"""
from dataclasses import dataclass, field, asdict
import math
import random
import hashlib
import json


def entropy(p):
    return 0.0 if p <= 0 or p >= 1 else -p*math.log2(p)-(1-p)*math.log2(1-p)


def information(p, reliability):
    q = p*reliability + (1-p)*(1-reliability)
    return entropy(q)-entropy(reliability)


def posterior(records, k):
    logodds = [0.0]*k
    pairs = {}
    used = set()
    for r in records:
        if r['eid'] in used:
            continue
        used.add(r['eid'])
        if r['kind'] == 'direct':
            h, bit, rel = r['h'], r['bit'], r['reliability']
            logodds[h] += (2*bit-1)*math.log(rel/(1-rel))
        elif r['kind'] == 'share':
            pairs.setdefault(r['pair'], {})[r['slot']] = r
    for group in pairs.values():
        if len(group) == 2:
            a, b = group[0], group[1]
            if a['h'] != b['h'] or a['reliability'] != b['reliability']:
                continue  # Conflicting approximate assertions do not form a channel.
            bit, rel = a['bit'] ^ b['bit'], a['reliability']
            logodds[a['h']] += (2*bit-1)*math.log(rel/(1-rel))
    return [1/(1+math.exp(-max(-60,min(60,z)))) for z in logodds]


@dataclass(frozen=True)
class Action:
    op: str
    node: str


@dataclass
class PublicState:
    k: int
    known: dict = field(default_factory=dict)
    expanded: set = field(default_factory=set)
    opened: set = field(default_factory=set)
    read: set = field(default_factory=set)
    records: list = field(default_factory=list)
    # References reveal paths written in acquired documents, not hidden payloads.
    references: dict = field(default_factory=dict)
    spent: float = 0
    version: int = 0

    def probabilities(self):
        return posterior(self.records, self.k)

    def actions(self):
        result = []
        for nid, m in sorted(self.known.items()):
            if m['type'] == 'device' and nid not in self.opened:
                result.append(Action('load',nid))
            elif m['type'] in ('root','device','folder') and nid not in self.expanded:
                if m['type'] != 'device' or nid in self.opened:
                    result.append(Action('discover',nid))
            elif m['type'] == 'doc' and nid not in self.read:
                result.append(Action('read',nid))
        return result

    def cost(self, action):
        return self.known[action.node]['size'] if action.op == 'read' else 1

    def snapshot(self):
        return {'known':dict(self.known),'expanded':sorted(self.expanded),'opened':sorted(self.opened),
                'read':sorted(self.read),'records':list(self.records),'references':dict(self.references),
                'spent':self.spent,'version':self.version,'p':self.probabilities()}


class Environment:
    def __init__(self, case, budget=64, capacity=3):
        self._case = case
        self.budget, self.capacity = budget, capacity
        self.state = PublicState(case['k'])
        self.state.known['root'] = dict(case['nodes']['root']['meta'])
        self.actual = []
        self.traces = []
        self.duplicate_cost = 0
        self.curve = [(0,0.0)]

    def utility(self):
        return 1-sum(entropy(p) for p in posterior(self.actual,self.state.k))/self.state.k

    def step(self, joint, extractor=None):
        """Validate against one common snapshot, pay duplicates, then merge once.

        A read payload is ephemeral; only bounded typed records persist. There is
        no persistent raw-data cache in this reference experiment.
        """
        legal = set(self.state.actions())
        before = self.state.snapshot()
        spent_before = self.state.spent
        seen = set()
        acquired = []
        for agent, action in enumerate(joint):
            if action not in legal:
                raise ValueError(f'illegal action {action}')
            cost = self.state.cost(action)
            if cost > self.capacity and action.op == 'read':
                raise ValueError('read exceeds working capacity')
            if self.state.spent+cost > self.budget:
                continue
            self.state.spent += cost
            duplicate = action in seen
            seen.add(action)
            if duplicate:
                self.duplicate_cost += cost
            node = self._case['nodes'][action.node]
            obs = {'agent':agent,'action':asdict(action),'cost':cost,'duplicate':duplicate}
            if not duplicate:
                if action.op == 'load':
                    self.state.opened.add(action.node)
                elif action.op == 'discover':
                    self.state.expanded.add(action.node)
                    for child in node['children']:
                        self.state.known[child] = dict(self._case['nodes'][child]['meta'])
                    obs['children'] = node['children']
                else:
                    self.state.read.add(action.node)
                    real = node['record']
                    self.actual.append(real)
                    parsed = extractor({'text':node['text'],'meta':dict(node['meta'])},agent,self.state.version) if extractor else dict(real)
                    if parsed is not None:
                        self.state.records.append(parsed)
                        if parsed.get('target_path'):
                            # References guide exploration but do not grant direct access.
                            self.state.references[parsed['target_path'][-1]] = {
                                'path':parsed['target_path'],'h':parsed['h'],
                                'source':real['eid'],'pair':parsed.get('pair')}
                    obs['record'] = parsed
                    obs['document'] = node['text']
                    acquired.append(action.node)
            self.traces.append({'version':self.state.version,**obs})
        self.curve.append((self.state.spent,self.utility()))
        self.state.version += 1
        return {'before':before,'after':self.state.snapshot(),'acquired':acquired,
                'cost':self.state.spent-spent_before}

    def metrics(self):
        p = self.state.probabilities()
        exact = posterior(self.actual,self.state.k)
        # Left-continuous integration: acquisitions are paid before their benefit.
        area = sum((b[0]-a[0])*a[1] for a,b in zip(self.curve,self.curve[1:]))
        area += (self.budget-self.state.spent)*self.utility()
        truth = self._case['truth']
        estimated={r['eid']:r for r in self.state.records}
        typed=sum(estimated.get(r['eid'])==r for r in self.actual)/max(1,len(self.actual))
        return {'typed_accuracy':typed,'memory_bytes':len(json.dumps(self.state.snapshot()).encode()),'auc':area/self.budget,'utility':self.utility(),
                'brier':sum((v-y)**2 for v,y in zip(p,truth))/self.state.k,
                'accuracy':sum((v>.5)==bool(y) for v,y in zip(p,truth))/self.state.k,
                'resolved':sum(abs(v-.5)>=.4 and ((v>.5)==bool(y)) for v,y in zip(p,truth))/self.state.k,
                'mae':sum(abs(a-b) for a,b in zip(p,exact))/self.state.k,
                'duplicates':self.duplicate_cost/max(1,self.state.spent),
                'reads':len(self.state.read),'coverage':len(self.state.known)/len(self._case['nodes']),
                'cost':self.state.spent,'rounds':self.state.version}


def generate_case(seed, k=4, devices=4, folders=4, docs=8, pair_fraction=.65,
                  cue_quality=.8, reference_quality=1.0, signal_count=4, rendering='numeric'):
    """Case truth is fixed before rendering. Numeric and prose share one oracle.

    Pair shares are one-time-pad fragments: neither alone has information about
    the target bit. Combined shares form a binary symmetric channel. References
    are exact public paths when present, never labels on unread documents.
    """
    rng = random.Random(seed)
    truth = [rng.randrange(2) for _ in range(k)]
    nodes = {'root': {'meta':{'type':'root','size':0,'topic':None,'path':['root']},'children':[]}}
    leaves = []
    for d in range(devices):
        did = f'D{d}'
        nodes['root']['children'].append(did)
        nodes[did]={'meta':{'type':'device','size':0,'topic':None,'path':['root',did]},'children':[]}
        for f in range(folders):
            fid=f'{did}/F{f}'
            nodes[did]['children'].append(fid)
            nodes[fid]={'meta':{'type':'folder','size':0,'topic':None,'path':['root',did,fid]},'children':[]}
            for j in range(docs):
                nid=f'{fid}/N{j}'
                nodes[fid]['children'].append(nid)
                topic = rng.randrange(k) if rng.random()<.5 else None
                nodes[nid]={'meta':{'type':'doc','size':rng.choice([1,1,2,3]),'topic':topic,
                                   'path':['root',did,fid,nid]},'children':[],
                            'record':{'eid':nid,'kind':'noise'},
                            'text':f'Routine inventory record {seed}-{d}-{f}-{j}. No case observation is reported.'}
                leaves.append(nid)
    # Sampling and IDs are independent of truth. Noise shares no diagnostic labels.
    slots=rng.sample(leaves, k*signal_count*2)
    cursor=0
    names=['access','copy','transfer','collaboration','authorization','meeting']
    for h in range(k):
        for j in range(signal_count):
            reliability=.85
            bit=truth[h] if rng.random()<reliability else 1-truth[h]
            paired=rng.random()<pair_fraction
            a,b=slots[cursor:cursor+2]; cursor+=2
            if paired:
                key=rng.randrange(2)
                records=[(a,{'kind':'share','h':h,'pair':f'P{h}-{j}','slot':0,'bit':key,'reliability':reliability},b),
                         (b,{'kind':'share','h':h,'pair':f'P{h}-{j}','slot':1,'bit':key^bit,'reliability':reliability},a)]
            else:
                records=[(a,{'kind':'direct','h':h,'bit':bit,'reliability':reliability},None)]
            for nid,record,target in records:
                record['eid']=nid
                if target and rng.random()<reference_quality:
                    record['target_path']=nodes[target]['meta']['path']
                nodes[nid]['record']=record
                nodes[nid]['meta']['topic']=h if rng.random()<cue_quality else rng.randrange(k)
                prefix=f'Artifact {nid}. Investigation question H{h}: {names[h%len(names)]}. '
                if paired:
                    text=prefix+f'Export fragment {record["pair"]}, part {record["slot"]}, contains binary value {record["bit"]}. '
                    text+='The two parts must be XOR-combined; an individual part has no implication. '
                else:
                    text=prefix+f'The recorded indicator is {bit} (1 supports, 0 contradicts). '
                text+=f'The source channel reliability is {reliability}. '
                if record.get('target_path'):
                    text+='The companion export is stored at '+ ' > '.join(record['target_path'])+'. '
                nodes[nid]['text']=text
    case={'schema':1,'seed':seed,'k':k,'truth':truth,'nodes':nodes,
          'parameters':dict(devices=devices,folders=folders,docs=docs,pair_fraction=pair_fraction,
                            cue_quality=cue_quality,reference_quality=reference_quality,signal_count=signal_count)}
    if rendering!='numeric':
        if rendering!='identity_join':raise ValueError('unknown documentary rendering')
        from .documents import render_identity
        render_identity(case)
        case['parameters']['rendering']=rendering
    case['sha256']=hashlib.sha256(json.dumps(case,sort_keys=True).encode()).hexdigest()
    return case
