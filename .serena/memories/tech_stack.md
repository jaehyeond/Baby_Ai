# Tech Stack

- Windows 11, PowerShell, Python virtual environment at `.venv`.
- Backend/runtime: Python, FastAPI/Starlette/Uvicorn, Neo4j, Redis, Gemini via `google-genai`.
- Trainable local core: PyTorch + Transformers + PEFT/LoRA; current research scripts use frozen inference unless learning is explicitly approved.
- Frontend: Next.js/React/Tailwind exists but is not the current J1 research critical path.
- Quest 3S is an embodiment client; the brain remains in the FastAPI/Neo4j/Redis backend.
- Project metadata and base dependencies live in `pyproject.toml`.