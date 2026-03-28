---
description: Destroy local DB and Vector Collection to test fresh state
---
# Wipe and Reindex Sequence
1. Stop backend services.
2. Delete the SQLite database inside `backend/.tmp_data/im_rag.db` (or appropriate local path).
3. Ensure the active Qdrant path inside `.tmp_data` is deleted.
4. Restart the backend. The API `lifespan` hook will automatically recreate the `init_qdrant_collections()` tables and local sql tables.
