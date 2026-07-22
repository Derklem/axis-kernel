# Full Index and Backup Script
Write-Host "📚 Indexing Arcane Library..." -ForegroundColor Cyan
python "$base\silent_indexer.py"
python "$base\recursive_manifest_updater.py"
Write-Host "🛡️ Creating Backup Snapshot..." -ForegroundColor Cyan
python "$base\backup_engine.py"
Write-Host "✅ Full Index and Backup Completed"
