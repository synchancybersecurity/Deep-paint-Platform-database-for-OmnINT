import re,json,time,random,os,urllib.request,urllib.parse,threading
from concurrent.futures import ThreadPoolExecutor,as_completed
from display_core import Colors,ok,info,warn,err

class DDGScraper:
    BASE="https://lite.duckduckgo.com/lite/"
    H={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0","Accept":"text/html","Content-Type":"application/x-www-form-urlencoded"}
    def __init__(self,delay=1.5,jitter=0.5):self.delay=delay;self.jitter=jitter;self._last=0
    def _sleep(self):
        e=time.time()-self._last;n=self.delay+random.uniform(0,self.jitter)
        if e<n:time.sleep(n-e)
        self._last=time.time()
    def search(self,q,max_results=10):
        self._sleep();d=urllib.parse.urlencode({"q":q,"kl":"us-en"}).encode()
        r=urllib.request.Request(self.BASE,data=d,headers=self.H,method="POST")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(r,timeout=30) as resp:h=resp.read().decode("utf-8","ignore")
                return self._parse(h,max_results)
            except Exception as e:
                if attempt<<2:time.sleep(2+attempt*2);continue
                return[{"title":"TIMEOUT","url":"","snippet":""}]
        return[{"title":"TIMEOUT","url":"","snippet":""}]
    def _parse(self,html,m):
        o=[];l=re.findall(r'<a[^>]+class="result-link"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',html,re.S)
        s=re.findall(r'<td[^>]*class="result-snippet"[^>]*>(.*?)</td>',html,re.S)
        for i,(href,title) in enumerate(l[:m]):
            t=re.sub(r'<[^>]+>','',title).strip()
            sn=re.sub(r'<[^>]+>','',s[i]).strip() if i<len(s) else ""
            o.append({"title":t,"url":urllib.parse.unquote(href),"snippet":sn})
        return o

class PlatformScanner:
    def __init__(self,platforms=None,workers=5,ddg_delay=1.5):
        self.ddg=DDGScraper(delay=ddg_delay);self.workers=min(max(workers,1),30)
        self.lock=threading.Lock();self.results={};self.platforms=platforms or self._load()
    def _load(self):
        b=os.path.dirname(os.path.abspath(__file__))
        for p in["platforms/sites_db.json","sites_db.json","../Deep-paint-Platform-database-for-OmnINT/sites_db.json"]:
            fp=os.path.join(b,p)
            if os.path.exists(fp):
                with open(fp,"r",encoding="utf-8") as f:raw=json.load(f)
                o=[]
                for name,url in raw.items():
                    dm=re.search(r'https?://(?:www\.)?([^/]+)',url)
                    dm=dm.group(1) if dm else name.lower().replace(" ","")
                    o.append({"name":name,"url":url,"q":f"site:{dm} {{}}"})
                ok(f"Loaded {len(o)} platforms from {fp}");return o
        warn("No DB found, using fallback");return[{"name":"GitHub","url":"https://github.com/{}","q":"site:github.com {}"},{"name":"Twitter","url":"https://x.com/{}","q":"site:x.com {}"}]
    def _one(self,target,p):
        q=p["q"].format(target);h=self.ddg.search(q,5)
        e={"platform":p["name"],"direct_url":p["url"].format(target),"query":q,"hits":h,"timestamp":time.strftime("%Y-%m-%d %H:%M:%S"),"confidence":0.0}
        if h and"ERROR"not in h[0].get("url",""):e["confidence"]=min(0.3+len(h)*0.15,0.95)
        with self.lock:self.results[p["name"]]=e
        return e
    def scan(self,target,platforms=None,callback=None):
        pl=platforms or self.platforms;info(f"Scanning {len(pl)} platforms for '{target}' with {self.workers} workers...")
        with ThreadPoolExecutor(max_workers=self.workers) as ex:
            f={ex.submit(self._one,target,p):p for p in pl}
            for fu in as_completed(f):
                try:
                    e=fu.result()
                    if callback:callback(e)
                    else:self._print(e)
                except Exception as x:err(f"Error: {x}")
        ok(f"Done. {len(self.results)} checked.");return self.results
    def _print(self,e):
        c=Colors;conf=e["confidence"];col=c.GREEN if conf>0.7 else c.YELLOW if conf>0.3 else c.RED
        print(f"\n  {c.BOLD}{e['platform']}{c.RESET} {col}[{conf:.0%}]{c.RESET}")
        print(f"  {c.DIM}{e['direct_url']}{c.RESET}")
        for h in e["hits"][:3]:print(f"    {c.CYAN}>{c.RESET} {h.get('title','')[:60]}\n      {c.DIM}{h.get('url','')[:70]}{c.RESET}")
    def report(self,fmt="json"):
        if fmt=="json":return json.dumps(self.results,indent=2)
        o=["# OmnINT Report",""]
        for n,e in sorted(self.results.items()):
            o+=[f"## {n} ({e['confidence']:.0%})",f"- Direct: {e['direct_url']}",f"- Query: `{e['query']}`"]
            for h in e["hits"][:3]:o.append(f"- [{h.get('title','')}]({h.get('url','')})")
            o.append("")
        return"\n".join(o)
    def save(self,path="scan_report.json"):
        with open(path,"w") as f:f.write(self.report("json"))
        ok(f"Saved: {path}")

if __name__=="__main__":
    import sys
    t=sys.argv[1] if len(sys.argv)>1 else "testuser"
    ps=PlatformScanner(workers=5);ps.scan(t);print(ps.report("md"))
