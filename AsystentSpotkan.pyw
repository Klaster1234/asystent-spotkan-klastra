# -*- coding: utf-8 -*-
"""Asystent Spotkań Klastra - transkrypcja mowy (Whisper, lokalnie).
Nagranie z mikrofonu lub plik audio/wideo -> tekst (.txt) + napisy (.srt).
Lekki, bez zewnętrznych usług. Interfejs webowy (WebView2).
"""
import os
import time
import wave
import base64
import threading
import subprocess

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
RECDIR = os.path.join(USER, "Documents", "Transkrypcje")
CREATE_NO_WINDOW = 0x08000000
LANGS = {"Polski": "pl", "Angielski": "en", "Automatyczny": "auto"}

WINDOW = None


def _js(code):
    if WINDOW:
        try:
            WINDOW.evaluate_js(code)
        except Exception:
            pass


def ui(fn, *args):
    import json
    _js("ui.%s(%s)" % (fn, ",".join(json.dumps(a) for a in args)))


class Api:
    def __init__(self):
        self.lang = "pl"
        self.busy = False
        self.recording = False
        self.frames = []
        self.stream = None
        self.txt_path = None

    def set_lang(self, code):
        self.lang = code

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
            ui("status", "Nagranie za krótkie - spróbuj ponownie.")
            return
        os.makedirs(RECDIR, exist_ok=True)
        path = os.path.join(RECDIR, time.strftime("nagranie_%Y%m%d_%H%M%S.wav"))
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(data)
        threading.Thread(target=self._process, args=(path,), daemon=True).start()

    def open_folder(self):
        if self.txt_path and os.path.exists(self.txt_path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self.txt_path)])

    def _process(self, path):
        self.busy = True
        self.txt_path = None
        ui("busy", True)
        ui("status", "Przepisuję: " + os.path.basename(path) + " …")
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
        self.busy = False
        ui("busy", False)
        if not content:
            ui("status", "Nie wykryto mowy w pliku.")
            return
        self.txt_path = txt
        ui("transcript", content)
        ui("status", "Gotowe. Zapisano: " + os.path.basename(txt) + "  (oraz .srt)")


def _data_uri(name):
    p = os.path.join(ASSETS, name)
    try:
        with open(p, "rb") as f:
            return "data:image/png;base64," + base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""


def build_html():
    opts = "".join("<option value='%s'>%s</option>" % (c, n) for n, c in LANGS.items())
    html = HTML_TEMPLATE
    html = html.replace("__LOGO__", _data_uri("logo.png")).replace("__KLASTUS__", _data_uri("klastus.png"))
    html = html.replace("__LANGOPTS__", opts).replace("__MIC__", "true" if MIC else "false")
    return html


HTML_TEMPLATE = r"""
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#fff;--cream:#F7F6F3;--line:#ECEAE4;--text:#37352F;--muted:#8A8782;--accent:#E07B54;--accentd:#C96A45;--dark:#2E2B27;}
*{box-sizing:border-box;}
html,body{margin:0;height:100%;}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);
  -webkit-font-smoothing:antialiased;display:flex;flex-direction:column;}
.wrap{max-width:920px;width:100%;margin:0 auto;padding:22px 28px 18px;display:flex;flex-direction:column;flex:1;min-height:0;}
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
.btn-primary{background:var(--accent);color:#fff;padding:12px 22px;}
.btn-primary:hover{background:var(--accentd);}
.btn-primary.on{background:#DC2626;}
.btn-ghost{background:transparent;color:var(--text);border:1px solid var(--line);padding:11px 18px;font-weight:500;}
.btn-ghost:hover{background:var(--cream);}
.btn-ghost:disabled{opacity:.4;cursor:default;}
.spacer{margin-left:auto;}
.lang{display:flex;align-items:center;gap:7px;font-size:13px;color:var(--muted);}
select{font-family:inherit;font-size:13px;color:var(--text);background:var(--bg);border:1px solid var(--line);
  border-radius:8px;padding:7px 8px;}
.statusrow{margin-top:18px;font-size:13px;color:var(--muted);min-height:18px;}
.prog{height:3px;background:var(--cream);border-radius:2px;margin:8px 0 14px;overflow:hidden;}
.prog>i{display:block;height:100%;width:30%;background:var(--accent);border-radius:2px;transform:translateX(-120%);}
.prog.run>i{animation:slide 1.1s infinite ease-in-out;}
@keyframes slide{0%{transform:translateX(-120%);}100%{transform:translateX(420%);}}
.panel{flex:1;min-height:0;border-top:1px solid var(--line);padding-top:14px;overflow:auto;}
.hint{color:var(--muted);font-size:14px;padding:26px 2px;}
#tr{white-space:pre-wrap;font-size:15px;line-height:1.65;}
.foot{display:flex;align-items:center;gap:10px;padding-top:12px;border-top:1px solid var(--line);margin-top:6px;}
.foot .info{margin-left:auto;font-size:11.5px;color:var(--muted);}
</style></head>
<body><div class="wrap">
  <div class="head">
    <img class="logo" src="__LOGO__">
    <div><div class="title">Asystent Spotkań</div>
    <div class="sub">Klaster Innowacji Społecznych · transkrypcja · 100% lokalnie</div></div>
    <img class="klastus" src="__KLASTUS__">
  </div>
  <div class="rule"></div>

  <div class="bar">
    <button class="btn-primary" id="rec">Nagraj głos</button>
    <button class="btn-ghost" id="pick">Wybierz plik…</button>
    <div class="spacer"></div>
    <div class="lang">Język <select id="lang">__LANGOPTS__</select></div>
  </div>

  <div class="statusrow" id="status">Gotowe - nagraj głos lub wczytaj plik, a zamienię go w tekst.</div>
  <div class="prog" id="prog"><i></i></div>

  <div class="panel">
    <div class="hint" id="hint">Tu pojawi się transkrypcja. Tekst zapisze się automatycznie obok nagrania (.txt), powstaną też napisy (.srt).</div>
    <div id="tr"></div>
  </div>

  <div class="foot">
    <button class="btn-ghost" id="copy" disabled>Kopiuj tekst</button>
    <button class="btn-ghost" id="open" disabled>Otwórz folder wyniku</button>
    <div class="info">Pliki .txt (tekst) i .srt (napisy) powstają obok nagrania.</div>
  </div>
</div>
<script>
const MIC=__MIC__;
const $=id=>document.getElementById(id);
let recOn=false, recT=null, recS=0;
function api(){return window.pywebview && window.pywebview.api;}
$('rec').onclick=()=>{
  if(!MIC){ui.error('Brak mikrofonu.');return;}
  if(!recOn){ api().start_recording().then(ok=>{ if(ok){recOn=true;recS=0;$('rec').classList.add('on');$('rec').textContent='Zatrzymaj i przepisz';$('pick').disabled=true;
      recT=setInterval(()=>{recS++;ui.status('Nagrywam… '+String(Math.floor(recS/60)).padStart(2,'0')+':'+String(recS%60).padStart(2,'0')+' - kliknij Zatrzymaj, gdy skończysz.');},1000);} }); }
  else{ recOn=false;clearInterval(recT);$('rec').classList.remove('on');$('rec').textContent='Nagraj głos'; api().stop_and_process(); }
};
$('pick').onclick=()=>api().choose_and_process();
$('lang').onchange=e=>api().set_lang(e.target.value);
$('copy').onclick=()=>{navigator.clipboard.writeText(($('tr').innerText||'').trim());ui.status('Skopiowano do schowka.');};
$('open').onclick=()=>api().open_folder();
window.ui={
  busy(b){$('prog').classList.toggle('run',b);$('rec').disabled=b&&!recOn;$('pick').disabled=b;},
  status(t){$('status').textContent=t;},
  error(t){$('status').textContent='Błąd: '+t;},
  transcript(t){$('hint').style.display='none';$('tr').textContent=t;$('copy').disabled=false;$('open').disabled=false;},
};
</script></body></html>
"""


def main():
    global WINDOW
    api = Api()
    WINDOW = webview.create_window("Asystent Spotkań Klastra", html=build_html(),
                                   js_api=api, width=900, height=660, min_size=(760, 540),
                                   background_color="#FFFFFF")
    webview.start()


if __name__ == "__main__":
    main()
