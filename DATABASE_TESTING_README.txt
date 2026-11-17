MULTI PLAZA DATABASE API TEST

1. Install Python 3.10+ on Windows.
2. Extract this ZIP.
3. Open the Multi_Plaza_Railway_Updated folder.
4. Double-click RUN_DATABASE_TESTS.bat.
   Or run:
      py -m pip install -r requirements.txt
      py test_database.py

IMPORTANT:
- The test uses a temporary local SQLite database.
- It does NOT connect to or change Railway PostgreSQL.
- Flask is a required dependency and is already listed in requirements.txt.
- If pip says ModuleNotFoundError / package missing, install requirements first.
- To verify live Railway, open /api/database/status after deployment and then
  create one harmless test record in each section and check it in Railway SQL.
