# Podpisywanie cyfrowe (Authenticode) - usuwa ostrzezenie SmartScreen.
#
# Uzycie:
#   # certyfikat z magazynu Windows (po odcisku palca):
#   .\sign.ps1 -Path ..\dist\AsystentSpotkan\AsystentSpotkan.exe -Thumbprint <ODCISK>
#   # albo certyfikat z pliku .pfx:
#   .\sign.ps1 -Path ..\installer\Output\AsystentSpotkanKlastra-Setup.exe -Pfx cert.pfx -Password ******
#
# Mozna tez ustawic zmienne srodowiskowe: SIGN_THUMBPRINT, SIGN_PFX, SIGN_PFX_PASSWORD.
# Gdy nie podano zadnego certyfikatu, krok jest POMIJANY (build nie przerywa sie).
param(
  [Parameter(Mandatory = $true)][string[]]$Path,
  [string]$Thumbprint = $env:SIGN_THUMBPRINT,
  [string]$Pfx = $env:SIGN_PFX,
  [string]$Password = $env:SIGN_PFX_PASSWORD,
  [string]$TimestampUrl = "http://timestamp.digicert.com"
)
$ErrorActionPreference = "Stop"

function Find-SignTool {
  $c = Get-Command signtool.exe -ErrorAction SilentlyContinue
  if ($c) { return $c.Source }
  $roots = @("${env:ProgramFiles(x86)}\Windows Kits\10\bin", "${env:ProgramFiles}\Windows Kits\10\bin")
  foreach ($r in $roots) {
    if (Test-Path $r) {
      $st = Get-ChildItem $r -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match '\\x64\\' } |
            Sort-Object FullName -Descending | Select-Object -First 1
      if ($st) { return $st.FullName }
    }
  }
  return $null
}

if (-not $Thumbprint -and -not $Pfx) {
  Write-Warning "Brak certyfikatu (ustaw -Thumbprint lub -Pfx). Pomijam podpisywanie - plik pozostaje niepodpisany."
  exit 0
}

$signtool = Find-SignTool
if (-not $signtool) {
  Write-Warning "Nie znaleziono signtool.exe. Zainstaluj Windows SDK (App Installer / Windows 10 SDK). Pomijam."
  exit 0
}

$common = @('sign', '/fd', 'SHA256', '/tr', $TimestampUrl, '/td', 'SHA256')
if ($Pfx) {
  $auth = @('/f', $Pfx)
  if ($Password) { $auth += @('/p', $Password) }
} else {
  $auth = @('/sha1', $Thumbprint)
}

foreach ($p in $Path) {
  if (-not (Test-Path $p)) { throw "Nie istnieje: $p" }
  & $signtool @common @auth $p
  if ($LASTEXITCODE -ne 0) { throw "signtool sign nie powiodlo sie dla: $p" }
  & $signtool verify /pa $p
  if ($LASTEXITCODE -ne 0) { throw "weryfikacja podpisu nie powiodla sie dla: $p" }
  Write-Host "Podpisano i zweryfikowano: $p" -ForegroundColor Green
}
