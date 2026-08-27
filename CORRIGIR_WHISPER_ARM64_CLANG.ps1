$ErrorActionPreference = "Stop"

function Info($m) { Write-Host "[MILK] $m" -ForegroundColor Cyan }
function Ok($m)   { Write-Host "[OK]   $m" -ForegroundColor Green }

$Jarvis = "C:\JARVIS"
$Third  = Join-Path $Jarvis "third_party\whisper.cpp"
$ModelDir = Join-Path $Jarvis "models"
$Model = Join-Path $ModelDir "ggml-base.bin"

New-Item -ItemType Directory -Force -Path $ModelDir | Out-Null

Info "Corrigindo compilação ARM64: usando ClangCL, não MSVC."

# Garante VS Build Tools + Clang/LLVM
Info "Instalando/atualizando Visual Studio Build Tools com LLVM/Clang e ARM64..."
winget install --id Microsoft.VisualStudio.2022.BuildTools -e `
  --accept-package-agreements --accept-source-agreements `
  --override "--wait --passive --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended --add Microsoft.VisualStudio.Component.VC.Tools.ARM64 --add Microsoft.VisualStudio.Component.VC.Llvm.Clang"

# CMake
if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
    winget install --id Kitware.CMake -e --accept-package-agreements --accept-source-agreements
    $env:Path += ";C:\Program Files\CMake\bin"
}

# Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    winget install --id Git.Git -e --accept-package-agreements --accept-source-agreements
}

# Código oficial
if (Test-Path $Third) {
    Push-Location $Third
    git fetch --all --tags
    git reset --hard origin/master
    Pop-Location
} else {
    git clone https://github.com/ggml-org/whisper.cpp.git $Third
}

Push-Location $Third

if (Test-Path "build") {
    Remove-Item -Recurse -Force "build"
}

Info "Configurando CMake com ClangCL ARM64..."
cmake -S . -B build `
  -G "Visual Studio 17 2022" `
  -A ARM64 `
  -T ClangCL `
  -DGGML_NATIVE=OFF `
  -DGGML_OPENMP=OFF `
  -DWHISPER_BUILD_TESTS=OFF `
  -DWHISPER_BUILD_EXAMPLES=ON

if ($LASTEXITCODE -ne 0) {
    throw "Falha na configuração CMake com ClangCL."
}

Info "Compilando whisper-cli..."
cmake --build build --config Release --target whisper-cli

if ($LASTEXITCODE -ne 0) {
    throw "Falha na compilação do whisper-cli."
}

Pop-Location

$ExeCandidates = @(
    (Join-Path $Third "build\bin\Release\whisper-cli.exe"),
    (Join-Path $Third "build\bin\whisper-cli.exe")
)

$Exe = $ExeCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $Exe) {
    throw "whisper-cli.exe não encontrado após a compilação."
}

Ok "whisper-cli ARM64 compilado com ClangCL."

if (-not (Test-Path $Model)) {
    Info "Baixando modelo Whisper Base..."
    Start-BitsTransfer `
      -Source "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin" `
      -Destination $Model
}

$config = @{
    whisper_exe = $Exe
    model = $Model
    language = "pt"
    seconds = 6
}
$config | ConvertTo-Json | Set-Content -Encoding UTF8 (Join-Path $Jarvis "config\whisper_local.json")

Ok "Configuração salva."
Write-Host ""
Write-Host "AGORA RODE:" -ForegroundColor White
Write-Host "cd C:\JARVIS" -ForegroundColor Green
Write-Host "python .\Conversar_Com_MILK.py" -ForegroundColor Green
