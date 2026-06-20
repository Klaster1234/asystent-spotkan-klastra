# Instalator: Asystent Spotkan Klastra (Whisper + Qwen)
# Uruchom w PowerShell:
#   powershell -ExecutionPolicy Bypass -File install.ps1
$ErrorActionPreference = "Stop"
$repo = $PSScriptRoot
$WDIR = Join-Path $env:USERPROFILE "whisper"
Write-Host "== Asystent Spotkan Klastra - instalacja ==" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  Write-Host "Brak Pythona. Zainstaluj z https://python.org (zaznacz Add to PATH)." -ForegroundColor Red
  exit 1
}

Write-Host "1/6 Instaluje biblioteki Python..."
python -m pip install -r (Join-Path $repo "requirements.txt")

Write-Host "2/6 Sprawdzam Microsoft Edge WebView2 Runtime..."
$wv = $false
$ids = @(
  "HKLM:\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
  "HKLM:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}",
  "HKCU:\SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
)
foreach ($k in $ids) { if (Test-Path $k) { $wv = $true } }
if (-not $wv) {
  Write-Host "    Pobieram i instaluje WebView2 Runtime..."
  $b = Join-Path $env:TEMP "MicrosoftEdgeWebview2Setup.exe"
  curl.exe -fsSL -o $b "https://go.microsoft.com/fwlink/p/?LinkId=2124703"
  Start-Process $b -ArgumentList "/silent","/install" -Wait
} else {
  Write-Host "    WebView2 Runtime juz jest."
}

Write-Host "3/6 Tworze foldery i kopiuje aplikacje..."
New-Item -ItemType Directory -Force -Path "$WDIR\bin", "$WDIR\models", "$WDIR\assets" | Out-Null
Copy-Item (Join-Path $repo "AsystentSpotkan.pyw") $WDIR -Force
Copy-Item (Join-Path $repo "assets\*") "$WDIR\assets\" -Force

Write-Host "4/6 Pobieram silnik whisper.cpp (CPU/BLAS)..."
$zip = Join-Path $WDIR "whisper-blas.zip"
curl.exe -fsSL -o $zip "https://github.com/ggml-org/whisper.cpp/releases/download/v1.9.1/whisper-blas-bin-x64.zip"
Expand-Archive -Path $zip -DestinationPath "$WDIR\bin" -Force
del $zip

Write-Host "5/6 Pobieram model Whisper large-v3-turbo (~550 MB)..."
$model = Join-Path $WDIR "models\ggml-large-v3-turbo-q5_0.bin"
if (-not (Test-Path $model)) {
  curl.exe -fL -C - -o $model "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo-q5_0.bin"
}

Write-Host "6/6 Tworze skrot na pulpicie..."
$pyw = (Get-Command pythonw).Source
$desktop = [Environment]::GetFolderPath("Desktop")
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut((Join-Path $desktop "Asystent Spotkan Klastra.lnk"))
$sc.TargetPath = $pyw
$sc.Arguments = '"' + (Join-Path $WDIR "AsystentSpotkan.pyw") + '"'
$sc.WorkingDirectory = $WDIR
$sc.IconLocation = "$WDIR\assets\klaster.ico"
$sc.Save()

Write-Host ""
Write-Host "GOTOWE. Ikona 'Asystent Spotkan Klastra' jest na pulpicie." -ForegroundColor Green
Write-Host "Aby dzialal RAPORT (Qwen): zainstaluj LM Studio (https://lmstudio.ai)," -ForegroundColor Yellow
Write-Host "pobierz model Qwen3 i wlacz lokalny serwer na porcie 1234." -ForegroundColor Yellow
