param(
    [switch]$WithAsr,
    [string]$SkillDestination
)
$ErrorActionPreference = 'Stop'
$repoPath = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$venvPath = Join-Path $repoPath '.venv'
$pythonPath = Join-Path $venvPath 'Scripts/python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    & py -3.12 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 virtual environment creation failed.' }
}
& $pythonPath -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,12) else 1)'
if ($LASTEXITCODE -ne 0) { throw 'The existing virtual environment must use Python 3.12.' }
$packagePath = if ($WithAsr) { "${repoPath}[asr]" } else { $repoPath }
& $pythonPath -m pip install -e $packagePath
if ($LASTEXITCODE -ne 0) { throw 'Package installation failed.' }
if ($SkillDestination) {
    & $pythonPath -m codex_resolve skill-copy $SkillDestination
    if ($LASTEXITCODE -ne 0) { throw 'Skill copy failed. Existing Skills are not overwritten.' }
}
Write-Output "Installed local development package. CLI: $venvPath/Scripts/codex-resolve.exe"
Write-Output 'FFmpeg and Resolve Studio must be installed separately. No tests or Resolve operations were run.'
