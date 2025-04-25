# Guide for Renaming EeazyCRM to OMCRM

This guide will help you rename the application from "eeazycrm" to "omcrm" throughout the codebase and file structure.

## 1. Prepare for Renaming

Before starting, make sure you:
- Have a backup of your code
- Are working in a development environment (not production)
- Have all requirements installed

## 2. Rename the Main Directory

```bash
# If you're starting fresh
git clone https://github.com/yourusername/eeazycrm.git omcrm
cd omcrm

# If you're renaming an existing directory
mv eeazycrm omcrm
cd omcrm
```

## 3. Rename the Package Directory

```bash
# Rename the main Python package
mv eeazycrm omcrm
```

## 4. Update Import Statements

Use a search and replace tool to find all instances of 'eeazycrm' in the codebase and replace them with 'omcrm':

### Linux/macOS command:
```bash
find . -type f -name "*.py" -exec sed -i 's/eeazycrm/omcrm/g' {} \;
find . -type f -name "*.html" -exec sed -i 's/eeazycrm/omcrm/g' {} \;
find . -type f -name "*.js" -exec sed -i 's/eeazycrm/omcrm/g' {} \;
find . -type f -name "*.md" -exec sed -i 's/eeazycrm/omcrm/g' {} \;
find . -type f -name "*.txt" -exec sed -i 's/eeazycrm/omcrm/g' {} \;
```

### Windows PowerShell commands:
```powershell
Get-ChildItem -Path . -Filter *.py -Recurse | ForEach-Object { (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName }
Get-ChildItem -Path . -Filter *.html -Recurse | ForEach-Object { (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName }
Get-ChildItem -Path . -Filter *.js -Recurse | ForEach-Object { (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName }
Get-ChildItem -Path . -Filter *.md -Recurse | ForEach-Object { (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName }
Get-ChildItem -Path . -Filter *.txt -Recurse | ForEach-Object { (Get-Content $_.FullName) -replace 'eeazycrm', 'omcrm' | Set-Content $_.FullName }
```

## 5. Update Configuration Files

Specifically check and update these files:
- `config.py` 
- `config_vars.py`
- `__init__.py`
- `deployment_config.py`
- `wsgi.py` 

## 6. Update Database URI References

Make sure to update the database name in your configuration:

```python
SQLALCHEMY_DATABASE_URI = 'postgresql://omuser:your_secure_password@localhost/omcrm'
```

## 7. Rename Database (If Needed)

If you already have a database:

```sql
-- PostgreSQL 
ALTER DATABASE eeazycrm RENAME TO omcrm;
```

## 8. Update Deployment Files

Edit the following files to reflect the new name:
- `wsgi.py`
- Any service files (e.g., `eeazycrm.service` → `omcrm.service`)
- Nginx configuration

For the Nginx config file:
```
sudo mv /etc/nginx/sites-available/eeazycrm /etc/nginx/sites-available/omcrm
sudo ln -sf /etc/nginx/sites-available/omcrm /etc/nginx/sites-enabled/
```

Update the content of the Nginx file to point to the new paths.

## 9. Update Templates

Check templates for any hardcoded references to "EeazyCRM" in:
- Title tags
- Branding elements
- Email templates

Update these to your new brand name "OMCRM".

## 10. Update Service File

If you have a systemd service file:

```bash
sudo mv /etc/systemd/system/eeazycrm.service /etc/systemd/system/omcrm.service
sudo nano /etc/systemd/system/omcrm.service
```

Edit the file to update:
- Description
- WorkingDirectory paths
- ExecStart paths

Then reload systemd:
```bash
sudo systemctl daemon-reload
sudo systemctl enable omcrm
sudo systemctl start omcrm
```

## 11. Test Everything

After making all these changes:
1. Create a new virtual environment if needed
2. Install dependencies
3. Run database migrations
4. Start the development server
5. Test all functionality

## 12. Common Issues

- **Import errors**: Double-check all imports, especially any that might be using absolute paths
- **Database connection issues**: Verify the database name and credentials
- **Static files not loading**: Ensure paths to static files are updated
- **404 errors**: Check URL routes for any hardcoded paths

If you encounter issues, check the application logs for specific error messages. 