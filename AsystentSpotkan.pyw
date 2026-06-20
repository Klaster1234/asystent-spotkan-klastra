# -*- coding: utf-8 -*-
"""Asystent Spotkań Klastra — Whisper + Qwen (lokalnie).
Nowoczesny interfejs webowy (WebView2) + lokalny silnik.
Nagranie/plik -> transkrypcja (Whisper) -> raport z rozmowy (Qwen, strumieniowany).
"""
import os
import time
import json
import wave
import base64
import threading
import subprocess
import urllib.request

import webview

try:
    import sounddevice as sd
    MIC = True
except Exception:
    MIC = False

USER = os.path.expanduser("~")
WDIR = os.path.join(USER, "whisper")
ASSETS = os.path.join(WDIR, "assets")
CLI = os.path.join(WDIR, "bin", "Release", "whisper-cli.exe")
MODEL = os.path.join(WDIR, "models", "ggml-large-v3-turbo-q5_0.bin")
LMS_EXE = os.path.join(USER, ".lmstudio", "bin", "lms.exe")
RECDIR = os.path.join(USER, "Documents", "Transkrypcje")
API = "http://localhost:1234/api/v0"
CREATE_NO_WINDOW = 0x08000000
LANGS = {"Polski": "pl", "Angielski": "en", "Automatyczny": "auto"}

SYS_PROMPT = ("Jesteś asystentem Klastra Innowacji Społecznych. Analizujesz transkrypcje rozmów "
              "i tworzysz zwięzłe, konkretne raporty po polsku.")
REPORT_PROMPT = """Na podstawie poniższej transkrypcji rozmowy przygotuj zwięzły raport w Markdown.
Sekcje (pomiń puste): ## Podsumowanie (2-3 zdania), ## Najważniejsze punkty, ## Decyzje i ustalenia,
## Zadania do wykonania (format: - [ ] zadanie — osoba — termin), ## Pytania otwarte.
Pisz bardzo zwięźle, krótkie punkty, bez lania wody.

TRANSKRYPCJA:
"""

WINDOW = None


def lm_models():
    try:
        with urllib.request.urlopen(API + "/models", timeout=5) as r:
            return [m for m in json.load(r).get("data", []) if m.get("type") == "llm"]
    except Exception:
        return None


def lm_pick_model(models):
    if not models:
        return None
    for m in models:
        if m.get("state") == "loaded":
            return m["id"]
    for m in models:
        if "qwen" in m["id"].lower():
            return m["id"]
    return models[0]["id"]


def lm_stream(model, system, user, timeout=900):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.3, "max_tokens": 700, "stream": True,
    }).encode("utf-8")
    req = urllib.request.Request(API + "/chat/completions", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        for raw in r:
            line = raw.decode("utf-8", "replace").strip()
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                break
            try:
                delta = json.loads(data)["choices"][0]["delta"].get("content", "")
            except Exception:
                delta = ""
            if delta:
                yield delta


def md_to_text(md):
    out = []
    for raw in md.splitlines():
        s = raw.strip().replace("**", "").replace("`", "").replace("—", "-")
        if not s:
            if out and out[-1] != "":
                out.append("")
        elif s.startswith("#"):
            t = s.lstrip("#").strip()
            if out and out[-1] != "":
                out.append("")
            out.append(t.upper())
        elif s[:5] in ("- [ ]", "- [x]", "- [X]"):
            out.append("  [ ] " + s[5:].strip())
        elif s[:2] in ("- ", "* "):
            out.append("  - " + s[2:].strip())
        else:
            out.append(s)
    return "\n".join(out).strip() + "\n"


def save_report(report, txt_path):
    stamp = time.strftime("%Y-%m-%d %H:%M")
    if txt_path:
        name = os.path.splitext(os.path.basename(txt_path))[0]
        folder = os.path.dirname(txt_path)
    else:
        name = time.strftime("rozmowa_%Y%m%d_%H%M%S")
        folder = RECDIR
        os.makedirs(folder, exist_ok=True)
    body = "RAPORT Z ROZMOWY\n%s\n%s\n\n%s" % (name, stamp, md_to_text(report))
    path = os.path.join(folder, name + " - raport.txt")
    with open(path, "w", encoding="utf-8") as f:
        f.write(body)
    return path


def _js(code):
    if WINDOW:
        try:
            WINDOW.evaluate_js(code)
        except Exception:
            pass


def ui(fn, *args):
    _js("ui.%s(%s)" % (fn, ",".join(json.dumps(a) for a in args)))


class Api:
    def __init__(self):
        self.lang = "pl"
        self.auto = True
        self.busy = False
        self.recording = False
        self.frames = []
        self.stream = None
        self.transcript = ""
        self.txt_path = None

    def set_lang(self, code):
        self.lang = code

    def set_auto(self, val):
        self.auto = bool(val)

    # ---------- plik ----------
    def choose_and_process(self):
        if self.busy or self.recording:
            return
        res = WINDOW.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=False,
            file_types=("Audio / Wideo (*.mp3;*.wav;*.m4a;*.mp4;*.mkv;*.flac;*.ogg;*.opus;*.mov;*.avi;*.webm)",
                        "Wszystkie pliki (*.*)"))
        if res:
            path = res[0] if isinstance(res, (list, tuple)) else res
            threading.Thread(target=self._process, args=(path,), daemon=True).start()

    # ---------- nagrywanie ----------
    def start_recording(self):
        if self.busy or not MIC:
            return False
        self.frames = []
        try:
            self.stream = sd.RawInputStream(samplerate=16000, channels=1, dtype="int16",
                                            callback=lambda i, f, t, s: self.frames.append(bytes(i)))
            self.stream.start()
        except Exception as e:
            ui("error", "Mikrofon: " + str(e))
            return False
        self.recording = True
        return True

    def stop_and_process(self):
        if not self.recording:
            return
        self.recording = False
        try:
            self.stream.stop(); self.stream.close()
        except Exception:
            pass
        data = b"".join(self.frames)
        if len(data) < 16000 * 2:
            ui("status", "Nagranie za krótkie — spróbuj ponownie.")
            return
        os.makedirs(RECDIR, exist_ok=True)
        path = os.path.join(RECDIR, time.strftime("nagranie_%Y%m%d_%H%M%S.wav"))
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(data)
        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    # ---------- raport ręcznie ----------
    def run_report(self):
        if self.busy or not self.transcript:
            return
        threading.Thread(target=self._report, args=(self.transcript, self.txt_path), daemon=True).start()

    def open_folder(self):
        if self.txt_path and os.path.exists(self.txt_path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.txt_path)])

    # ---------- logika ----------
    def _process(self, path):
        self.busy = True
        self.transcript = ""
        self.txt_path = None
        ui("busy", True)
        ui("step", 2)
        ui("status", "Transkrypcja: " + os.path.basename(path) + " …")
        base = os.path.splitext(path)[0]
        try:
            subprocess.run([CLI, "-m", MODEL, "-l", self.lang, "-t", "16", "-otxt", "-osrt", "-of", base, "-f", path],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=CREATE_NO_WINDOW)
            txt = base + ".txt"
            content = ""
            if os.path.exists(txt):
                with open(txt, "r", encoding="utf-8") as fh:
                    content = fh.read().strip()
        except Exception as e:
            ui("error", "Transkrypcja: " + str(e)); ui("busy", False); self.busy = False
            return
        if not content:
            ui("status", "Nie wykryto mowy w pliku."); ui("busy", False); self.busy = False
            ui("step", 1)
            return
        self.transcript = content
        self.txt_path = txt
        ui("transcript", content)
        ui("status", "Transkrypcja gotowa: " + os.path.basename(txt))
        if self.auto:
            self._report(content, txt)
        else:
            ui("busy", False); self.busy = False
            ui("step", 2)

    def _ensure_models(self):
        m = lm_models()
        if m is None and os.path.exists(LMS_EXE):
            try:
                subprocess.run([LMS_EXE, "server", "start"], creationflags=CREATE_NO_WINDOW,
                               timeout=30, capture_output=True)
                time.sleep(2)
                m = lm_models()
            except Exception:
                pass
        return m

    def _report(self, transcript, txt_path):
        self.busy = True
        ui("busy", True)
        ui("step", 3)
        ui("reportStart")
        ui("status", "Generuję raport modelem Qwen …")
        try:
            models = self._ensure_models()
            if not models:
                ui("error", "Serwer LM Studio nie odpowiada. Uruchom aplikację LM Studio.")
                ui("busy", False); self.busy = False
                return
            model = lm_pick_model(models)
            chunks = []
            for delta in lm_stream(model, SYS_PROMPT, REPORT_PROMPT + transcript):
                chunks.append(delta)
                ui("reportDelta", delta)
            report = "".join(chunks).strip()
            path = save_report(report, txt_path)
            ui("reportDone", report)
            ui("status", "Raport gotowy. Zapisano: " + os.path.basename(path))
        except Exception as e:
            ui("error", "Raport: " + str(e))
        finally:
            ui("busy", False); self.busy = False


def _data_uri(name):
    p = os.path.join(ASSETS, name)
    try:
        with open(p, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""


def build_html():
    logo = _data_uri("logo.png")
    klastus = _data_uri("klastus.png")
    opts = "".join("<option value='%s'>%s</option>" % (c, n) for n, c in LANGS.items())
    html = HTML_TEMPLATE
    html = html.replace("__LOGO__", logo).replace("__KLASTUS__", klastus).replace("__LANGOPTS__", opts)
    html = html.replace("__MIC__", "true" if MIC else "false")
    return html


def _prewarm():
    try:
        m = lm_models()
        if m:
            model = lm_pick_model(m)
            list(lm_stream(model, "ok", "ok", timeout=60))
    except Exception:
        pass


HTML_TEMPLATE = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#fff;--cream:#F7F6F3;--line:#ECEAE4;--text:#37352F;--muted:#8A8782;--accent:#E07B54;--accentd:#C96A45;--dark:#2E2B27;}
*{box-sizing:border-box;}
html,body{margin:0;height:100%;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);
  -webkit-font-smoothing:antialiased;display:flex;flex-direction:column;}
.wrap{max-width:980px;width:100%;margin:0 auto;padding:22px 28px 18px;display:flex;flex-direction:column;flex:1;min-height:0;}
.head{display:flex;align-items:center;gap:13px;}
.logo{width:40px;height:40px;border-radius:10px;object-fit:contain;}
.title{font-size:20px;font-weight:600;line-height:1.15;}
.sub{font-size:12.5px;color:var(--muted);}
.klastus{width:46px;height:46px;margin-left:auto;object-fit:contain;}
.rule{height:3px;background:var(--accent);border-radius:2px;margin:14px 0 18px;}
.bar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;}
button{font-family:inherit;cursor:pointer;border:none;border-radius:10px;font-size:14px;font-weight:600;
  transition:background .12s,transform .04s;}
button:active{transform:scale(.98);}
.btn-primary{background:var(--accent);color:#fff;padding:11px 20px;display:inline-flex;align-items:center;gap:9px;}
.btn-primary:hover{background:var(--accentd);}
.btn-rec{background:var(--dark);color:#fff;padding:11px 20px;display:inline-flex;align-items:center;gap:9px;}
.btn-rec:hover{background:#1f1d1a;}
.btn-rec.on{background:#DC2626;}
.btn-ghost{background:transparent;color:var(--text);border:1px solid var(--line);padding:10px 16px;font-weight:500;}
.btn-ghost:hover{background:var(--cream);}
.btn-ghost:disabled{opacity:.4;cursor:default;}
.spacer{margin-left:auto;}
.lang{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--muted);}
select{font-family:inherit;font-size:13px;color:var(--text);background:var(--bg);border:1px solid var(--line);
  border-radius:8px;padding:6px 8px;}
.opt{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text);margin-top:12px;user-select:none;cursor:pointer;}
.opt input{accent-color:var(--accent);width:16px;height:16px;}
.statusrow{margin-top:16px;font-size:13px;color:var(--muted);min-height:18px;}
.prog{height:3px;background:var(--cream);border-radius:2px;margin:8px 0 14px;overflow:hidden;}
.prog>i{display:block;height:100%;width:30%;background:var(--accent);border-radius:2px;transform:translateX(-120%);}
.prog.run>i{animation:slide 1.1s infinite ease-in-out;}
@keyframes slide{0%{transform:translateX(-120%);}100%{transform:translateX(420%);}}
.tabs{display:inline-flex;background:var(--cream);border-radius:10px;padding:3px;gap:3px;}
.tab{font-size:13px;font-weight:500;color:var(--muted);padding:6px 16px;border-radius:8px;cursor:pointer;}
.tab.act{background:var(--bg);color:var(--text);box-shadow:0 1px 2px rgba(0,0,0,.06);}
.panes{flex:1;min-height:0;margin-top:14px;border-top:1px solid var(--line);padding-top:12px;overflow:auto;}
.pane{display:none;}
.pane.act{display:block;}
.hint{color:var(--muted);font-size:14px;padding:24px 2px;}
#tr{white-space:pre-wrap;font-size:15px;line-height:1.6;}
.rpt h3{color:var(--accentd);font-size:13.5px;font-weight:600;letter-spacing:.02em;margin:18px 0 6px;}
.rpt h3:first-child{margin-top:2px;}
.rpt p{font-size:15px;line-height:1.65;margin:0 0 10px;}
.rpt ul{margin:0 0 12px;padding-left:4px;list-style:none;}
.rpt li{font-size:15px;line-height:1.55;margin:3px 0;display:flex;gap:9px;}
.rpt li .dot{color:var(--accent);}
.rpt .task{font-size:15px;line-height:1.5;margin:5px 0;display:flex;gap:9px;align-items:flex-start;font-weight:500;}
.rpt .box{width:15px;height:15px;border:1.5px solid var(--muted);border-radius:4px;flex:none;margin-top:2px;}
.rpt .meta{color:var(--muted);font-weight:400;}
#rawrpt{white-space:pre-wrap;font-size:14px;line-height:1.6;color:var(--text);}
.foot{display:flex;align-items:center;gap:10px;padding-top:12px;border-top:1px solid var(--line);margin-top:6px;}
.foot .info{margin-left:auto;font-size:11.5px;color:var(--muted);}
</style></head>
<body><div class="wrap">
  <div class="head">
    <img class="logo" src="__LOGO__">
    <div><div class="title">Asystent Spotkań</div>
    <div class="sub">Klaster Innowacji Społecznych · 100% lokalnie</div></div>
    <img class="klastus" src="__KLASTUS__">
  </div>
  <div class="rule"></div>

  <div class="bar">
    <button class="btn-rec" id="rec">Nagraj głos</button>
    <button class="btn-ghost" id="pick">Wybierz plik…</button>
    <div class="spacer"></div>
    <div class="lang">Język
      <select id="lang">__LANGOPTS__</select></div>
  </div>
  <label class="opt"><input type="checkbox" id="auto" checked> Po transkrypcji od razu zrób raport (Qwen)
    <button class="btn-ghost" id="dorpt" style="margin-left:12px;padding:6px 12px;font-size:12.5px;" disabled>Zrób raport teraz</button>
  </label>

  <div class="statusrow" id="status">Gotowe — zacznij od nagrania lub wczytania pliku.</div>
  <div class="prog" id="prog"><i></i></div>

  <div class="tabs">
    <div class="tab act" id="t-tr" data-p="tr">Transkrypcja</div>
    <div class="tab" id="t-rp" data-p="rp">Raport</div>
  </div>
  <div class="panes">
    <div class="pane act" id="p-tr"><div class="hint" id="h-tr">Tu pojawi się transkrypcja Twojego nagrania.</div><div id="tr"></div></div>
    <div class="pane" id="p-rp"><div class="hint" id="h-rp">Tu pojawi się raport z rozmowy (podsumowanie, decyzje, zadania).</div><div class="rpt" id="rpt"></div><div id="rawrpt"></div></div>
  </div>

  <div class="foot">
    <button class="btn-ghost" id="copy" disabled>Kopiuj</button>
    <button class="btn-ghost" id="open" disabled>Otwórz folder wyniku</button>
    <div class="info">Wyniki zapisują się obok nagrania: tekst (.txt), napisy (.srt), raport (.txt).</div>
  </div>
</div>
<script>
const MIC=__MIC__;
const $=id=>document.getElementById(id);
let recOn=false, recT=null, recS=0, raw="";
function api(){return window.pywebview && window.pywebview.api;}
function setTab(p){
  document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('act',t.dataset.p===p));
  $('p-tr').classList.toggle('act',p==='tr'); $('p-rp').classList.toggle('act',p==='rp');
}
document.querySelectorAll('.tab').forEach(t=>t.onclick=()=>setTab(t.dataset.p));

$('rec').onclick=()=>{
  if(!MIC){ui.error('Brak mikrofonu.');return;}
  if(!recOn){ api().start_recording().then(ok=>{ if(ok){recOn=true;recS=0;$('rec').classList.add('on');$('rec').textContent='Zatrzymaj i przepisz';
      recT=setInterval(()=>{recS++;ui.status('Nagrywam… '+String(Math.floor(recS/60)).padStart(2,'0')+':'+String(recS%60).padStart(2,'0')+' — kliknij Zatrzymaj, gdy skończysz.');},1000);} }); }
  else{ recOn=false;clearInterval(recT);$('rec').classList.remove('on');$('rec').textContent='Nagraj głos'; api().stop_and_process(); }
};
$('pick').onclick=()=>api().choose_and_process();
$('dorpt').onclick=()=>api().run_report();
$('lang').onchange=e=>api().set_lang(e.target.value);
$('auto').onchange=e=>api().set_auto(e.target.checked);
$('copy').onclick=()=>{const act=$('p-rp').classList.contains('act');const t=act?($('rpt').innerText||raw):$('tr').innerText;navigator.clipboard.writeText((t||'').trim());ui.status('Skopiowano do schowka.');};
$('open').onclick=()=>api().open_folder();

function renderMd(md){
  const lines=md.split('\n');let html='';let inUl=false;
  const esc=s=>s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/\*\*/g,'').replace(/`/g,'').replace(/—/g,'-');
  const closeUl=()=>{if(inUl){html+='</ul>';inUl=false;}};
  for(let l of lines){const s=l.trim();
    if(!s){continue;}
    if(s.startsWith('#')){closeUl();html+='<h3>'+esc(s.replace(/^#+/,'').trim())+'</h3>';}
    else if(/^- \[[ xX]\]/.test(s)){closeUl();html+='<div class="task"><span class="box"></span><span>'+esc(s.replace(/^- \[[ xX]\]/,'').trim())+'</span></div>';}
    else if(s.startsWith('- ')||s.startsWith('* ')){if(!inUl){html+='<ul>';inUl=true;}html+='<li><span class="dot">•</span><span>'+esc(s.slice(2).trim())+'</span></li>';}
    else{closeUl();html+='<p>'+esc(s)+'</p>';}
  }
  closeUl();return html;
}
const STEPS={1:'Nagraj lub wgraj',2:'Transkrypcja',3:'Raport'};
window.ui={
  busy(b){$('prog').classList.toggle('run',b);$('rec').disabled=b&&!recOn;$('pick').disabled=b;$('dorpt').disabled=b|| !$('tr').innerText;},
  step(n){},
  status(t){$('status').textContent=t;},
  error(t){$('status').textContent='Błąd: '+t;},
  transcript(t){$('h-tr').style.display='none';$('tr').textContent=t;setTab('tr');$('copy').disabled=false;$('open').disabled=false;$('dorpt').disabled=false;},
  reportStart(){raw='';$('h-rp').style.display='none';$('rpt').innerHTML='';$('rawrpt').textContent='';setTab('rp');},
  reportDelta(d){raw+=d;$('rawrpt').textContent=raw;const pn=$('p-rp');pn.scrollTop=pn.scrollHeight;},
  reportDone(md){raw=md;$('rawrpt').textContent='';$('rpt').innerHTML=renderMd(md);$('copy').disabled=false;$('open').disabled=false;},
};
</script></body></html>
"""


def main():
    global WINDOW
    api = Api()
    WINDOW = webview.create_window("Asystent Spotkań Klastra", html=build_html(),
                                   js_api=api, width=960, height=800, min_size=(820, 660),
                                   background_color="#FFFFFF")
    threading.Thread(target=_prewarm, daemon=True).start()
    webview.start()


if __name__ == "__main__":
    main()
