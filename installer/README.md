# Instalator Windows

Ten folder buduje **jeden plik `Setup.exe`** dla Windows. Użytkownik końcowy
nie potrzebuje Pythona ani PowerShella - klika dwukrotnie i instaluje.

Instalator jest *offline*: zawiera spakowaną aplikację, silnik whisper.cpp oraz
model Whisper (large-v3-turbo). Jedyny element pobierany w razie potrzeby to
Microsoft Edge WebView2 Runtime (w Windows 11 jest już wbudowany).

## Z czego się składa

| Plik | Rola |
|---|---|
| `AsystentSpotkan.spec` | PyInstaller - pakuje `AsystentSpotkan.pyw` w samodzielny `.exe` (bez Pythona). |
| `installer.iss` | Inno Setup - tworzy `Setup.exe` (skróty, dezinstalator, WebView2, kreator po polsku). |

Gotowy plik trafia do `installer/Output/AsystentSpotkanKlastra-Setup.exe` (~510 MB).

## Budowanie (Windows)

Wymagane: Python 3.10-3.13 oraz [Inno Setup 6](https://jrsoftware.org/isdl.php)
(np. `winget install JRSoftware.InnoSetup`).

```powershell
# 1. Zależności
python -m pip install pyinstaller pywebview pythonnet sounddevice

# 2. Spakuj aplikację (-> dist\AsystentSpotkan\)
pyinstaller installer/AsystentSpotkan.spec --noconfirm

# 3. Przygotuj folder build\ (aplikacja + silnik + model + WebView2)
mkdir build\app, build\bin, build\models, build\webview2
Copy-Item dist\AsystentSpotkan\* build\app\ -Recurse -Force
curl.exe -fL -o whisper.zip "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-blas-bin-x64.zip"
Expand-Archive whisper.zip -DestinationPath build\bin -Force
curl.exe -fL -o "build\models\ggml-large-v3-turbo-q5_0.bin" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
curl.exe -fL -o "build\webview2\MicrosoftEdgeWebview2Setup.exe" "https://go.microsoft.com/fwlink/p/?LinkId=2124703"

# (opcjonalnie) zostaw w build\bin\Release tylko whisper-cli.exe + pliki *.dll,
# resztę exe można usunąć - aplikacja używa wyłącznie whisper-cli.exe.

# 4. Zbuduj Setup.exe (-> installer\Output\)
& "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe" installer/installer.iss "/DStage=$($PWD)\build" /DAppVersion=1.0.0
```

## Publikacja

Wgraj gotowy plik na stronę [Releases](https://github.com/Klaster1234/asystent-spotkan-klastra/releases):

```powershell
gh release upload v1.0 installer/Output/AsystentSpotkanKlastra-Setup.exe --clobber
```

Strona projektu i README kierują użytkowników właśnie tam.
