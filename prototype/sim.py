"""Dependency-free deterministic Living Universe reference scheduler."""
from dataclasses import dataclass, asdict
import argparse, hashlib, heapq, json, random
REGIONS = ("magic","cultivation","science","primal","superpowers","nexus")
@dataclass
class Agent:
    id:int
    region:str
    age_days:int
    skill:int
    knowledge:int
    next_action:int
class Universe:
    def __init__(self,population=1000,seed=42):
        self.seed=seed; self.rng=random.Random(seed); self.day=0
        self.agents={}; self.queue=[]; self.events=[]
        for i in range(population):
            a=Agent(i,REGIONS[i%5],self.rng.randrange(16*365,80*365),
                    self.rng.randrange(100),self.rng.randrange(100),
                    self.rng.randrange(1,31))
            self.agents[i]=a; heapq.heappush(self.queue,(a.next_action,i))
    def advance(self,days):
        end=self.day+days
        while self.queue and self.queue[0][0]<=end:
            when,ident=heapq.heappop(self.queue); a=self.agents[ident]
            if when!=a.next_action: continue
            action=self.rng.randrange(100)
            if action<65: a.skill+=1; kind="training"
            elif action<90: a.knowledge+=1; kind="study"
            else: a.region=REGIONS[self.rng.randrange(len(REGIONS))]; kind="migration"
            self.events.append((when,ident,kind,a.region))
            a.next_action=when+self.rng.randrange(1,31)
            heapq.heappush(self.queue,(a.next_action,ident))
        for a in self.agents.values(): a.age_days+=days
        self.day=end
    def snapshot(self):
        return {"schema_version":1,"seed":self.seed,"day":self.day,
                "agents":[asdict(a) for a in self.agents.values()],
                "events":self.events,"rng_state":repr(self.rng.getstate())}
    def digest(self):
        data=json.dumps(self.snapshot(),sort_keys=True,separators=(",",":"))
        return hashlib.sha256(data.encode()).hexdigest()
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--agents",type=int,default=1000)
    p.add_argument("--days",type=int,default=365)
    p.add_argument("--seed",type=int,default=42)
    args=p.parse_args(); w=Universe(args.agents,args.seed); w.advance(args.days)
    print(json.dumps({"agents":len(w.agents),"days":w.day,
                      "events":len(w.events),"sha256":w.digest()},indent=2))
