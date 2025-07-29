-- PostgreSQL migration to add client tracking fields
-- Add online activity tracking columns to the lead table

-- Add last_login_at column
ALTER TABLE lead ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMP;

-- Add last_seen_at column  
ALTER TABLE lead ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMP;

-- Add login_count column with default value
ALTER TABLE lead ADD COLUMN IF NOT EXISTS login_count INTEGER DEFAULT 0;

-- Show the updated table structure
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns 
WHERE table_name='lead' AND table_schema='public'
AND column_name IN ('last_login_at', 'last_seen_at', 'login_count')
ORDER BY column_name; 