"""Four decision protocols. No protocol receives hidden state or oracle metrics."""
from dataclasses import asdict
from copy import deepcopy
from .model import AgentKnowledge,AcquisitionCore,Action,Message,Assignment,digest


class OrganizationProtocol:
    def __init__(self,root,k,n,core,seed=0,delay=0,capacities=None):
        self.n,self.core,self.seed,self.delay=n,core,seed,delay
        self.capacities=capacities or [3]*n
        self.views=[AgentKnowledge(k,known={'root':deepcopy(root)}) for _ in range(n)]
        self.queue=[];self.seen=[set() for _ in range(n)];self.mail=[[] for _ in range(n)]
        self.logs=[];self.messages=0;self.bytes=0;self.round=0;self.serial=0;self.available=set(range(n))
        self.assignments=[];self.metrics={'conflicts':0,'formations':0,'dissolutions':0,'bids':0,'expirations':0}
    def send(self,sender,recipient,kind,payload,mid=None):
        self.serial+=1;mid=mid or f'{sender}:{self.round}:{self.serial}'
        message=Message(mid,sender,recipient,kind,deepcopy(payload),self.round+self.delay)
        lost=int(digest([self.seed,message.id,sender,recipient])[:12],16)/16**12<getattr(self,'drop_rate',0)
        if not lost:self.queue.append(message)
        self.messages+=1;self.bytes+=len(__import__('json').dumps(asdict(message),sort_keys=True).encode())
        self.logs.append({'round':self.round,'type':'lost' if lost else 'send',**asdict(message)})
    def receive(self,m):
        if m.id in self.seen[m.recipient]:return
        self.seen[m.recipient].add(m.id)
        if m.kind=='EVIDENCE_UPDATE':self.views[m.recipient].integrate(m.payload)
        else:self.mail[m.recipient].append(m)
    def deliver(self):
        # Deliver zero-delay gossip to closure. Seen IDs bound forwarding.
        while True:
            due=[m for m in self.queue if m.due<=self.round and m.recipient in self.available]
            if not due:break
            due_ids={id(m) for m in due};self.queue=[m for m in self.queue if id(m) not in due_ids]
            for m in due:
                self.logs.append({'round':self.round,'type':'deliver','id':m.id,'recipient':m.recipient,'kind':m.kind})
                self.receive(m)
    def start(self,round_id,spent,available):
        self.round=round_id;self.available=set(available)
        for s in self.views:s.spent=spent
        self.deliver()
    def propose(self,worker,limit=3,reserved=()):
        return self.core.proposals(self.views[worker].detached(),worker,self.capacities[worker],self.seed,self.round,limit,reserved)
    def choose(self):raise NotImplementedError
    def integrate(self,worker,event):raise NotImplementedError
    def pending(self):return bool(self.queue)
    def state_log(self):
        return {'knowledge':[digest(s.snapshot()) for s in self.views],**self.metrics}


class Centralized(OrganizationProtocol):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.coordinator=self.views[0].detached();self.busy=set();self.busy_since={}
    def send_assignment(self,worker,action):
        # Serializable event replay, never a Python object on the wire.
        payload={'action':asdict(action),'snapshot':self.coordinator.snapshot()}
        self.send(0,worker,'CENT_ASSIGN',payload)
    def receive(self,m):
        if m.kind=='RESULT':
            if m.id in self.seen[0]:return
            self.seen[0].add(m.id);self.coordinator.integrate(m.payload);self.busy.discard(m.payload['worker'])
        elif m.kind=='CENT_ASSIGN':
            if m.id in self.seen[m.recipient]:return
            self.seen[m.recipient].add(m.id)
            snap=m.payload['snapshot'];s=self.views[m.recipient]
            s.known.update(deepcopy(snap['known']));s.opened.update(snap['opened']);s.expanded.update(snap['expanded']);s.read.update(snap['read'])
            known={r['eid'] for r in s.records};s.records.extend(deepcopy(r) for r in snap['records'] if r['eid'] not in known)
            self.assignments.append(Assignment(m.recipient,Action(**m.payload['action']),0))
        else:super().receive(m)
    def choose(self):
        for worker in list(self.busy):
            if self.round-self.busy_since[worker]>2*self.delay+3:
                self.busy.discard(worker);self.metrics['expirations']+=1
        reserved=[]
        for worker in sorted(self.available):
            if worker in self.busy:continue
            ps=self.core.proposals(self.coordinator.detached(),worker,self.capacities[worker],self.seed,self.round,10000,reserved)
            valid=[p for p in ps if p.action not in reserved]
            if not valid:continue
            a=valid[0].action;reserved.append(a);self.busy.add(worker);self.busy_since[worker]=self.round;self.send_assignment(worker,a)
        self.deliver();result=self.assignments;self.assignments=[]
        return [a for a in result if a.worker in self.available]
    def integrate(self,worker,event):
        self.views[worker].integrate(event);self.send(worker,0,'RESULT',event)
    def rejected(self,worker):self.busy.discard(worker)
    def pending(self):return super().pending() or bool(self.assignments)


class PeerToPeer(OrganizationProtocol):
    def neighbours(self,i):return sorted({(i-1)%self.n,(i+1)%self.n}-{i})
    def receive(self,m):
        new=m.id not in self.seen[m.recipient]
        super().receive(m)
        if new and m.kind=='EVIDENCE_UPDATE':
            for target in self.neighbours(m.recipient):
                if target!=m.sender:self.send(m.recipient,target,m.kind,m.payload,m.id)
    def choose(self):
        proposed={i:self.propose(i,1) for i in sorted(self.available)}
        for i,ps in proposed.items():
            if ps:
                for target in self.neighbours(i):self.send(i,target,'INTENT',{'action':asdict(ps[0].action),'epoch':self.round})
        self.deliver();result=[]
        for i,ps in proposed.items():
            if not ps:continue
            a=ps[0].action;priority=lambda w:(w-self.round)%self.n
            conflicts=[m for m in self.mail[i] if m.kind=='INTENT' and m.payload['epoch']==self.round and m.payload['action']==asdict(a) and priority(m.sender)<priority(i)]
            self.mail[i]=[m for m in self.mail[i] if m.payload.get('epoch',self.round)>=self.round]
            if conflicts:self.metrics['conflicts']+=1
            else:result.append(Assignment(i,a,i))
        return result
    def integrate(self,worker,event):
        self.views[worker].integrate(event)
        for target in self.neighbours(worker):self.send(worker,target,'EVIDENCE_UPDATE',event,mid=event['id'])
    def rejected(self,worker):pass


class Coalitions(PeerToPeer):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.membership={};self.groups={};self.invitations={};self.busy={}
    def neighbours(self,i):return [j for j in self.membership if self.membership.get(j)==self.membership.get(i) and j!=i] if i in self.membership else []
    def _receive(self,m):
        if m.id in self.seen[m.recipient]:return
        if m.kind=='COAL_INVITE':
            self.seen[m.recipient].add(m.id)
            if m.recipient not in self.membership:
                choices=self.propose(m.recipient,1);local=choices[0].score if choices else 0
                if m.payload['value']>=local/2:
                    self.send(m.recipient,m.sender,'COAL_JOIN',{'goal':m.payload['goal']})
        elif m.kind=='COAL_JOIN':
            self.seen[m.recipient].add(m.id);leader=m.recipient
            if leader in self.groups and len(self.groups[leader]['members'])<3 and m.sender not in self.membership:
                self.groups[leader]['members'].add(m.sender);self.membership[m.sender]=leader
                self.logs.append({'round':self.round,'type':'coalition_join','leader':leader,'member':m.sender,'goal':m.payload['goal']})
        elif m.kind=='COAL_ASSIGN':
            self.seen[m.recipient].add(m.id)
            for event in m.payload['events']:
                self.views[m.recipient].integrate(event)
                self.event_archive[m.recipient][event['id']]=deepcopy(event)
            self.assignments.append(Assignment(m.recipient,Action(**m.payload['action']),m.sender))
        else:super().receive(m)
    def choose(self):
        for leader,g in list(self.groups.items()):
            s=self.views[leader];goal=g['goal'];done=goal in s.read or goal in s.expanded
            progress=len(s.events)
            if progress>g['progress']:g['last']=self.round;g['progress']=progress
            if done or self.round-g['last']>=3:
                for i in g['members']:self.membership.pop(i,None);self.busy.pop(i,None)
                del self.groups[leader];self.metrics['dissolutions']+=1
                self.logs.append({'round':self.round,'type':'coalition_dissolve','leader':leader,'reason':'completed' if done else 'stalled'})
        for i in sorted(self.available):
            if i in self.membership:continue
            ps=self.propose(i,1)
            if not ps:continue
            obs=self.views[i].obligations();goal=obs[0].path[-1] if obs else ps[0].action.node
            self.groups[i]={'goal':goal,'members':{i},'last':self.round,'progress':len(self.views[i].events)};self.membership[i]=i;self.metrics['formations']+=1
            for target in sorted(self.available-{i}):self.send(i,target,'COAL_INVITE',{'goal':goal,'value':ps[0].score})
            # Only one initiator per epoch; others may join after delivery.
            break
        self.deliver();result=[]
        for leader,g in self.groups.items():
            if leader not in self.available:continue
            reserved=[]
            for worker in sorted(g['members'] & self.available):
                if worker in self.busy and self.round-self.busy[worker]<2*self.delay+2:continue
                self.busy.pop(worker,None)
                ps=self.core.proposals(self.views[leader].detached(),worker,self.capacities[worker],self.seed,self.round,10000,reserved)
                valid=[p for p in ps if p.action not in reserved]
                if valid:
                    a=valid[0].action;reserved.append(a);self.busy[worker]=self.round
                    events=list(self.event_archive[leader].values())
                    self.send(leader,worker,'COAL_ASSIGN',{'action':asdict(a),'events':events})
        self.deliver();result=self.assignments;self.assignments=[]
        assigned={a.worker for a in result}
        for i in sorted(self.available):
            if i not in self.membership and i not in assigned:
                ps=self.propose(i,1)
                if ps:result.append(Assignment(i,ps[0].action,i))
        return result
    def start(self,*args):
        if not hasattr(self,'event_archive'):self.event_archive=[{} for _ in range(self.n)]
        super().start(*args)
    def integrate(self,worker,event):
        self.event_archive[worker][event['id']]=deepcopy(event);self.busy.pop(worker,None)
        super().integrate(worker,event)
    def receive(self,m):
        # dispatch is provided by _receive below; archive only delivered observations.
        self._receive(m)
        if m.kind=='EVIDENCE_UPDATE' and m.id in self.seen[m.recipient]:self.event_archive[m.recipient][m.payload['id']]=deepcopy(m.payload)



class Market(OrganizationProtocol):
    def __init__(self,*args,**kw):
        super().__init__(*args,**kw);self.offers={};self.busy={}
    def receive(self,m):
        if m.id in self.seen[m.recipient]:return
        if m.kind=='BID':
            self.seen[m.recipient].add(m.id);self.offers[m.sender]=m.payload
        elif m.kind=='AWARD':
            self.seen[m.recipient].add(m.id)
            self.assignments.append(Assignment(m.recipient,Action(**m.payload['action']),-1))
        elif m.kind=='MARKET_RESULT':
            self.seen[m.recipient].add(m.id);self.busy.pop(m.payload['worker'],None)
        else:super().receive(m)
    def choose(self):
        for i in sorted(self.available):
            if i in self.busy and self.round-self.busy[i]<2*self.delay+2:continue
            self.busy.pop(i,None);ps=self.propose(i,3)
            if ps:
                self.metrics['bids']+=len(ps)
                self.send(i,0,'BID',{'epoch':self.round,'offers':[{'action':asdict(p.action),'score':p.score} for p in ps]})
        self.deliver();ranked=[]
        for worker,payload in self.offers.items():
            if worker not in self.available or worker in self.busy or self.round-payload['epoch']>self.delay+1:continue
            for o in payload['offers']:ranked.append((o['score'],digest([self.seed,self.round,worker,o['action']]),worker,o['action']))
        used=set();workers=set()
        for _,_,worker,action in sorted(ranked,reverse=True):
            key=(action['op'],action['node'])
            if key in used or worker in workers:continue
            used.add(key);workers.add(worker);self.busy[worker]=self.round
            self.send(0,worker,'AWARD',{'action':action})
        self.deliver();result=self.assignments;self.assignments=[];return result
    def integrate(self,worker,event):
        self.views[worker].integrate(event);self.send(worker,0,'MARKET_RESULT',{'worker':worker})
        # Public result bulletin is explicit, costed, and delayed; bids remain local.
        for i in range(self.n):
            if i!=worker:self.send(worker,i,'EVIDENCE_UPDATE',event,mid=event['id'])
    def rejected(self,worker):self.busy.pop(worker,None)


PROTOCOLS={'CENT':Centralized,'P2P':PeerToPeer,'COAL':Coalitions,'MKT':Market}
