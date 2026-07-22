# v0.2.2 Adversarial Drill Report

| Drill | Expected Warning | Passed |
|---|---|---|
| Clean fixture | **Integrity status:** OK | ✅ YES |
| Whole-file metadata tamper | HASH_MISMATCH | ✅ YES |
| Content tamper | HASH_MISMATCH, CONTENT_HASH_MISMATCH | ✅ YES |
| Wrong receipt content hash only | CONTENT_HASH_MISMATCH | ✅ YES |
| Archive without receipt | ORPHANED_ARCHIVE | ✅ YES |
| Multiple receipts |  | ✅ YES |
| Invalid timestamp | Invalid timestamp in receipt, window calculation failed. | ✅ YES |
| Quarantined receipt | PLATFORM_REFERENCE_MISMATCH, APPROVED_ARCHIVED_NOT_DEPLOYED | ✅ YES |