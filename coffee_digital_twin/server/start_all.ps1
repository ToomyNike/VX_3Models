$ErrorActionPreference = "Stop"

$backendDir = Resolve-Path (Join-Path $PSScriptRoot "..\backend")
Set-Location $backendDir

$condaHook = "D:\AAACODE\PYTHON\anaconda\shell\condabin\conda-hook.ps1"
$condaExe = "D:\AAACODE\PYTHON\anaconda\Scripts\conda.exe"

Write-Host "Starting backend at http://0.0.0.0:5000 with conda env: pyweb"

if (Test-Path $condaHook) {
    . $condaHook
    conda activate pyweb
    python app.py
} elseif (Test-Path $condaExe) {
    & $condaExe run -n pyweb python app.py
} else {
    throw "Conda was not found at D:\AAACODE\PYTHON\anaconda"
}
