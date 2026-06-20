# Instalator: Asystent Spotkan Klastra (Whisper + Qwen)
# Uruchom w PowerShell:
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$WDIR = Join-Path $env:USERPROFILE "whisper"
Write-Host "== Asystent Spotkan Klastra - instalacja ==" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Brak Pythona. Zainstaluj z https://python.org (zaznacz tcl/tk + Add to PATH)." -ForegroundColor Red
  exit 1
}

Write-Host "1/5 Instaluje biblioteki Python..."
python -m pip install -r (Join-Path $repo "requirements.txt")

Write-Host "2/5 Tworze foldery i kopiuje aplikacje..."
New-Item -ItemType Directory -Force -Path "$WDIR\bin", "$WDIR\models", "$WDIR\assets" | Out-Null
Copy-Item (Join-Path $repo "TranskrypcjaApp.pyw") $WDIR -Force
Copy-Item (Join-Path $repo "assets\*") "$WDIR\assets\" -Force

Write-Host "3/5 Pobieram silnik whisper.cpp (CPU/BLAS)..."
$zip = Join-Path $WDIR "whisper-blas.zip"
curl.exe -fsSL -o $zip "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-blas-bin-x64.zip"
Expand-Archive -Path $zip -DestinationPath "$WDIR\bin" -Force
del $zip

Write-Host "4/5 Pobieram model Whisper large-v3-turbo (~550 MB)..."
$model = Join-Path $WDIR "models\ggml-large-v3-turbo-q5_0.bin"
if (-not (Test-Path $model)) {
  curl.exe -fL -C - -o $model "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
}

Write-Host "5/5 Tworze skrot na pulpicie..."
$pyw = (Get-Command pythonw).Source
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut((Join-Path $desktop "Asystent Spotkan Klastra.lnk"))
$sc.TargetPath = $pyw
$sc.Arguments = '"' + (Join-Path $WDIR "TranskrypcjaApp.pyw") + '"'
$sc.WorkingDirectory = $WDIR
$sc.IconLocation = "$WDIR\assets\klaster.ico"
$sc.Save()

Write-Host ""
Write-Host "GOTOWE! Ikona 'Asystent Spotkan Klastra' jest na pulpicie." -ForegroundColor Green
Write-Host "Aby dzialal RAPORT (Qwen): zainstaluj LM Studio (https://lmstudio.ai)," -ForegroundColor Yellow
Write-Host "pobierz model Qwen3 i wlacz lokalny serwer na porcie 1234." -ForegroundColor Yellow
