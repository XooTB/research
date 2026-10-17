"""T011: find arXiv versions of T010 papers lacking PDFs (title keyword search + fuzzy title match)."""
import sqlite3,json,re,time,difflib,sys,requests,xml.etree.ElementTree as ET
db,out=sys.argv[1],sys.argv[2]
c=sqlite3.connect(db); c.row_factory=sqlite3.Row
rows=c.execute("select id,title,topic from papers where topic in ('blockchain-fl','blockchain-supply-chain','blockchain-carbon') and (pdf_path is null or pdf_path='')").fetchall()
STOP=set("a an the of for and in on with via to based using by from towards toward its is are at as or into under".split())
norm=lambda s:re.sub(r"[^a-z0-9 ]"," ",(s or "").lower()).split()
NS={"a":"http://www.w3.org/2005/Atom"}
found=[]
for r in rows:
    words=[w for w in norm(r["title"]) if w not in STOP and len(w)>2][:7]
    q=" AND ".join(f"ti:{w}" for w in words)
    for attempt in range(3):
        try:
            x=requests.get("http://export.arxiv.org/api/query",params={"search_query":q,"max_results":5},timeout=60)
            if x.status_code!=200: raise RuntimeError(x.status_code)
            best=(0,None,None)
            for e in ET.fromstring(x.text).findall("a:entry",NS):
                t=" ".join(e.find("a:title",NS).text.split())
                s=difflib.SequenceMatcher(None," ".join(norm(t))," ".join(norm(r["title"]))).ratio()
                if s>best[0]: best=(s,e.find("a:id",NS).text.split("/abs/")[-1],t)
            if best[0]>=0.88:
                found.append({"db_id":r["id"],"topic":r["topic"],"title":r["title"],"arxiv_title":best[2],"score":round(best[0],3),"pdf_url":f"https://arxiv.org/pdf/{best[1]}"})
                print("HIT",round(best[0],2),best[1],r["title"][:60],file=sys.stderr)
            break
        except Exception as ex:
            print("retry",ex,file=sys.stderr); time.sleep(10)
    time.sleep(3.1)
json.dump(found,open(out,"w"),indent=1)
print(json.dumps({"missing":len(rows),"arxiv_hits":len(found)}))
