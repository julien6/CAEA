"""Policies use public observations only; no access to Environment or truth."""
import math
import random
from collections import Counter
from .core import information


class Policy:
    def __init__(self, name, seed, agents=3, organization='central', references=True):
        self.name,self.rng,self.agents=name,random.Random(seed),agents
        self.organization,self.references=organization,references
        self.counts=Counter(); self.gains=Counter()

    def feedback(self, update):
        # Observed typed evidence, rather than evaluator reward, drives UCB.
        from .core import entropy
        before,after=update['before'],update['after']
        gain=sum(entropy(p)-entropy(q) for p,q in zip(before['p'],after['p']))/len(before['p'])
        for nid in update['acquired']:
            device=after['known'][nid]['path'][1]
            self.counts[device]+=1
            self.gains[device]+=gain/max(1,len(update['acquired']))

    def score(self, a, s, reserved):
        meta=s.known[a.node]
        family=self.name.removesuffix('_informed')
        myopic=family=='myopic'
        if myopic:family='caea'
        p=s.probabilities()
        # Common prior proxy: a diagnostic channel may be found in any document.
        topic=meta['topic']
        unresolved=1 if topic is None else information(p[topic],.85)/information(.5,.85)
        if a.op=='read':
            score=.16*unresolved/s.cost(a)
        else:
            score={'load':.035,'discover':.045}[a.op]
            if meta['type']=='folder': score=.055
        if self.name.endswith('_informed') and a.op=='read' and topic is None:
            score=0.0  # The documented generator assigns all diagnostics a topic.
        if family=='ucb':
            path=meta['path']; device=path[1] if len(path)>1 else 'root'
            n=self.counts[device]
            score+=(self.gains[device]/max(1,n)+.06*math.sqrt(2*math.log(2+sum(self.counts.values()))/(n+1)))
        if family in ('caea','caea_no_refs') and self.references:
            for target,ref in s.references.items():
                if myopic and a.op!='read':continue
                if target in s.read or a.node not in ref['path']:
                    continue
                # A real acquired share, rather than a raw path, creates obligation.
                pending=any(r.get('pair')==ref.get('pair') and r['kind']=='share' for r in s.records)
                if not pending:
                    continue
                dist=len(ref['path'])-ref['path'].index(a.node)
                benefit=information(p[ref['h']],.85)
                score+=benefit/(dist+s.cost(a))
        # Residual allocation discounts same hypothesis/device within the batch.
        if family in ('joint','caea','caea_no_refs','ucb'):
            for chosen in reserved:
                other=s.known[chosen.node]
                if topic is not None and topic==other['topic']:
                    score*=.6
        return score

    def choose(self,s,capacity):
        candidates=[a for a in s.actions() if s.cost(a)<=capacity]
        remaining=self.budget-s.spent
        if not candidates or remaining<min(s.cost(a) for a in candidates):
            return []
        joint=[]
        for agent in range(self.agents):
            valid=[a for a in candidates if s.cost(a)<=remaining]
            if self.name!='independent':
                valid=[a for a in valid if a not in joint]
            if self.organization=='coalition' and len(valid)>self.agents:
                subgroup=[a for a in valid if len(s.known[a.node]['path'])<2 or
                          int(s.known[a.node]['path'][1][1:])%2==agent%2]
                if subgroup: valid=subgroup
            if not valid: break
            if self.name=='random':
                chosen=self.rng.choice(valid)
            else:
                # Fixed ID-independent random tie breaking, same candidates each agent.
                scores=[(self.score(a,s,joint),self.rng.random(),a) for a in valid]
                chosen=max(scores,key=lambda z:(z[0],z[1]))[2]
            joint.append(chosen)
            remaining-=s.cost(chosen)
        return joint
