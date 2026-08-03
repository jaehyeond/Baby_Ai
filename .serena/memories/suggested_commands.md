# Suggested Commands

- Status first: `git status --short --branch`; branch: `git branch --show-current`.
- Canonical tests: `.\\.venv\\Scripts\\python.exe -m pytest tests\\ -q`.
- Focused exploratory audit: `.\\.venv\\Scripts\\python.exe -m pytest tests\\test_exploratory_signal_audit.py tests\\test_exploratory_question_probe.py -q`.
- Validate existing J1 exploratory audit without DB/GPU: `.\\.venv\\Scripts\\python.exe scripts\\research\\j1_exploratory_signal_audit.py audit-existing`.
- Compile touched Python: `.\\.venv\\Scripts\\python.exe -m py_compile <files>`.
- Diff hygiene: `git diff --check`.
- Run brain server when requested: `.\\.venv\\Scripts\\python.exe -m neural.baby.api_server --port 8000`.
- PowerShell UTF-8 reads: `Get-Content -Encoding utf8 <path>`.