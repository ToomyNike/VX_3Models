$ErrorActionPreference = "Stop"

$condaHook = "D:\AAACODE\PYTHON\anaconda\shell\condabin\conda-hook.ps1"
$condaExe = "D:\AAACODE\PYTHON\anaconda\Scripts\conda.exe"

if (Test-Path $condaHook) {
    . $condaHook
    conda activate pyweb
    python --version
    python -m pip show Flask Flask-Cors Werkzeug
} elseif (Test-Path $condaExe) {
    & $condaExe run -n pyweb python --version
    & $condaExe run -n pyweb python -m pip show Flask Flask-Cors Werkzeug
} else {
    throw "Conda was not found at D:\AAACODE\PYTHON\anaconda"
}

$apsimExe = Join-Path $PSScriptRoot "apsim_engine\Models.exe"
$hydrusExe = Join-Path $PSScriptRoot "hydrus_engine\H1D_CALC.EXE"

if (Test-Path $apsimExe) {
    Write-Host "APSIM Models.exe found"
} else {
    Write-Host "APSIM Models.exe not found; MVP adapter fallback will be used"
}

if (Test-Path $hydrusExe) {
    Write-Host "HYDRUS H1D_CALC.EXE found"
} else {
    Write-Host "HYDRUS executable not found; MVP adapter fallback will be used"
}
