<#
Dev helper (Windows / PowerShell).

Usage:  .\scripts\dev.ps1 <command>
Commands:
  setup   create .venv, install deps, seed the DB
  seed    (re)create + seed the SQLite catalog
  test    run the test suite
  eval    run the evaluation harness
  check   test + eval (release gate)
  demo    run the console demo
  run     start the API with reload (http://localhost:8000)
#>
param([Parameter(Position = 0)][string]$Command = "help")

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Py = Join-Path $Root ".venv\Scripts\python.exe"

function Need-Venv {
    if (-not (Test-Path $Py)) { throw "No venv found. Run: .\scripts\dev.ps1 setup" }
}

switch ($Command) {
    "setup" {
        python -m venv .venv
        & $Py -m pip install --upgrade pip
        & $Py -m pip install -r requirements.txt
        & $Py -m app.db.seed
    }
    "seed"  { Need-Venv; & $Py -m app.db.seed }
    "test"  { Need-Venv; & $Py -m pytest -q }
    "eval"  { Need-Venv; & $Py -m app.eval.run }
    "llm-check" { Need-Venv; & $Py -m app.eval.llm_check }
    "check" { Need-Venv; & $Py -m pytest -q; & $Py -m app.eval.run }
    "demo"  { Need-Venv; & $Py demo.py }
    "run"   { Need-Venv; & $Py -m uvicorn app.main:app --reload }
    default { Get-Content $PSCommandPath -TotalCount 15 | Select-Object -Skip 1 }
}
