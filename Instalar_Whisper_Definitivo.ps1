param(
    [switch]$SkipBuildTools
)

$ErrorActionPreference = "Stop"

function Info($m) { Write-Host "[MILK] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }
function Warn($m) { Write-Host "[AVISO] $m" -ForegroundColor Yellow }

$Jarvis = "C:\JARVIS"
$Third  = Join-Path $Jarvis "third_party\whisper.cpp"
$ModelDir = Join-Path $Jarvis "models"
$Model = Join-Path $ModelDir "ggml-base.bin"

New-Item -ItemType Directory -Force -Path $Jarvis,$ModelDir,(Join-Path $Jarvis "third_party") | Out-Null

Info "Instalação definitiva do reconhecimento local Whisper.cpp"
Info "Fonte oficial: https://github.com/ggml-org/whisper.cpp"

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Info "Instalando Git oficial..."
    winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
}
Ok "Git disponível."

# CMake
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    Info "Instalando CMake..."
    winget install --id Kitware.CMake -e --accept-package-agreements --accept-source-agreements
    $env:Path += ";C:\Program Files\CMake\bin"
}
Ok "CMake disponível."

# Visual Studio Build Tools with ARM64 C++ workload
$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
$vsOk = $false
if (Test-Path $vswhere) {
    $found = & $vswhere -latest -products * -requires Microsoft.VisualStudio.Component.VC.Tools.ARM64 -property installationPath
    if ($found) { $vsOk = $true }
}

if (-not $vsOk -and -not $SkipBuildTools) {
    Info "Instalando Microsoft Visual Studio 2022 Build Tools com compilador C++ ARM64..."
    winget install --id Microsoft.VisualStudio.2022.BuildTools -e `
      --accept-package-agreements --accept-source-agreements `
      --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.VC.Tools.ARM64"

    Warn "Os Build Tools podem terminar de registrar componentes em alguns minutos."
}

# Clone/update source
if (Test-Path $Third) {
    Info "Atualizando whisper.cpp..."
    Push-Location $Third
    git fetch --all --tags
    git reset --hard origin/master
    Pop-Location
} else {
    Info "Baixando código-fonte oficial whisper.cpp..."
    git clone https://github.com/ggml-org/whisper.cpp.git $Third
}
Ok "Código-fonte oficial pronto."

# Configure ARM64 build
Push-Location $Third
if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

Info "Compilando whisper.cpp para Windows ARM64..."
cmake -B build -G "Visual Studio 17 2022" -A ARM64 `
  -DWHISPER_BUILD_TESTS=OFF `
  -DWHISPER_BUILD_EXAMPLES=ON

cmake --build build --config Release --target whisper-cli
Pop-Location

$ExeCandidates = @(
    (Join-Path $Third "build\bin\Release\whisper-cli.exe"),
    (Join-Path $Third "build\bin\whisper-cli.exe")
)
$Exe = $ExeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Exe) {
    throw "A compilação terminou, mas whisper-cli.exe não foi encontrado."
}
Ok "whisper-cli ARM64 compilado: $Exe"

# Model official hosting referenced by whisper.cpp
if (-not (Test-Path $Model)) {
    Info "Baixando modelo multilíngue BASE oficial..."
    $uri = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin"
    Start-BitsTransfer -Source $uri -Destination $Model
}
Ok "Modelo pronto: $Model"

# Write config
$config = @{
    whisper_exe = $Exe
    model = $Model
    language = "pt"
    seconds = 6
}
$config | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Jarvis "config\whisper_local.json")

Info "Validando executável..."
& $Exe -h | Out-Null

Ok "INSTALAÇÃO CONCLUÍDA."
Write-Host ""
Write-Host "Agora execute apenas:" -ForegroundColor White
Write-Host "  cd C:\JARVIS" -ForegroundColor Green
Write-Host "  python .\Conversar_Com_MILK.py" -ForegroundColor Green
