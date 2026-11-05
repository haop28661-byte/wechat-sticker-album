param(
    [ValidateSet("Project", "Global")]
    [string]$Scope = "Project",
    [string]$ProjectRoot = (Get-Location).Path,
    [switch]$Force,
    [switch]$Link
)

$ErrorActionPreference = "Stop"
$PythonExe = $null
$PythonPrefix = @()
$Python = Get-Command python -ErrorAction SilentlyContinue
if ($Python) {
    $PythonExe = $Python.Source
} else {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        $PythonExe = $PyLauncher.Source
        $PythonPrefix = @("-3")
    }
}
if (-not $PythonExe) {
    throw "Python 3.10 or newer is required."
}
& $PythonExe @PythonPrefix -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)"
if ($LASTEXITCODE -ne 0) {
    throw "Python 3.10 or newer is required."
}

$ArgsList = @(
    "$PSScriptRoot\scripts\install_skill.py",
    "--scope", $Scope.ToLowerInvariant(),
    "--project-root", $ProjectRoot
)
if ($Force) { $ArgsList += "--force" }
if ($Link) { $ArgsList += "--link" }

& $PythonExe @PythonPrefix @ArgsList
exit $LASTEXITCODE
