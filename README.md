# EECE430 Assignment 6 - AI Inventory Agent CI/CD

This is the supplied Django/Gemini inventory agent with a GitHub Actions pipeline that checks and tests the app, builds a Docker image, publishes it to GitHub Container Registry (GHCR), and deploys the tested commit to a Windows self-hosted runner.

## Pipeline

1. Pull requests and pushes to `main`: install dependencies, check Django, verify migrations, run mocked unit/integration tests, build the container, and check its HTTP endpoints. No Gemini key is needed for CI.
2. Successful pushes to `main`: publish `ghcr.io/<owner>/<repository>:<commit-sha>` and `:latest`. The repository name is lowercased automatically. GHCR authentication uses the temporary `GITHUB_TOKEN`.
3. After publication: a Windows runner with the `inventory-deploy` label pulls the exact commit image, replaces the application container, and waits for its Docker health check. The SQLite database survives replacement in the `inventory-agent-data` volume.

The app is bound to `127.0.0.1:8000` for the local lab demonstration. It has no inventory authorization layer and is intended for local lab use. Deployment can briefly interrupt requests while the container is replaced.

## Run locally with Docker

From this directory in PowerShell:

```powershell
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_urlsafe(50))"
# Edit .env locally: set DJANGO_SECRET_KEY to the generated value and add your Gemini API key.
docker compose up -d --build
docker compose logs web
```

Open <http://localhost:8000> and <http://localhost:8000/health/>. To create an optional administrator:

```powershell
docker compose exec web python manage.py createsuperuser
```

To stop the local app without deleting inventory: `docker compose down`. Stop this Compose deployment before starting the CI/CD deployment, because both use port 8000.

The page and health endpoint work without a Gemini key; sending a chat message requires a valid key. Set `GEMINI_MODEL` if your account uses a different available model. Real Gemini calls may consume your API quota. CI uses mocks and makes no model calls.

## Run the checks without Docker

Use Python 3.13:

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py check
.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.venv\Scripts\python.exe manage.py test --verbosity 2
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py runserver
```

Tests cover inventory mutations, insufficient/missing stock, HTTP health, session continuity, empty messages, error handling, reset, tool execution, missing API configuration, and the maximum agent loop length.

## GitHub repository and deployment setup

1. Create a new repository under your account and push this directory's contents with `.github/workflows/ci.yml` at the repository root. Do not push the enclosing assignment/reference folders. Use `main` as the default branch.
2. In repository **Settings > Collaborators > Add people**, invite `am38@aub.edu.lb` with collaborator/write access. If GitHub cannot find that email, obtain the instructor's GitHub username. Do not guess a matching person.
3. In **Settings > Actions > General**, ensure Actions is enabled and repository policy allows the workflow's `packages: write` permission.
4. In **Settings > Actions > Runners > New self-hosted runner**, select **Windows / x64**. Follow GitHub's current download, checksum verification, extraction, and configuration commands. Keep the runner outside the project directory. Give it name `inventory-local` and additional label `inventory-deploy`. Use a dedicated runner for this repository. The workflow never sends pull requests to this runner.
5. Keep Docker Desktop running in **Linux container** mode. Run `docker info` in the same account that starts the runner. Install/keep Git and Windows PowerShell available.
6. Create `$env:USERPROFILE/.inventory-agent.env` on the runner computer by copying `.env.example`; set a stable `DJANGO_SECRET_KEY` and your real `GEMINI_API_KEY`. Keep this file outside the repository. It is read locally by Docker; it is not sent through workflow secrets or baked into the image.
7. Start the runner with `./run.cmd` and keep it running for the demo. It must appear **Idle** on GitHub. Use a current runner release compatible with the action versions in the workflow.
8. Push to `main`, or use **Actions > Inventory Agent CI/CD > Run workflow**. Wait for `test`, `publish`, and `deploy` to finish. Without an online labeled runner, `deploy` remains queued.
9. Open <http://localhost:8000> to demonstrate the deployed application.

The workflow creates its first image/package automatically. If GHCR returns a permission error, check package access under **Package settings > Manage Actions access** and grant this repository access. For private packages, the deployment uses `GITHUB_TOKEN` with `packages: read`.

## Lab demonstration

- Show the repository and the pending/accepted collaborator invitation.
- Show a successful workflow with all three jobs.
- Open the chat and add 15 hammers, check stock, then remove 3. Verify 12 remain (start with a new item name if there is existing stock).
- Open `chat/templates/chat.html`, change the heading to `Inventory Agent - Assignment 6 Demo`, commit, and push to `main`.
- Watch the new workflow complete. Refresh the page to show the new heading without manually pulling an image.
- Verify the same inventory quantity remains after deployment. Show `docker ps`, the healthy container, the commit image tag, and the named data volume.
- Keep the machine, Docker Desktop, and runner running during the demonstration.

## Files and changes from the starter

The original model, migration, inventory functions, and chat interface are retained. The Gemini client is initialized only when chat runs so CI/startup do not require an API key. Configuration comes from the environment; `.env`, database files, and caches are excluded from Git and the Docker build. The container applies migrations on startup and serves through Waitress with WhiteNoise for admin static files. A database connectivity health endpoint supports automated verification. Detailed model exceptions are logged on the server and are not shown in the browser.

## Reference documentation

- [GitHub: building and testing Python](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)
- [GitHub: adding self-hosted runners](https://docs.github.com/en/actions/hosting-your-own-runners/managing-self-hosted-runners/adding-self-hosted-runners)
- [GitHub: working with the container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [Gemini Interactions API](https://ai.google.dev/gemini-api/docs/interactions)
