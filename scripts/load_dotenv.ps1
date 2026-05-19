# Load variables from project-root `.env` into the current PowerShell session.
param(
    [string]$EnvFile = (Join-Path (Split-Path $PSScriptRoot -Parent) ".env")
)

function Import-ProjectDotEnv {
    param([string]$Path)
    if (-not (Test-Path $Path)) {
        Write-Warning ".env not found at: $Path"
        Write-Warning "Copy .env.example to .env and add OPENAI_API_KEY / PYANNOTE_TOKEN."
        return $false
    }
    Get-Content $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $name = $line.Substring(0, $eq).Trim()
        $value = $line.Substring($eq + 1).Trim().Trim('"').Trim("'")
        if ($name) {
            Set-Item -Path "env:$name" -Value $value
        }
    }
    return $true
}

Import-ProjectDotEnv -Path $EnvFile | Out-Null
