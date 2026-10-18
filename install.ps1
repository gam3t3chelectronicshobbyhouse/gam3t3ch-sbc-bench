param(
    [string]$Prefix = '',
    [switch]$NoLaunch,
    [switch]$SkipGodot
)
$ErrorActionPreference = 'Stop'

function Find-BenchPython {
    foreach ($candidate in @('python', 'python3', "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe")) {
        $resolved = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($resolved) {
            try {
                $version = & $resolved.Source -c 'import sys; print(sys.executable if sys.version_info >= (3,9) else "")' 2>$null
                if ($LASTEXITCODE -eq 0 -and $version -and (Test-Path -LiteralPath $version)) { return $version.Trim() }
            } catch { }
        }
    }
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        $version = & $pyLauncher.Source -3 -c 'import sys; print(sys.executable if sys.version_info >= (3,9) else "")'
        if ($LASTEXITCODE -eq 0 -and $version -and (Test-Path -LiteralPath $version)) { return $version.Trim() }
    }
    return $null
}

$pythonCommand = Find-BenchPython
if (-not $pythonCommand) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw 'Python 3.9+ is required. Install Python from python.org, then rerun this command.'
    }
    Write-Host 'Installing Python for your user with Windows Package Manager...'
    & winget install --exact --id Python.Python.3.13 --source winget --scope user
    if ($LASTEXITCODE -ne 0) { throw 'Python installation did not complete.' }
    $pythonCommand = Find-BenchPython
    if (-not $pythonCommand) { throw 'Python is installed but unavailable in this session. Reopen PowerShell and rerun.' }
}

$scratch = Join-Path ([IO.Path]::GetTempPath()) ('gam3t3ch-' + [guid]::NewGuid().ToString('N'))
$null = New-Item -ItemType Directory -Path $scratch
$installerFile = Join-Path $scratch 'installer.py'
try {
    Invoke-WebRequest -UseBasicParsing -Uri 'https://raw.githubusercontent.com/gam3t3chelectronicshobbyhouse/gam3t3ch-sbc-bench/main/installer.py' -OutFile $installerFile
    $installerOptions = @()
    if ($Prefix) { $installerOptions += @('--prefix', $Prefix) }
    elseif ($env:G3BENCH_PREFIX) { $installerOptions += @('--prefix', $env:G3BENCH_PREFIX) }
    if ($NoLaunch) { $installerOptions += '--no-launch' }
    if ($SkipGodot) { $installerOptions += '--skip-godot' }
    & $pythonCommand $installerFile @installerOptions
    if ($LASTEXITCODE -ne 0) { throw 'GAM3T3CH installation did not complete; see the error above.' }
} finally {
    # Remove only the explicitly-created helper file and empty directory.
    if (Test-Path -LiteralPath $installerFile) { Remove-Item -LiteralPath $installerFile }
    if (Test-Path -LiteralPath $scratch) { Remove-Item -LiteralPath $scratch }
}
