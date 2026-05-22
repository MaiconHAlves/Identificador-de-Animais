"""Servidor HTTP local que serve LIVE_LOG.md com auto-scroll."""
import http.server, os, threading, webbrowser

LOG = os.path.join(os.path.dirname(__file__), "LIVE_LOG.md")
PORT = 8765

HTML = """<!DOCTYPE html><html><head><meta charset="utf-8">
<title>LIVE LOG</title>
<style>
  body{background:#0d1117;color:#c9d1d9;font-family:monospace;font-size:13px;margin:0;padding:10px;}
  pre{white-space:pre-wrap;word-break:break-all;}
  #status{position:fixed;top:6px;right:10px;font-size:11px;color:#58a6ff;}
  .head{color:#f0883e;font-weight:bold;}
  .ok{color:#56d364;}
  .err{color:#f85149;}
  .warn{color:#e3b341;}
</style></head><body>
<span id="status">conectando...</span>
<pre id="log"></pre>
<script>
let last="", paused=false;
document.addEventListener("keydown",e=>{if(e.key===" ")paused=!paused;});
async function poll(){
  try{
    const r=await fetch("/log?t="+Date.now());
    const txt=await r.text();
    if(txt!==last){
      last=txt;
      const el=document.getElementById("log");
      el.innerHTML=txt
        .replace(/&/g,"&amp;").replace(/</g,"&lt;")
        .replace(/(==>.*<==)/g,'<span class="head">$1</span>')
        .replace(/(GREEN LIGHT|SUCCESS|OK\]|carregada)/g,'<span class="ok">$1</span>')
        .replace(/(ERRO|ERROR|FAIL|crash)/gi,'<span class="err">$1</span>')
        .replace(/(WARN|WARNING)/gi,'<span class="warn">$1</span>');
      if(!paused) window.scrollTo(0,document.body.scrollHeight);
      document.getElementById("status").textContent=
        (paused?"[PAUSADO] ":"[LIVE] ")+new Date().toLocaleTimeString();
    }
  }catch(e){}
  setTimeout(poll,1500);
}
poll();
</script></body></html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/log"):
            try:
                with open(LOG, encoding="utf-8", errors="replace") as f:
                    data = f.read().encode()
            except:
                data = b"aguardando log..."
            self.send_response(200)
            self.send_header("Content-Type","text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(data)
        else:
            self.send_response(200)
            self.send_header("Content-Type","text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML.encode())
    def log_message(self, *_): pass

print(f"LIVE LOG → http://localhost:{PORT}")
threading.Timer(1, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
http.server.HTTPServer(("", PORT), Handler).serve_forever()
