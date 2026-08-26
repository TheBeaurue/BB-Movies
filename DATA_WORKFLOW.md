# BB Movies V2.1 — Data Workflow

1. Fill the CSV templates inside `backend/data/`.
2. Use reliable/licensed/public sources and keep `source` and `last_verified`.
3. Do not add uncertain facts just to increase the count.
4. Run:
   `.\.venv\Scripts\python.exe -m backend.import_csv`
5. Verify:
   `http://127.0.0.1:8001/api/health`
6. Only after verification should the data be used by BB.

Target:
- First: 20 movies / 30 songs
- Then: 100 movies / 200 songs
- Final major-project target: 500+ movies / 1,000+ songs

This version provides the pipeline and schema; the demo seed remains intentionally small.
