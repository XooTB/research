"""T010: pull blockchain x {FL, supply chain, carbon} works from OpenAlex with venue-quality signals."""
import requests,time,json,sys,os
B="https://api.openalex.org"
OUT=sys.argv[1]
BC='(blockchain OR "distributed ledger" OR "smart contract" OR "smart contracts")'
DOM={
 "fl":   f'title.search:{BC} AND ("federated learning" OR federated)',
 "sc":   f'title.search:{BC} AND ("supply chain" OR "supply chains" OR traceability OR logistics OR provenance OR "food chain")',
 "carbon": f'title_and_abstract.search:{BC} AND ("carbon trading" OR "carbon credit" OR "carbon credits" OR "carbon market" OR "carbon emission" OR "carbon emissions" OR "emission trading" OR "emissions trading" OR "carbon footprint" OR "carbon neutrality" OR "green certificate" OR "renewable energy certificate" OR "carbon offset" OR "net zero")',
}
SEL="id,doi,title,publication_year,type,cited_by_count,fwci,citation_normalized_percentile,primary_location,keywords,primary_topic,authorships"
def get(params):
    for i in range(4):
        r=requests.get(B+"/works",params=params,timeout=90)
        if r.status_code==200: return r.json()
        print("HTTP",r.status_code,r.text[:200],file=sys.stderr); time.sleep(5*(i+1))
    raise SystemExit("OpenAlex refused (budget?)")
def pull(f):
    # lean: top 600 most-cited 2018+, plus top 400 most-cited 2024+ (anonymous budget ~100 calls/day)
    rows=[]
    for yrs,pages in (("2018-2026",3),("2024-2026",2)):
        for p in range(1,pages+1):
            j=get({"filter":f+f",publication_year:{yrs},type:article|review|preprint","per_page":200,"page":p,"sort":"cited_by_count:desc","select":SEL})
            rows+=j["results"]; time.sleep(0.2)
    return rows
def src_stats(ids):
    st={}
    ids=list(ids)
    for i in range(0,len(ids),100):
        chunk="|".join(x.split("/")[-1] for x in ids[i:i+100])
        r=requests.get(B+"/sources",params={"filter":f"openalex_id:{chunk}","per_page":100,"select":"id,display_name,type,host_organization_name,summary_stats,is_in_doaj,is_oa"},timeout=90).json()
        for s in r["results"]: st[s["id"]]=s
        time.sleep(0.2)
    return st
for d,f in DOM.items():
    rows=pull(f); print(d,len(rows),file=sys.stderr)
    srcs={(w["primary_location"] or {}).get("source",{}) and w["primary_location"]["source"]["id"] for w in rows if (w.get("primary_location") or {}).get("source")}
    st=src_stats([s for s in srcs if s])
    slim=[]
    for w in rows:
        s=((w.get("primary_location") or {}).get("source") or {})
        ss=st.get(s.get("id"),{})
        sm=ss.get("summary_stats") or {}
        cnp=w.get("citation_normalized_percentile") or {}
        slim.append({"id":w["id"].split("/")[-1],"doi":w.get("doi"),"title":w.get("title"),"year":w["publication_year"],"type":w["type"],
          "cites":w["cited_by_count"],"fwci":w.get("fwci"),"pct":cnp.get("value"),"top10":cnp.get("is_in_top_10_percent"),
          "venue":s.get("display_name"),"venue_type":ss.get("type"),"publisher":ss.get("host_organization_name"),
          "venue_h":sm.get("h_index"),"venue_2yr":sm.get("2yr_mean_citedness"),
          "kw":[k["display_name"] for k in (w.get("keywords") or [])][:6],
          "topic":(w.get("primary_topic") or {}).get("display_name"),
          "first_author":(w["authorships"][0]["author"]["display_name"] if w.get("authorships") else None)})
    # dedupe by lowercased title
    seen,ded={},[]
    for x in sorted(slim,key=lambda x:-(x["cites"] or 0)):
        t=(x["title"] or "").lower().strip()
        if t and t not in seen: seen[t]=1; ded.append(x)
    json.dump(ded,open(os.path.join(OUT,f"{d}.json"),"w"),indent=0)
    print(d,"dedup",len(ded),file=sys.stderr)
