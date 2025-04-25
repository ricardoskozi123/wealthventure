# Simple PowerShell Script to Rename EeazyCRM to OMCRM
Write-Host "Starting renaming process..." -ForegroundColor Yellow

# 1. Rename the main package directory
if (Test-Path -Path ".\eeazycrm") {
    Write-Host "Renaming main package directory..." -ForegroundColor Cyan
    try {
        Rename-Item -Path ".\eeazycrm" -NewName "omcrm"
        Write-Host "Directory renamed successfully" -ForegroundColor Green
    } catch {
        Write-Host "Error renaming directory" -ForegroundColor Red
    }
} else {
    Write-Host "Main package directory 'eeazycrm' not found. Skipping directory rename." -ForegroundColor Yellow
}

# 2. Replace in Python files
Write-Host "Replacing in Python files..." -ForegroundColor Cyan
Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName
    $content = $content -replace 'eeazycrm', 'omcrm'
    $content = $content -replace 'EeazyCRM', 'OMCRM'
    Set-Content -Path $_.FullName -Value $content
}

# 3. Replace in HTML files
Write-Host "Replacing in HTML files..." -ForegroundColor Cyan
Get-ChildItem -Path . -Filter *.html -Recurse | ForEach-Object {
    $content = Get-Content $_.FullName
    $content = $content -replace 'eeazycrm', 'omcrm'
    $content = $content -replace 'EeazyCRM', 'OMCRM'
    Set-Content -Path $_.FullName -Value $content
}

# 4. Replace in configuration files
Write-Host "Replacing in configuration files..." -ForegroundColor Cyan
$configFiles = @(
    ".\deployment_config.py",
    ".\wsgi.py",
    ".\deployment_guide.md",
    ".\requirements.txt"
)

foreach ($file in $configFiles) {
    if (Test-Path -Path $file) {
        $content = Get-Content $file
        $content = $content -replace 'eeazycrm', 'omcrm'
        $content = $content -replace 'EeazyCRM', 'OMCRM'
        Set-Content -Path $file -Value $content
    }
}

Write-Host "Renaming process completed!" -ForegroundColor Green 