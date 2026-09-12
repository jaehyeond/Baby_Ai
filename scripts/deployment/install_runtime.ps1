param(
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$Uv = 'uv',
    [string]$RuntimeDirectory = (Join-Path $PSScriptRoot '../../.runtime')
)
$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$runtimeRoot = [IO.Path]::GetFullPath($RuntimeDirectory)
if ([IO.Path]::GetPathRoot($runtimeRoot) -eq 'C:\') { throw 'Choose E: or another data drive for runtime/cache files.' }
New-Item -ItemType Directory -Force $runtimeRoot | Out-Null
$env:UV_CACHE_DIR = Join-Path $runtimeRoot 'uv-cache'
$env:UV_PYTHON_DOWNLOADS = 'never'
$env:UV_LINK_MODE = 'copy'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:TEMP = Join-Path $runtimeRoot 'tmp'
$env:TMP = $env:TEMP
New-Item -ItemType Directory -Force $env:TEMP | Out-Null
$runtimePython = Join-Path $runtimeRoot 'venv/Scripts/python.exe'
& $Python -c 'import sys; assert sys.version_info[:2] == (3,12), "Python 3.12 required by lock"'
if ($LASTEXITCODE -ne 0) { throw 'Python version check failed' }
if (!(Test-Path -LiteralPath $runtimePython)) {
    & $Uv venv (Join-Path $runtimeRoot 'venv') --python $Python
    if ($LASTEXITCODE -ne 0) { throw 'venv creation failed' }
}
& $Uv pip sync --python $runtimePython --require-hashes (Join-Path $PSScriptRoot 'requirements-win-py312.lock')
if ($LASTEXITCODE -ne 0) { throw 'Locked installation failed' }
Push-Location $projectRoot
try {
    & $Uv build --wheel --out-dir (Join-Path $runtimeRoot 'dist') --python $runtimePython
    if ($LASTEXITCODE -ne 0) { throw 'Wheel build failed' }
    $wheelPath = Join-Path $runtimeRoot 'dist/our_a2a_project-0.1.0-py3-none-any.whl'
    & $Uv pip install --python $runtimePython --no-deps $wheelPath
    if ($LASTEXITCODE -ne 0) { throw 'Wheel installation failed' }
    & $Uv pip check --python $runtimePython
    if ($LASTEXITCODE -ne 0) { throw 'Dependency check failed' }
} finally { Pop-Location }
Write-Output "BIBI_RUNTIME_INSTALLED $runtimePython"
