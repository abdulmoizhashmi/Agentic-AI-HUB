$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$frontend = Join-Path $root "frontend"
$dist = Join-Path $frontend "dist"
$publishedAssets = Join-Path $root "agentic-ai-hub-assets"
$previousGitHubActions = $env:GITHUB_ACTIONS

try {
    $env:GITHUB_ACTIONS = "true"
    Push-Location $frontend
    try {
        npm run build
        if ($LASTEXITCODE -ne 0) {
            throw "Frontend build failed."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($null -eq $previousGitHubActions) {
        Remove-Item Env:GITHUB_ACTIONS -ErrorAction SilentlyContinue
    }
    else {
        $env:GITHUB_ACTIONS = $previousGitHubActions
    }
}

$builtAssets = Join-Path $dist "agentic-ai-hub-assets"
if (-not (Test-Path (Join-Path $dist "index.html")) -or -not (Test-Path $builtAssets)) {
    throw "The frontend build did not produce the expected Pages files."
}

if (Test-Path $publishedAssets) {
    Remove-Item $publishedAssets -Recurse -Force
}
Copy-Item $builtAssets $publishedAssets -Recurse
Copy-Item (Join-Path $dist "index.html") (Join-Path $root "index.html") -Force

Write-Host "GitHub Pages files are ready in the repository root."
Write-Host "Commit index.html and agentic-ai-hub-assets/, then push to main."
