import requests,time
B="https://api.openalex.org/works"
def n(f):
    r=requests.get(B,params={"filter":f,"per_page":1},timeout=60).json(); time.sleep(0.2); return r["meta"]["count"]
Y="publication_year:2025"
print("== A. query semantics (2025)")
a=n(f"title_and_abstract.search:blockchain,{Y}")
h=n(f"title_and_abstract.search:healthcare,{Y}")
ah=n(f"title_and_abstract.search:blockchain AND healthcare,{Y}")
aoh=n(f"title_and_abstract.search:blockchain OR healthcare,{Y}")
print(f"blockchain={a} healthcare={h} AND={ah} OR={aoh}  check AND+OR==A+B: {ah+aoh==a+h} ({ah+aoh} vs {a+h})")
p=n(f'title_and_abstract.search:"supply chain",{Y}'); s=n(f"title_and_abstract.search:supply chain,{Y}")
print(f'"supply chain" phrase={p} vs unquoted={s}')
llm=n(f'title_and_abstract.search:blockchain AND (LLM),{Y}'); llm2=n(f'title_and_abstract.search:blockchain AND ("large language model"),{Y}')
print(f"blockchain AND LLM={llm}, AND 'large language model'={llm2}")
print("== B. indexing growth: all OpenAlex works by year")
r=requests.get(B,params={"filter":"publication_year:2018-2025","group_by":"publication_year"},timeout=60).json()
print({g["key"]:g["count"] for g in sorted(r["group_by"],key=lambda g:g["key"])})
print("== blockchain by type 2022 vs 2025")
for y in (2022,2025):
    r=requests.get(B,params={"filter":f"title_and_abstract.search:blockchain,publication_year:{y}","group_by":"type"},timeout=60).json()
    print(y,{g["key_display_name"]:g["count"] for g in r["group_by"][:6]})
