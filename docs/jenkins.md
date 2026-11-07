# Running the pipeline in Jenkins

Requirements: Docker Desktop (Windows/macOS) or Docker Engine (Linux), and Git.

## 1. Start Jenkins

```bash
cd jenkins
docker compose up -d --build
docker exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
```

Open <http://localhost:8080>, paste the password, choose **Install suggested plugins** and
create an admin user. The image already contains the Docker CLI and the plugins the
pipeline needs (`jenkins/plugins.txt`).

## 2. Create the pipeline job

1. **New Item** → name `learner-analytics` → **Pipeline** → OK.
2. **Pipeline** section → Definition: **Pipeline script from SCM**.
3. SCM: **Git**, Repository URL `https://github.com/borzki/learner-analytics.git`,
   branch `*/main`, Script Path `Jenkinsfile`. Save.
4. Click **Build Now**. The first run also registers the polling trigger and parameters.

From then on Jenkins checks the repository every two minutes and builds each new commit.
GitHub webhooks cannot reach `localhost`, which is why polling is used.

## 3. Pipeline stages

| Stage | What it does |
|---|---|
| Checkout info | Prints the commit and Docker versions |
| Build test image | `docker build --target test` |
| Lint | `ruff check` and `ruff format --check` inside the test image |
| Unit tests | pytest with coverage ≥ 90 %; JUnit and coverage XML are published |
| Build image | `docker build --target runtime`, tagged with the build number and `latest` |
| Smoke test image | Runs `--version`, `simulate` and `analyze` inside the new image |
| Push to Docker Hub | Optional (`PUSH_IMAGE`), uses the `dockerhub` credentials |
| Deploy to staging | Replaces the `learner-analytics-staging` container with the new image |
| Verify deployment | Waits until the report page answers and prints `summary.json` |

After a successful build the staging report is at <http://localhost:8501>.

## 4. Optional: push to Docker Hub

Create an access token at hub.docker.com → Account settings → Personal access tokens.
In Jenkins: **Manage Jenkins → Credentials → System → Global → Add credentials** →
*Username with password*, ID `dockerhub`. Then **Build with Parameters**, tick
`PUSH_IMAGE` and set `DOCKERHUB_REPO` to `<your-user>/learner-analytics`.

## 5. Optional: Kubernetes (Minikube)

```bash
minikube start
minikube image load learner-analytics:latest
kubectl apply -f k8s/
kubectl get pods
minikube service learner-analytics-report
```

## Security note

The Jenkins container runs as root and has access to the host Docker socket. This is fine for
a local lab machine but not for a shared server, where Docker-in-Docker or separate build
agents should be used.
