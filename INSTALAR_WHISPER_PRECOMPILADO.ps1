$ErrorActionPreference = "Stop"

function Info($m) { Write-Host "[MILK] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }

$Jarvis = "C:\JARVIS"
$BinDir = Join-Path $Jarvis "third_party\whisper-prebuilt"
$ModelDir = Join-Path $Jarvis "models"
$Model = Join-Path $ModelDir "ggml-base.bin"
$Zip = Join-Path $env:TEMP "whisper-bin-x64.zip"

New-Item -ItemType Directory -Force -Path $BinDir,$ModelDir,(Join-Path $Jarvis "config") | Out-Null

Info "Usando binário oficial pré-compilado x64 do whisper.cpp."
Info "No Windows 11 ARM64 ele roda pela emulação x64/Prism do próprio Windows."
Info "Não haverá compilação C++, MSVC ou Clang."

$WhisperUrl = "https://github.com/ggml-org/whisper.cpp/releases/latest/download/whisper-bin-x64.zip"

Info "Baixando whisper.cpp oficial..."
if (Test-Path $Zip) { Remove-Item -Force $Zip }

try {
    curl.exe -L --fail --retry 3 -o $Zip $WhisperUrl
} catch {
    Invoke-WebRequest -Uri $WhisperUrl -OutFile $Zip -UseBasicParsing
}

if (-not (Test-Path $Zip)) {
    throw "Download do whisper.cpp não foi concluído."
}

Info "Extraindo..."
if (Test-Path $BinDir) {
    Remove-Item -Recurse -Force $BinDir
}
New-Item -ItemType Directory -Force -Path $BinDir | Out-Null
Expand-Archive -Path $Zip -DestinationPath $BinDir -Force

$Exe = Get-ChildItem -Path $BinDir -Recurse -Filter "whisper-cli.exe" |
       Select-Object -First 1 -ExpandProperty FullName

if (-not $Exe) {
    throw "O pacote oficial foi baixado, mas whisper-cli.exe não foi encontrado."
}

Ok "whisper-cli encontrado: $Exe"

if (-not (Test-Path $Model)) {
    Info "Baixando modelo Whisper BASE multilíngue..."
    $ModelUrl = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
    try {
        curl.exe -L --fail --retry 3 -o $Model $ModelUrl
    } catch {
        Invoke-WebRequest -Uri $ModelUrl -OutFile $Model -UseBasicParsing
    }
}

if (-not (Test-Path $Model)) {
    throw "Modelo Whisper não foi baixado."
}

Ok "Modelo pronto."

$config = @{
    whisper_exe = $Exe
    model = $Model
    language = "pt"
    seconds = 6
}
$config | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Jarvis "config\whisper_local.json")

Info "Validando executável..."
& $Exe --version
if ($LASTEXITCODE -ne 0) {
    throw "O Windows não conseguiu executar o whisper-cli x64."
}

Ok "WHISPER INSTALADO E VALIDADO."
Write-Host ""
Write-Host "Agora rode:" -ForegroundColor White
Write-Host "cd C:\JARVIS" -ForegroundColor Green
Write-Host "python .\Conversar_Com_MILK.py" -ForegroundColor Green
