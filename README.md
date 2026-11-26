# AgentTown — Agent Civilization

AgentTown is an experimental local civilization simulator with five role-based worker agents and a Creator (God) control view.

## One-click start on Windows

1. Download this repository as a ZIP from GitHub and extract it.
2. Open the extracted `agenttown` folder.
3. Double-click **`START_AGENTTOWN.bat`**.
4. Wait for the browser to open at http://127.0.0.1:8000.

Python 3.9 or newer must be installed on Windows. The launcher checks for the Python launcher (`py`) or `python`, starts the local server in a minimized window, waits for it to respond, and opens the dashboard. If Windows shows a security prompt, choose the option to run the local batch file only if you trust this project.

To stop AgentTown, double-click **`STOP_AGENTTOWN.bat`**. You can also close the minimized AgentTown Server window.

## Manual start

Open a terminal in this folder and run:

    py -3 app.py

If that command is unavailable, try:

    python app.py

Then visit http://127.0.0.1:8000. Press Ctrl+C in the server window to stop it.

## What currently works

- Five local role workers: Mayor, Researcher, Developer, Designer, Auditor
- Creator decrees that dispatch work to a selected worker
- Council cycle that assigns work to all five workers
- Pause and resume controls
- SQLite persistence in `agenttown.db`
- Agent work results and civilization event history
- No paid API or third-party Python package required

## Important limitations

This is a local, deterministic workflow engine. The workers generate role-based plans; they are **not yet LLM-powered agents**, do not independently browse the live web, and do not execute arbitrary code. The Python server runs only while your computer is on and the server process is running. GitHub Pages hosts a separate static preview; it cannot run this Python backend.

The database file `agenttown.db` is created in this folder and is ignored by Git. Back it up if you want to preserve your local civilization history.

## Safety

The server binds to `127.0.0.1` so it is accessible only from your own computer by default. Do not expose it to the public internet without authentication and a security review.
