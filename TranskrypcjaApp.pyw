# -*- coding: utf-8 -*-
"""Asystent Spotkan Klastra - Whisper + Qwen (lokalnie).
Nagrywanie/plik -> transkrypcja (Whisper) -> raport z rozmowy (Qwen).
Raport zapisywany jako .md (obok nagrania oraz w vaulcie Obsidian).
Wyglad zgodny z CRM Klastra (paleta terakota / kremowy / grafit)."""
import os
import time
import json
import wave
import urllib.request
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND = True
except Exception:
    DND = False

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

# --- Paleta CRM Klastra (Notion-like, akcent terakota) ---
BG = "#FFFFFF"        # tlo glowne
CREAM = "#F7F6F3"     # panele / secondary
ACCENT_BG = "#EFEDE8" # przyciski neutralne
TEXT = "#37352F"      # grafit
MUTED = "#6E6C69"
PRIMARY = "#E07B54"   # terakota (CTA)
PRIMARY_DK = "#C96A45"
DARK = "#37352F"      # grafitowy przycisk
DARK_DK = "#2A2824"
REC = "#DC2626"       # nagrywanie
BORDER = "#E3E2DE"

DROP_HINT = "Przeciagnij tu plik audio/wideo  —  albo uzyj przyciskow ponizej"
PICK_HINT = "Wybierz plik lub nagraj glos przyciskami ponizej"

SYS_PROMPT = ("Jestes asystentem Klastra Innowacji Spolecznych, ktory analizuje transkrypcje "
              "rozmow i spotkan oraz tworzy zwiezle, konkretne raporty po polsku.")
REPORT_PROMPT = """Przeanalizuj ponizsza transkrypcje rozmowy i przygotuj raport w formacie Markdown. Uzyj dokladnie takich sekcji (pomin sekcje, jesli brak tresci):

## Podsumowanie
(2-4 zdania)

## Najwazniejsze punkty
(lista wypunktowana)

## Decyzje i ustalenia
(lista)

## Zadania do wykonania
(lista w formacie: - [ ] zadanie — osoba odpowiedzialna — termin)

## Pytania otwarte
(jesli sa)

Pisz konkretnie, po polsku, bez lania wody.

TRANSKRYPCJA:
"""


def find_obsidian_vault():
    cfg = os.path.join(os.environ.get("APPDATA", ""), "obsidian", "obsidian.json")
    try:
        with open(cfg, encoding="utf-8") as f:
            data = json.load(f)
        best = None
        for v in data.get("vaults", {}).values():
            p = v.get("path")
            if not p or not os.path.isdir(p):
                continue
            if v.get("open"):
                return p
            best = p
        return best
    except Exception:
        return None


def lm_models():
    try:
        with urllib.request.urlopen(API + "/models", timeout=5) as r:
            data = json.load(r)
        return [m for m in data.get("data", []) if m.get("type") == "llm"]
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


def lm_chat(model, system, user, timeout=900):
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user}],
        "temperature": 0.3,
        "max_tokens": 1500,
    }).encode("utf-8")
    req = urllib.request.Request(API + "/chat/completions", data=payload,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.load(r)
    return data["choices"][0]["message"]["content"].strip()


class App:
    def __init__(self, root):
        self.root = root
        self.busy = False
        self.recording = False
        self.frames = []
        self.stream = None
        self.txt_path = None
        self.transcript = ""
        self.vault = find_obsidian_vault()
        root.title("Asystent Spotkan Klastra  -  Whisper + Qwen")
        root.geometry("860x740")
        root.minsize(740, 620)
        root.configure(bg=BG)
        self._imgs = {}
        try:
            root.iconbitmap(os.path.join(ASSETS, "klaster.ico"))
        except Exception:
            pass
        self._setup_style()

        # ---- Naglowek z logo ----
        head = tk.Frame(root, bg=BG, padx=18, pady=14)
        head.pack(fill="x")
        logo = self._img("logo_header.png")
        if logo:
            tk.Label(head, image=logo, bg=BG).pack(side="left", padx=(0, 12))
        tt = tk.Frame(head, bg=BG)
        tt.pack(side="left", anchor="w")
        tk.Label(tt, text="Asystent Spotkan", font=("Segoe UI", 18, "bold"),
                 bg=BG, fg=TEXT).pack(anchor="w")
        tk.Label(tt, text="Klaster Innowacji Spolecznych · nagranie → transkrypcja → raport · 100% lokalnie",
                 font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor="w")
        klastus = self._img("klastus_small.png")
        if klastus:
            tk.Label(head, image=klastus, bg=BG).pack(side="right")
        tk.Frame(root, bg=PRIMARY, height=3).pack(fill="x")  # terakotowa linia

        # ---- Strefa upuszczania ----
        self.drop = tk.Label(root, text=(DROP_HINT if DND else PICK_HINT),
                             font=("Segoe UI", 11), fg=MUTED, bg=CREAM,
                             relief="flat", bd=0, height=2)
        self.drop.pack(fill="x", padx=18, pady=(12, 8))
        if DND:
            self.drop.drop_target_register(DND_FILES)
            self.drop.dnd_bind("<<Drop>>", self.on_drop)

        # ---- Przyciski glowne ----
        ctr = tk.Frame(root, bg=BG, padx=18)
        ctr.pack(fill="x")
        self.pick_btn = self._btn(ctr, "\U0001F4C2  Wybierz plik…", self.pick, PRIMARY, PRIMARY_DK)
        self.pick_btn.pack(side="left")
        self.rec_btn = self._btn(ctr, "\U0001F3A4  Nagraj glos", self.toggle_record, DARK, DARK_DK)
        self.rec_btn.pack(side="left", padx=8)
        if not MIC:
            self.rec_btn.config(state="disabled", text="\U0001F3A4  (brak mikrofonu)")
        tk.Label(ctr, text="Jezyk:", font=("Segoe UI", 10), bg=BG, fg=TEXT).pack(side="left", padx=(16, 4))
        self.lang = ttk.Combobox(ctr, values=list(LANGS.keys()), state="readonly", width=12)
        self.lang.set("Polski")
        self.lang.pack(side="left")

        # ---- Opcja raportu ----
        ctr2 = tk.Frame(root, bg=BG, padx=18)
        ctr2.pack(fill="x", pady=(10, 0))
        self.auto_report = tk.BooleanVar(value=True)
        tk.Checkbutton(ctr2, text="Po transkrypcji od razu zrob raport (Qwen)",
                       variable=self.auto_report, bg=BG, fg=TEXT, font=("Segoe UI", 10),
                       activebackground=BG, activeforeground=TEXT, selectcolor=BG).pack(side="left")
        self.report_btn = self._btn(ctr2, "\U0001F9E0  Zrob raport teraz", self.run_report, PRIMARY, PRIMARY_DK, small=True)
        self.report_btn.config(state="disabled")
        self.report_btn.pack(side="left", padx=12)

        # ---- Status + pasek ----
        self.status = tk.Label(root, text="Gotowe.", anchor="w", fg=TEXT, bg=BG,
                               padx=18, font=("Segoe UI", 10))
        self.status.pack(fill="x", pady=(12, 0))
        self.pb = ttk.Progressbar(root, mode="indeterminate", style="Klaster.Horizontal.TProgressbar")
        self.pb.pack(fill="x", padx=18, pady=(2, 6))

        # ---- Zakladki ----
        self.nb = ttk.Notebook(root)
        f1, self.text = self._scrolled(self.nb)
        f2, self.report = self._scrolled(self.nb)
        self.nb.add(f1, text="   \U0001F4DD  Transkrypcja   ")
        self.nb.add(f2, text="   \U0001F9E0  Raport (Qwen)   ")
        self.nb.pack(fill="both", expand=True, padx=18, pady=(0, 4))

        # ---- Dolny pasek ----
        bot = tk.Frame(root, bg=BG, padx=18, pady=10)
        bot.pack(fill="x")
        self.copy_btn = self._btn(bot, "\U0001F4CB  Kopiuj", self.copy, ACCENT_BG, BORDER, fg=TEXT)
        self.copy_btn.config(state="disabled")
        self.copy_btn.pack(side="left")
        self.folder_btn = self._btn(bot, "\U0001F4C1  Otworz folder", self.open_folder, ACCENT_BG, BORDER, fg=TEXT)
        self.folder_btn.config(state="disabled")
        self.folder_btn.pack(side="left", padx=8)
        vinfo = ("Raport tez w Obsidian: " + os.path.basename(self.vault)) if self.vault else "Pliki .txt/.srt/.md powstaja obok nagrania."
        tk.Label(bot, text=vinfo, fg=MUTED, bg=BG, font=("Segoe UI", 8)).pack(side="right")

        if not (os.path.exists(CLI) and os.path.exists(MODEL)):
            messagebox.showerror("Brak plikow",
                                 "Nie znaleziono silnika Whisper lub modelu.\n\n" + WDIR)

    # ---------- styl / obrazy ----------
    def _setup_style(self):
        st = ttk.Style()
        try:
            st.theme_use("clam")
        except Exception:
            pass
        st.configure("Klaster.Horizontal.TProgressbar", troughcolor=CREAM,
                     background=PRIMARY, borderwidth=0)
        st.configure("TNotebook", background=BG, borderwidth=0)
        st.configure("TNotebook.Tab", background=CREAM, foreground=MUTED,
                     padding=(10, 6), font=("Segoe UI", 10))
        st.map("TNotebook.Tab", background=[("selected", BG)],
               foreground=[("selected", TEXT)])
        st.configure("TCombobox", fieldbackground=BG, background=CREAM)

    def _img(self, name):
        path = os.path.join(ASSETS, name)
        if not os.path.exists(path):
            return None
        try:
            img = tk.PhotoImage(file=path)
            self._imgs[name] = img  # trzymaj referencje
            return img
        except Exception:
            return None

    def _btn(self, parent, text, cmd, bg, abg, fg="white", small=False):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg,
                         activebackground=abg, activeforeground=fg, relief="flat",
                         font=("Segoe UI", 10 if small else 11, "bold"),
                         padx=12 if small else 15, pady=5 if small else 8,
                         cursor="hand2", borderwidth=0)

    def _scrolled(self, parent):
        fr = tk.Frame(parent, bg=BG)
        t = tk.Text(fr, wrap="word", font=("Segoe UI", 12), bd=0, padx=12, pady=10,
                    bg=BG, fg=TEXT, insertbackground=TEXT, selectbackground="#F2D9CC")
        t.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(fr, command=t.yview)
        sb.pack(side="right", fill="y")
        t.config(yscrollcommand=sb.set)
        return fr, t

    # ---------- wybor pliku / DnD ----------
    def pick(self):
        if self.busy or self.recording:
            return
        f = filedialog.askopenfilename(
            title="Wybierz plik audio lub wideo",
            filetypes=[("Audio / Wideo",
                        "*.mp3 *.wav *.m4a *.mp4 *.mkv *.flac *.ogg *.opus *.wma *.aac *.mov *.avi *.webm"),
                       ("Wszystkie pliki", "*.*")])
        if f:
            self.start(f)

    def on_drop(self, event):
        if self.busy or self.recording:
            return
        raw = event.data.strip()
        raw = raw[1:].split("}")[0] if raw.startswith("{") else raw.split(" ")[0]
        if os.path.exists(raw):
            self.start(raw)
        else:
            messagebox.showwarning("Plik", "Nie udalo sie odczytac sciezki pliku.")

    # ---------- nagrywanie ----------
    def toggle_record(self):
        if self.busy:
            return
        self.stop_record() if self.recording else self.start_record()

    def _cb(self, indata, frames, t, status):
        self.frames.append(bytes(indata))

    def start_record(self):
        self.frames = []
        try:
            self.stream = sd.RawInputStream(samplerate=16000, channels=1, dtype="int16", callback=self._cb)
            self.stream.start()
        except Exception as exc:
            messagebox.showerror("Mikrofon", "Nie udalo sie uruchomic mikrofonu:\n\n" + str(exc)
                                 + "\n\nSprawdz: Ustawienia > Prywatnosc > Mikrofon.")
            return
        self.recording = True
        self.rec_start = time.time()
        self.rec_btn.config(text="⏹  Zatrzymaj i przepisz", bg=REC, activebackground="#B91C1C")
        self.pick_btn.config(state="disabled")
        self.drop.config(text="\U0001F534  Trwa nagrywanie…")
        self._tick()

    def _tick(self):
        if self.recording:
            s = int(time.time() - self.rec_start)
            self.status.config(text="\U0001F534 Nagrywam…  %02d:%02d   — kliknij „Zatrzymaj i przepisz”." % (s // 60, s % 60))
            self.root.after(400, self._tick)

    def stop_record(self):
        self.recording = False
        try:
            self.stream.stop(); self.stream.close()
        except Exception:
            pass
        self.rec_btn.config(text="\U0001F3A4  Nagraj glos", bg=DARK, activebackground=DARK_DK)
        data = b"".join(self.frames)
        if len(data) < 16000 * 2:
            self.status.config(text="Nagranie za krotkie - sprobuj ponownie.")
            self.pick_btn.config(state="normal")
            return
        os.makedirs(RECDIR, exist_ok=True)
        path = os.path.join(RECDIR, time.strftime("nagranie_%Y%m%d_%H%M%S.wav"))
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(16000); wf.writeframes(data)
        self.start(path)

    # ---------- transkrypcja ----------
    def start(self, path):
        self.busy = True
        self.txt_path = None
        self.transcript = ""
        self._lock(True)
        self.text.delete("1.0", "end")
        self.report.delete("1.0", "end")
        self.nb.select(0)
        self.drop.config(text="⏳  Przepisuje…  to moze chwile potrwac")
        self.status.config(text="Transkrypcja: " + os.path.basename(path) + "  …")
        self.pb.start(12)
        threading.Thread(target=self.work, args=(path, LANGS[self.lang.get()]), daemon=True).start()

    def work(self, path, lang):
        base = os.path.splitext(path)[0]
        try:
            subprocess.run([CLI, "-m", MODEL, "-l", lang, "-t", "16", "-otxt", "-osrt", "-of", base, "-f", path],
                           capture_output=True, text=True, encoding="utf-8", errors="replace",
                           creationflags=CREATE_NO_WINDOW)
            txt = base + ".txt"
            content = ""
            if os.path.exists(txt):
                with open(txt, "r", encoding="utf-8") as fh:
                    content = fh.read().strip()
            self.root.after(0, self.done, content, txt)
        except Exception as exc:
            self.root.after(0, self.fail, str(exc))

    def done(self, content, txt):
        self.pb.stop()
        self.busy = False
        self._lock(False)
        self.drop.config(text=(DROP_HINT if DND else PICK_HINT))
        if not content:
            self.status.config(text="⚠  Zakonczono, ale nie wykryto mowy w pliku.")
            return
        self.transcript = content
        self.txt_path = txt
        self.text.insert("1.0", content)
        self.copy_btn.config(state="normal")
        self.folder_btn.config(state="normal")
        self.report_btn.config(state="normal")
        self.status.config(text="✅  Transkrypcja gotowa: " + os.path.basename(txt))
        if self.auto_report.get():
            self.run_report()

    def fail(self, err):
        self.pb.stop(); self.busy = False; self._lock(False)
        self.drop.config(text=(DROP_HINT if DND else PICK_HINT))
        self.status.config(text="❌  Blad: " + err)
        messagebox.showerror("Blad", err)

    # ---------- raport (Qwen) ----------
    def run_report(self):
        if self.busy or not self.transcript:
            return
        self.busy = True
        self._lock(True)
        self.report.delete("1.0", "end")
        self.nb.select(1)
        self.pb.start(12)
        self.status.config(text="\U0001F9E0  Analizuje rozmowe modelem Qwen…  (~20-40 s)")
        threading.Thread(target=self.report_work, args=(self.transcript, self.txt_path), daemon=True).start()

    def report_work(self, transcript, txt_path):
        try:
            models = lm_models()
            if models is None and os.path.exists(LMS_EXE):
                try:
                    subprocess.run([LMS_EXE, "server", "start"], creationflags=CREATE_NO_WINDOW,
                                   timeout=30, capture_output=True)
                    time.sleep(2)
                    models = lm_models()
                except Exception:
                    pass
            if models is None:
                self.root.after(0, self.report_fail, "Serwer LM Studio nie odpowiada. Uruchom aplikacje LM Studio.")
                return
            model = lm_pick_model(models)
            if not model:
                self.root.after(0, self.report_fail, "Nie znaleziono modelu Qwen w LM Studio.")
                return
            report = lm_chat(model, SYS_PROMPT, REPORT_PROMPT + transcript)
            paths = self.save_report(report, txt_path)
            self.root.after(0, self.report_done, report, paths)
        except Exception as exc:
            self.root.after(0, self.report_fail, str(exc))

    def save_report(self, report, txt_path):
        stamp = time.strftime("%Y-%m-%d %H:%M")
        if txt_path:
            name = os.path.splitext(os.path.basename(txt_path))[0]
            folder = os.path.dirname(txt_path)
        else:
            name = time.strftime("rozmowa_%Y%m%d_%H%M%S")
            folder = RECDIR
            os.makedirs(folder, exist_ok=True)
        body = "# Raport z rozmowy — %s\n_%s · Asystent Spotkan Klastra_\n\n%s\n" % (name, stamp, report)
        saved = []
        md = os.path.join(folder, name + " - raport.md")
        with open(md, "w", encoding="utf-8") as f:
            f.write(body)
        saved.append(md)
        if self.vault:
            try:
                vdir = os.path.join(self.vault, "Transkrypcje")
                os.makedirs(vdir, exist_ok=True)
                vmd = os.path.join(vdir, name + " - raport.md")
                with open(vmd, "w", encoding="utf-8") as f:
                    f.write(body)
                saved.append(vmd)
            except Exception:
                pass
        return saved

    def report_done(self, report, paths):
        self.pb.stop(); self.busy = False; self._lock(False)
        self.report.insert("1.0", report)
        self.copy_btn.config(state="normal")
        self.folder_btn.config(state="normal")
        extra = "  +  Obsidian" if (self.vault and len(paths) > 1) else ""
        self.status.config(text="✅  Raport gotowy. Zapisano: " + os.path.basename(paths[0]) + extra)

    def report_fail(self, err):
        self.pb.stop(); self.busy = False; self._lock(False)
        self.status.config(text="❌  Raport: " + err)
        messagebox.showwarning("Raport (Qwen)", err)

    # ---------- pomocnicze ----------
    def _lock(self, busy):
        st = "disabled" if busy else "normal"
        self.pick_btn.config(state=st)
        if MIC:
            self.rec_btn.config(state=st)
        self.report_btn.config(state=("disabled" if (busy or not self.transcript) else "normal"))

    def copy(self):
        w = self.report if self.nb.index(self.nb.select()) == 1 else self.text
        self.root.clipboard_clear()
        self.root.clipboard_append(w.get("1.0", "end").strip())
        self.status.config(text="\U0001F4CB  Skopiowano do schowka.")

    def open_folder(self):
        target = self.txt_path
        if target and os.path.exists(target):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(target)])


def main():
    root = TkinterDnD.Tk() if DND else tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
