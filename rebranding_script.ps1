# PowerShell Script to Rename EeazyCRM to OMCRM
# ================================================
# This script automates the renaming process from EeazyCRM to OMCRM
# Run this script from the root directory of your project
# Make sure to backup your project before running this script!

Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Automated Renaming Script: EeazyCRM to OMCRM" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""

# Confirm before proceeding
$confirm = Read-Host "This script will rename EeazyCRM to OMCRM throughout your project. Have you backed up your project? (y/n)"
if ($confirm -ne "y") {
    Write-Host "Operation cancelled. Please backup your project before proceeding." -ForegroundColor Red
    exit
}

Write-Host "Starting renaming process..." -ForegroundColor Yellow

# 1. Rename the main package directory
if (Test-Path -Path ".\eeazycrm") {
    Write-Host "Renaming main package directory..." -ForegroundColor Cyan
    try {
        Rename-Item -Path ".\eeazycrm" -NewName "omcrm" -ErrorAction Stop
        Write-Host "Directory renamed successfully" -ForegroundColor Green
    } catch {
        Write-Host "Error renaming directory: $($_.Exception.Message)" -ForegroundColor Red
    }
} else {
    Write-Host "Main package directory 'eeazycrm' not found. Skipping directory rename." -ForegroundColor Yellow
}

# 2. Find and replace in all Python files
Write-Host "Replacing 'eeazycrm' with 'omcrm' in Python files..." -ForegroundColor Cyan
try {
    Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object {
        Write-Host "Processing file: $($_.FullName)" -ForegroundColor Gray
        (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName
    }
    Write-Host "Python files updated successfully" -ForegroundColor Green
} catch {
    Write-Host "Error updating Python files: $($_.Exception.Message)" -ForegroundColor Red
}

# 3. Find and replace in all HTML files
Write-Host "Replacing 'eeazycrm' with 'omcrm' in HTML files..." -ForegroundColor Cyan
try {
    Get-ChildItem -Path . -Filter *.html -Recurse | ForEach-Object {
        Write-Host "Processing file: $($_.FullName)" -ForegroundColor Gray
        (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName
        (Get-Content $_.FullName) -replace 'EeazyCRM', 'OMCRM' | Set-Content $_.FullName
    }
    Write-Host "HTML files updated successfully" -ForegroundColor Green
} catch {
    Write-Host "Error updating HTML files: $($_.Exception.Message)" -ForegroundColor Red
}

# 4. Find and replace in all JavaScript files
Write-Host "Replacing 'eeazycrm' with 'omcrm' in JavaScript files..." -ForegroundColor Cyan
try {
    Get-ChildItem -Path . -Filter *.js -Recurse | ForEach-Object {
        Write-Host "Processing file: $($_.FullName)" -ForegroundColor Gray
        (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName
    }
    Write-Host "JavaScript files updated successfully" -ForegroundColor Green
} catch {
    Write-Host "Error updating JavaScript files: $($_.Exception.Message)" -ForegroundColor Red
}

# 5. Find and replace in all configuration files
Write-Host "Replacing 'eeazycrm' with 'omcrm' in configuration files..." -ForegroundColor Cyan
$configFiles = @(
    ".\deployment_config.py",
    ".\wsgi.py",
    ".\requirements.txt",
    ".\omcrm\config.py",
    ".\omcrm\config_vars.py",
    ".\omcrm\__init__.py"
)

foreach ($file in $configFiles) {
    if (Test-Path -Path $file) {
        try {
            Write-Host "Processing file: $file" -ForegroundColor Gray
            (Get-Content $file) -replace 'eeazycrm', 'omcrm' | Set-Content $file
            (Get-Content $file) -replace 'EeazyCRM', 'OMCRM' | Set-Content $file
        } catch {
            Write-Host "Error updating file $file: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "File not found: $file. Skipping." -ForegroundColor Yellow
    }
}
Write-Host "Configuration files updated successfully" -ForegroundColor Green

# 6. Update deployment files
$deploymentFiles = @(
    ".\deployment_guide.md"
)

foreach ($file in $deploymentFiles) {
    if (Test-Path -Path $file) {
        try {
            Write-Host "Processing deployment file: $file" -ForegroundColor Gray
            (Get-Content $file) -replace 'eeazycrm', 'omcrm' | Set-Content $file
            (Get-Content $file) -replace 'EeazyCRM', 'OMCRM' | Set-Content $file
            (Get-Content $file) -replace 'Eeazy', 'OM' | Set-Content $file
        } catch {
            Write-Host "Error updating deployment file $file: $($_.Exception.Message)" -ForegroundColor Red
        }
    } else {
        Write-Host "Deployment file not found: $file. Skipping." -ForegroundColor Yellow
    }
}
Write-Host "Deployment files updated successfully" -ForegroundColor Green

# 7. Replace uppercase and title case variations
Write-Host "Replacing uppercase and title case variations..." -ForegroundColor Cyan
try {
    Get-ChildItem -Path . -Filter *.* -Recurse -Exclude *.git,*.pyc,*.pyo,*.pyd,*.gitignore | ForEach-Object {
        # Only process text files
        if ((Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue) -ne $null) {
            # Process the file content
            $content = Get-Content $_.FullName -Raw
            if ($content -match "EeazyCRM|Eeazy CRM|EEAZYCRM") {
                Write-Host "Updating case variations in: $($_.FullName)" -ForegroundColor Gray
                $content = $content -replace 'EeazyCRM', 'OMCRM'
                $content = $content -replace 'Eeazy CRM', 'OM CRM'
                $content = $content -replace 'EEAZYCRM', 'OMCRM'
                Set-Content -Path $_.FullName -Value $content
            }
        }
    }
    Write-Host "Case variations updated successfully" -ForegroundColor Green
} catch {
    Write-Host "Error updating case variations: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  Renaming completed!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Check for any remaining references to 'eeazycrm'" -ForegroundColor Yellow
Write-Host "2. Update your database name if needed" -ForegroundColor Yellow
Write-Host "3. Test all functionality of your application" -ForegroundColor Yellow
Write-Host ""
Write-Host "If you're deploying to a server, update your service files and Nginx configuration." -ForegroundColor Yellow
Write-Host "" 