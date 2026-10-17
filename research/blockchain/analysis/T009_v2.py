import requests,time,json
B="https://api.openalex.org/works"
D=json.load(open("doms.json"))
for k,q in D.items():
    r=requests.get(B,params={"filter":f"title_and_abstract.search:blockchain AND {q},publication_year:2025","sample":15,"seed":7,"per_page":15,"select":"title"},timeout=60).json()
    print(f"\n## {k}")
    for w in r["results"]: print("  -",(w["title"] or "")[:105])
    time.sleep(0.3)
