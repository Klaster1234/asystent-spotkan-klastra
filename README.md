<div align="center">

<img src="assets/logo.png" width="92" alt="Klaster Innowacji Społecznych" />

# Asystent Spotkań Klastra

Nagranie → transkrypcja → gotowy raport z rozmowy. W 100% lokalnie, bez internetu.

![Licencja: MIT](https://img.shields.io/badge/Licencja-MIT-E07B54)
![Python](https://img.shields.io/badge/Python-3.10%2B-37352F)
![Prywatność](https://img.shields.io/badge/Prywatno%C5%9B%C4%87-100%25%20lokalnie-16a34a)
![System](https://img.shields.io/badge/System-Windows-2563eb)

<img src="docs/screenshot.png" width="760" alt="Asystent Spotkań Klastra" />

</div>

---

## Po polsku

Asystent Spotkań Klastra to lekka aplikacja dla Windows, która zamienia nagranie rozmowy w tekst (transkrypcja) i automatycznie tworzy z niego zwięzły raport: podsumowanie, decyzje oraz zadania z osobami i terminami. Wszystko dzieje się na Twoim komputerze - żadne dane nie wychodzą do chmury.

Interfejs jest renderowany przez WebView2 (silnik Edge), więc jest nowoczesny i szybki, a raport pojawia się na żywo, słowo po słowie.

### Funkcje

- Nagrywanie z mikrofonu jednym przyciskiem albo wczytanie pliku audio/wideo.
- Transkrypcja po polsku silnikiem whisper.cpp (model large-v3-turbo).
- Automatyczny raport z rozmowy lokalnym modelem Qwen3 przez LM Studio, strumieniowany na żywo.
- Zapis wyników do plików .txt (tekst), .srt (napisy) i .txt (raport) obok nagrania.
- Pełna prywatność - działa offline.

### Jak to działa

```
nagranie / plik  ->  Whisper (transkrypcja)  ->  Qwen (raport)  ->  pliki .txt / .srt
```

## Wymagania sprzętowe

Aplikacja ma dwa tryby o różnych wymaganiach.

Transkrypcja (Whisper, na procesorze):

- Windows 10/11 64-bit
- Microsoft Edge WebView2 Runtime (zwykle już jest w Windows 11; instalator dograje go w razie potrzeby)
- Procesor 4-rdzeniowy lub lepszy
- 8 GB RAM
- Około 2 GB miejsca na dysku (silnik + model Whisper)
- Mikrofon - jeśli chcesz nagrywać (przy wczytywaniu plików niepotrzebny)

Raport AI (Qwen przez LM Studio) - dodatkowo:

- Zainstalowane LM Studio z modelem Qwen3
- Minimalnie: 16 GB RAM dla mniejszego modelu (Qwen3 4B lub 8B)
- Zalecane: 32 GB RAM lub dedykowane GPU dla modeli 14-32B
- Optymalnie: APU lub GPU z dużą pamięcią (32-128 GB) dla modeli 30B+ i najszybszych raportów

Sama transkrypcja działa bez LM Studio. Raport wymaga uruchomionego LM Studio z modelem.

## Instalacja (Windows)

1. Zainstaluj [Python 3.10+](https://www.python.org/downloads/) (zaznacz „Add to PATH").
2. Pobierz to repozytorium (Code → Download ZIP albo `git clone`).
3. W folderze projektu uruchom w PowerShell:
   ```powershell
   powershell -ExecutionPolicy Bypass -File install.ps1
   ```
   Instalator dograje WebView2 (jeśli trzeba), pobierze silnik i model Whisper oraz utworzy skrót na pulpicie.
4. Dla raportów: zainstaluj [LM Studio](https://lmstudio.ai), pobierz model Qwen3 i włącz lokalny serwer (port 1234).

Modele AI nie są dołączone do repozytorium (są duże i mają własne licencje) - pobiera je instalator.

## Użycie

Kliknij ikonę „Asystent Spotkań Klastra" na pulpicie, a potem:

- „Nagraj głos" → mów → „Zatrzymaj i przepisz", albo
- „Wybierz plik…" i wskaż nagranie.

Tekst i raport pojawią się w zakładkach; raport zapisuje się automatycznie obok nagrania.

## Wykorzystane modele i licencje

| Komponent | Licencja | Źródło |
|---|---|---|
| whisper.cpp | MIT | https://github.com/ggml-org/whisper.cpp |
| Whisper large-v3-turbo (GGML) | MIT | https://huggingface.co/ggerganov/whisper.cpp |
| Qwen3 (np. Qwen3-30B-A3B-Instruct) | Apache-2.0 | https://huggingface.co/Qwen |
| LM Studio (środowisko uruchomieniowe) | proprietary (darmowe) | https://lmstudio.ai |

## Licencja

Kod: MIT (zobacz [LICENSE](LICENSE)). Logo Klastra i maskotka Klastus to znaki towarowe i nie są objęte licencją MIT - zobacz [NOTICE.md](NOTICE.md).

<div align="center">
<sub>Zbudowane dla Klaster Innowacji Społecznych · „Inicjatywy społeczne dla wszystkich"</sub>
</div>
