<div align="center">

<img src="assets/logo.png" width="96" alt="Klaster Innowacji Społecznych" />

# Asystent Spotkań Klastra

**Nagranie → transkrypcja → gotowy raport z rozmowy. W 100% lokalnie, bez internetu.**

![License: MIT](https://img.shields.io/badge/Licencja-MIT-E07B54)
![Python](https://img.shields.io/badge/Python-3.10%2B-37352F)
![Offline](https://img.shields.io/badge/Prywatno%C5%9B%C4%87-100%25%20lokalnie-16a34a)
![Platform](https://img.shields.io/badge/System-Windows-2563eb)

<img src="docs/screenshot.png" width="720" alt="Asystent Spotkań Klastra — zrzut ekranu" />

</div>

---

## 🇵🇱 Po polsku

**Asystent Spotkań Klastra** to prosta aplikacja okienkowa dla Windows, która zamienia
nagranie rozmowy w **tekst** (transkrypcja) i automatycznie tworzy z niej **zwięzły raport**
(podsumowanie, decyzje, zadania z osobami i terminami). Wszystko dzieje się **na Twoim
komputerze** — żadne dane nie wychodzą do chmury.

### Funkcje
- 🎤 **Nagrywanie z mikrofonu** jednym przyciskiem (albo wczytanie pliku / przeciągnij-i-upuść)
- 📝 **Transkrypcja po polsku** silnikiem [whisper.cpp](https://github.com/ggml-org/whisper.cpp) (model `large-v3-turbo`)
- 🧠 **Automatyczny raport z rozmowy** lokalnym modelem **Qwen3** (przez [LM Studio](https://lmstudio.ai))
- 💾 Zapis do `.txt`, `.srt` (napisy) i `.md` (raport) — opcjonalnie prosto do **Obsidian**
- 🔒 **Pełna prywatność** — działa offline, idealne do danych wrażliwych

### Jak to działa
```
🎤 nagranie / 📂 plik  →  📝 Whisper (transkrypcja)  →  🧠 Qwen (raport)  →  💾 .txt / .srt / .md
```

### Instalacja (Windows)
1. Zainstaluj [Python 3.10+](https://www.python.org/downloads/) (zaznacz **„tcl/tk"** i **„Add to PATH"**).
2. Pobierz to repozytorium (zielony przycisk **Code → Download ZIP** lub `git clone`).
3. W folderze projektu uruchom w PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   Instalator pobierze silnik Whisper + model i utworzy skrót na pulpicie.
4. **Dla raportów (Qwen):** zainstaluj [LM Studio](https://lmstudio.ai), pobierz model
   **Qwen3** i włącz lokalny serwer (port `1234`).

> Modele AI nie są dołączone do repozytorium (są duże i mają własne licencje) — pobiera je instalator.

### Użycie
Kliknij ikonę **„Asystent Spotkań Klastra"** na pulpicie, a potem:
- **🎤 Nagraj głos** → mów → **Zatrzymaj** → tekst i raport pojawią się same, **albo**
- **📂 Wybierz plik** / przeciągnij nagranie na okno.

---

## 🇬🇧 In English

**Asystent Spotkań Klastra** ("Cluster Meeting Assistant") is a simple Windows desktop app
that turns a conversation recording into **text** and an automatic **meeting report**
(summary, decisions, action items with owners and deadlines) — **100% locally, offline**.

- 🎤 One-click mic recording (or file / drag-and-drop)
- 📝 Polish (and other languages) transcription via [whisper.cpp](https://github.com/ggml-org/whisper.cpp)
- 🧠 Automatic report via a local **Qwen3** model ([LM Studio](https://lmstudio.ai))
- 💾 Saves `.txt`, `.srt`, `.md` — optionally straight into **Obsidian**
- 🔒 Fully private, runs offline

See the Polish section above for installation (`install.ps1`). AI models are **not** bundled —
the installer downloads them.

---

## 🧩 Wykorzystane modele i licencje / Models & licenses
| Komponent | Licencja | Źródło |
|---|---|---|
| whisper.cpp | MIT | https://github.com/ggml-org/whisper.cpp |
| Whisper `large-v3-turbo` (GGML) | MIT | https://huggingface.co/ggerganov/whisper.cpp |
| Qwen3 (np. `Qwen3-30B-A3B-Instruct`) | Apache-2.0 | https://huggingface.co/Qwen |
| LM Studio (środowisko uruchomieniowe) | proprietary (darmowe) | https://lmstudio.ai |

## 📄 Licencja / License
Kod: **MIT** (zobacz [LICENSE](LICENSE)). Logo Klastra i maskotka Klastus to znaki
towarowe i **nie** są objęte licencją MIT — zobacz [NOTICE.md](NOTICE.md).

<div align="center">
<sub>Zbudowane dla <b>Klaster Innowacji Społecznych</b> · „Inicjatywy społeczne dla wszystkich"</sub>
</div>
