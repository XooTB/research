import requests,time
B="https://api.openalex.org/works"
T={"AI/ML":'("artificial intelligence" OR "machine learning" OR AI OR "federated learning" OR "large language model" OR "deep learning")',
"LLM/agents":'("large language model" OR LLM OR LLMs OR "AI agent" OR "AI agents" OR agentic)',
"federated learning":'("federated learning")',
"sustainability/ESG/circular":'(sustainability OR sustainable OR ESG OR "circular economy")',
"carbon":'(carbon)',
"supply chain":'("supply chain" OR traceability OR logistics)',
"IoT":'(IoT OR "internet of things")',
"healthcare":'(healthcare OR medical OR health OR hospital)',
"energy trading/grid":'("energy trading" OR "smart grid" OR microgrid OR "peer-to-peer energy" OR "P2P energy")',
"digital twin":'("digital twin" OR "digital twins")',
"NFT/metaverse":'(NFT OR NFTs OR "non-fungible" OR metaverse)',
"DeFi":'(DeFi OR "decentralized finance")',
"SSI/identity":'("self-sovereign" OR "decentralized identity" OR "digital identity")',
"CBDC/stablecoin":'(CBDC OR CBDCs OR "central bank digital" OR stablecoin OR stablecoins)',
"RWA/tokenization":'(tokenization OR tokenisation OR "real-world asset" OR "real world assets")',
"e-voting":'(voting)',"smart city":'("smart city" OR "smart cities")'}
def g(q):
    r=requests.get(B,params={"filter":f"title.search:{q},publication_year:2020-2025","group_by":"publication_year"},timeout=60).json(); time.sleep(0.25)
    return {int(x["key"]):x["count"] for x in r["group_by"]}
tot=g("blockchain")
print("title-only; blockchain totals:",[tot[y] for y in range(2020,2026)])
print(f"{'domain':28s} {'n2022':>6s} {'n2025':>6s}  sh22  sh23  sh24  sh25")
for k,q in T.items():
    c=g(f"blockchain AND {q}")
    sh=[c.get(y,0)/tot[y]*100 for y in (2022,2023,2024,2025)]
    print(f"{k:28s} {c.get(2022,0):6d} {c.get(2025,0):6d} "+" ".join(f"{s:5.1f}" for s in sh))
