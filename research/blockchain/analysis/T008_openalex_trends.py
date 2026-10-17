import requests, json, time, sys
B="https://api.openalex.org/works"
DOM={
 "healthcare/medical": '(healthcare OR medical OR "health records" OR hospital)',
 "supply chain/logistics": '("supply chain" OR logistics OR traceability)',
 "IoT": '(IoT OR "internet of things")',
 "energy/P2P trading": '(energy OR "smart grid" OR "peer-to-peer trading" OR microgrid)',
 "finance/DeFi": '(DeFi OR "decentralized finance")',
 "NFT/metaverse": '(NFT OR "non-fungible" OR metaverse)',
 "CBDC/stablecoin": '(CBDC OR "central bank digital currency" OR stablecoin)',
 "tokenization/RWA": '("real-world asset" OR "asset tokenization" OR "tokenized assets" OR "security token")',
 "AI/ML integration": '("artificial intelligence" OR "machine learning" OR "large language model" OR "federated learning")',
 "federated learning": '("federated learning")',
 "LLM/AI agents": '("large language model" OR LLM OR "AI agent" OR "autonomous agents")',
 "vehicles/V2X/UAV": '(vehicular OR VANET OR "electric vehicle" OR UAV OR drone)',
 "digital identity/SSI": '("self-sovereign identity" OR "decentralized identity" OR "digital identity")',
 "education/credentials": '(education OR "academic credentials" OR diploma)',
 "agriculture/food": '(agriculture OR agri-food OR "food supply" OR "food traceability")',
 "carbon/sustainability/ESG": '("carbon credit" OR "carbon trading" OR "carbon emission" OR ESG OR sustainability)',
 "voting/e-government": '("e-voting" OR "electronic voting" OR e-government)',
 "smart cities": '("smart city" OR "smart cities")',
 "construction/BIM": '(construction OR BIM OR "building information")',
 "6G/edge computing": '(6G OR "edge computing" OR "mobile edge")',
 "digital twin": '("digital twin")',
 "DePIN": '(DePIN OR "decentralized physical infrastructure")',
 "data sharing/marketplace": '("data sharing" OR "data marketplace")',
 "IP/copyright/creative": '(copyright OR "intellectual property" OR royalties)',
}
yrs=range(2018,2026)
def counts(q):
    r=requests.get(B,params={"filter":f"title_and_abstract.search:blockchain AND {q},publication_year:2018-2026","group_by":"publication_year","mailto":"research@example.org"},timeout=60)
    r.raise_for_status()
    return {int(g["key"]):g["count"] for g in r.json()["group_by"]}
out={"__all__":counts("(blockchain)")}
for k,q in DOM.items():
    out[k]=counts(q); time.sleep(0.3); print(k,file=sys.stderr)
json.dump(out,open("trends.json","w"),indent=1)
tot=out["__all__"]
print(f"{'domain':28s}"+"".join(f"{y:>7d}" for y in yrs)+"  share18 share25  x(25/20)")
rows=[]
for k in DOM:
    c=out[k]; s18=c.get(2018,0)/tot[2018]*100; s25=c.get(2025,0)/tot[2025]*100
    g=c.get(2025,0)/max(c.get(2020,1),1)
    rows.append((s25-s18,k,c,s18,s25,g))
print(f"{'ALL':28s}"+"".join(f"{tot.get(y,0):7d}" for y in yrs))
for d,k,c,s18,s25,g in sorted(rows,reverse=True):
    print(f"{k:28s}"+"".join(f"{c.get(y,0):7d}" for y in yrs)+f"  {s18:6.1f} {s25:6.1f}  {g:6.2f}")
