"""Atomic physical execution and independent evaluation of organization protocols."""
from copy import deepcopy
from dataclasses import asdict
import math,time,random
from .model import AcquisitionCore,posterior,digest,EpisodeConfig
from .protocols import PROTOCOLS
from caea.core import entropy


class Environment:
    def __init__(self,case,budget=72):
        self._case=case;self.budget=budget;self.spent=0;self.actual={};self.completed=set();self.duplicate_cost=0
        self.events=[];self.curve=[(0,0.,0.)];self.elapsed=0
    def utility(self):
        if self._case.get('external'):
            groups=self._case['support_sets']
            return sum(all(e in self.actual for e in group) for group in groups)/len(groups)
        return 1-sum(entropy(p) for p in posterior(self.actual.values(),self._case['k']))/self._case['k']
    def execute(self,assignments,views,capacities,round_id):
        accepted=[];refused=[]
        # Fair admission is mechanical and independent of values, authority, and truth.
        for assignment in sorted(assignments,key=lambda a:(a.worker-round_id)%len(views)):
            i=assignment.worker;a=assignment.action;s=views[i];m=s.known.get(a.node)
            if not m or a not in s.actions():refused.append({'worker':i,'reason':'stale_or_illegal','action':asdict(a)});continue
            cost=s.cost(a)
            if a.op=='read' and cost>capacities[i]:refused.append({'worker':i,'reason':'capacity','action':asdict(a)});continue
            if self.spent+cost>self.budget:refused.append({'worker':i,'reason':'budget','action':asdict(a)});continue
            # Observed metadata must match actual metadata, never a privilege granted by a reference.
            node=self._case['nodes'][a.node]
            if node['meta']!=m:raise ValueError('fabricated public metadata')
            self.spent+=cost;key=(a.op,a.node);duplicate=key in self.completed;self.completed.add(key)
            if duplicate:self.duplicate_cost+=cost
            e={'id':f'{round_id}:{i}:{a.op}:{a.node}','worker':i,'action':asdict(a),'cost':cost,'duplicate':duplicate}
            if a.op=='discover':e['children']={v:deepcopy(self._case['nodes'][v]['meta']) for v in node['children']}
            elif a.op=='read':self.actual[a.node]=deepcopy(node['record']);e['payload']={'meta':deepcopy(m),'text':node['text']}
            accepted.append(e)
        return accepted,refused


def duration(event,model,seed):
    base=event['cost']
    if model=='slow':return 10*base
    if model=='lognormal':
        rng=random.Random(int(digest([seed,event['action']])[:16],16));return base*rng.lognormvariate(-.5,1)
    return base


def episode(case,config,extractor=None,replay=None):
    EpisodeConfig.validate(config)
    started=time.perf_counter();n=config.get('agents',3);caps=config.get('capacities',[3]*n)
    core=AcquisitionCore(config.get('policy','caea'),config.get('bonus',1),informed=not case.get('external',False))
    org=PROTOCOLS[config['organization']](case['nodes']['root']['meta'],case['k'],n,core,seed=config.get('policy_seed',0),delay=config.get('delay',0),capacities=caps)
    org.drop_rate=config.get('drop_rate',0)
    env=Environment(case,config.get('budget',72));traces=[];round_id=0;idle=0;refusals=0;extracted=[]
    threshold_times={str(v):None for v in (.1,.25,.4)};sync=config.get('sync',.1);model=config.get('duration','linear');message_cost=config.get('message_cost',0)
    while env.spent<env.budget:
        # Bound is a safety assertion, never silent experimental truncation.
        if round_id>10000:raise RuntimeError('nonterminating protocol')
        available=set(range(n))
        if config.get('unavailable') and 5<=round_id<10:available.discard(n-1)
        before_bytes=org.bytes;org.start(round_id,env.spent,available)
        assignments=org.choose()
        if len({a.worker for a in assignments})!=len(assignments):raise AssertionError('multiple assignments to one worker')
        events,refused=env.execute(assignments,org.views,caps,round_id);refusals+=len(refused)
        for r in refused:org.rejected(r['worker'])
        for e in events:
            if e['action']['op']=='read':
                if replay is not None:
                    key=e['id']
                    if key not in replay:raise AssertionError('unrecorded response')
                    e['record']=deepcopy(replay[key])
                elif extractor:
                    e['record']=extractor(e['payload'],e['worker'],round_id)
                    if e['record'] and e['record']['kind']=='share':e['record'].setdefault('parts',2)
                else:e['record']=deepcopy(case['nodes'][e['action']['node']]['record'])
                if e['record'] is not None:
                    e['record']=deepcopy(e['record'])
                    e['record']['eid']=e['action']['node']  # authoritative executor identity, not extractor testimony
                extracted.append({'event':e['id'],'record':e['record']})
                del e['payload']
            org.integrate(e['worker'],e)
        dt=max([duration(e,model,case['seed']) for e in events] or [1])+sync+message_cost*(org.bytes-before_bytes)/1024
        env.elapsed+=dt
        utility=env.utility();env.curve.append((env.spent,env.elapsed,utility))
        for t in threshold_times:
            if threshold_times[t] is None and utility>=float(t):threshold_times[t]=env.elapsed
        traces.append({'round':round_id,'assignments':[asdict(a) for a in assignments],'events':events,'refused':refused,'state':org.state_log(),'elapsed':env.elapsed})
        idle=idle+1 if not events else 0
        # Delayed messages may restore progress. Empty acquisition plans alone do not imply termination.
        if idle>=max(8,4*config.get('delay',0)+4) and not org.pending():break
        # Permanently stale mail/assignments cannot buy an unaffordable read.
        if idle>=max(30,8*config.get('delay',0)+8):
            org.logs.append({'round':round_id,'type':'quiescence','pending':len(org.queue)});break
        round_id+=1
    area=sum((b[0]-a[0])*a[2] for a,b in zip(env.curve,env.curve[1:]))+(env.budget-env.spent)*env.utility()
    p=[sum(s.probabilities()[h] for s in org.views)/n for h in range(case['k'])]
    exact=posterior(env.actual.values(),case['k']) if not case.get('external') else [.5]*case['k']
    groups={r['pair'] for r in env.actual.values() if r['kind']=='share'}
    complete=sum(len({r['slot'] for r in env.actual.values() if r.get('pair')==pair})==max(r.get('parts',2) for r in env.actual.values() if r.get('pair')==pair) for pair in groups)
    metrics={'auc':area/env.budget,'utility':env.utility(),'cost':env.spent,'elapsed':env.elapsed,'rounds':len(traces),'duplicates':env.duplicate_cost/max(1,env.spent),'messages':org.messages,'message_bytes':org.bytes,'communication_cost':message_cost*org.bytes/1024,'refusals':refusals,'dependency_completion':complete/max(1,len(groups)),**org.metrics}
    if not case.get('external'):
        metrics.update(brier=sum((v-y)**2 for v,y in zip(p,case['truth']))/case['k'],mae=sum(abs(a-b) for a,b in zip(p,exact))/case['k'])
    return {'schema':2,'config':config,'case_sha256':case['sha256'],'metrics':metrics,'threshold_times':threshold_times,'curve':env.curve,'traces':traces,'messages':org.logs,'extractions':extracted,'wall_seconds':time.perf_counter()-started}
