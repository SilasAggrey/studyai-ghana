import os
import subprocess

# Delete the database file
db_path = 'studyai.db'
if os.path.exists(db_path):
    os.remove(db_path)
    print(f"Deleted {db_path}")

# Now run alembic from scratch
result = subprocess.run(
    ['.\\.venv\\Scripts\\python.exe', '-m', 'alembic', 'upgrade', 'head'],
    capture_output=True, text=True, cwd='C:\\Users\\silas\\Documents\\Default Project\\studyai-ghana'
)
print("STDOUT:", result.stdout)
if result.stderr:
    print("STDERR:", result.stderr[:1000])