import requests,time
U="https://api.semanticscholar.org/graph/v1/paper/search/bulk"
Q={"ALL":"blockchain",
"AI/ML":'blockchain + ("artificial intelligence" | "machine learning" | "federated learning" | "large language model" | "deep learning")',
"LLM/agents":'blockchain + ("large language model" | "large language models" | "AI agent" | "AI agents")',
"sustainability/ESG":'blockchain + (sustainability | ESG | "circular economy")',
"carbon":'blockchain + ("carbon credit" | "carbon trading" | "carbon emission" | "carbon market")',
"supply chain":'blockchain + ("supply chain" | traceability)',
"IoT":'blockchain + (IoT | "internet of things")',
"healthcare":'blockchain + (healthcare | medical | "health records")',
"energy trading/grid":'blockchain + ("energy trading" | "smart grid" | microgrid | "peer-to-peer energy")',
"digital twin":'blockchain + "digital twin"',
"NFT/metaverse":'blockchain + (NFT | "non-fungible" | metaverse)',
"DeFi":'blockchain + (DeFi | "decentralized finance")',
"CBDC/stablecoin":'blockchain + (CBDC | "central bank digital currency" | stablecoin)',
"e-voting":'blockchain + (voting)'}
def tot(q,y):
    for i in range(6):
        r=requests.get(U,params={"query":q,"year":str(y),"fields":"title"},timeout=60)
        if r.status_code==200: return r.json().get("total",0)
        time.sleep(3+3*i)
    return -1
res={}
for k,q in Q.items():
    res[k]={y:tot(q,y) for y in (2022,2025)}; time.sleep(1.2)
A=res["ALL"]; print("ALL",A)
for k,c in res.items():
    if k=="ALL": continue
    print(f"{k:22s} {c[2022]:6d} {c[2025]:6d}  sh22 {c[2022]/A[2022]*100:5.1f}  sh25 {c[2025]/A[2025]*100:5.1f}")
