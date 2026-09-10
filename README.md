# Kubernetes URL Shortener

A small URL shortener built with **FastAPI**, **Redis**, **Docker**, and **Kubernetes**.

The application creates deterministic six-character short codes from submitted URLs, stores the URL mappings in Redis, and redirects requests for the generated codes to the original URL.

The project demonstrates containerization, Kubernetes deployments, service discovery, persistent storage, health probes, NGINX Ingress, Kubernetes Secrets and ConfigMaps, Helm, and Horizontal Pod Autoscaling.

## Architecture

```text
                    ┌─────────────────────┐
                    │       Client        │
                    └──────────┬──────────┘
                               │
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │    NGINX Ingress    │
                    │ url-shortener.local │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Kubernetes Service │
                    │    ClusterIP :80    │
                    └──────────┬──────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
                    ▼                     ▼
             ┌─────────────┐       ┌─────────────┐
             │ API Pod     │       │ API Pod     │
             │ FastAPI     │       │ FastAPI     │
             └──────┬──────┘       └──────┬──────┘
                    │                     │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Redis Service    │
                    │    :6379            │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │    Redis Pod        │
                    │    + PVC            │
                    └─────────────────────┘
```

### Kubernetes Components

| Component             | Purpose                                           |
| --------------------- | ------------------------------------------------- |
| FastAPI Deployment    | Runs the URL Shortener API                        |
| ClusterIP Service     | Provides internal access to API pods              |
| Redis Deployment      | Stores shortened URLs                             |
| Redis Service         | Provides internal Redis service discovery         |
| PersistentVolumeClaim | Provides persistent Redis storage                 |
| Secret                | Stores the Redis password                         |
| ConfigMap             | Provides non-sensitive configuration              |
| NGINX Ingress         | Exposes the API through `url-shortener.local`     |
| HPA                   | Automatically scales API replicas based on CPU    |
| Metrics Server        | Provides resource metrics for HPA                 |
| Helm                  | Packages and manages the API Kubernetes resources |

The Helm chart manages the API-side Kubernetes resources. Redis remains a separate Kubernetes workload because it represents the application's stateful data layer.

## Technologies

* Python 3.12+
* FastAPI
* Redis
* Docker
* Docker Compose
* Kubernetes
* Helm 3
* NGINX Ingress Controller
* Kubernetes Metrics Server

## Requirements

* Python 3.12 or newer
* Docker
* Docker Compose
* Kubernetes
* NGINX Ingress Controller for the ingress examples
* Helm 3
* Kubernetes Metrics Server for HPA metrics

## API

The application listens on port `8000`.

### Health check

```http
GET /health
```

Returns:

```json
{"status":"healthy"}
```

when Redis is reachable.

If Redis is unavailable, the endpoint returns HTTP `503`.

Example:

```bash
curl http://localhost:8000/health
```

### Shorten a URL

```http
POST /shorten
```

Example:

```bash
curl -X POST http://localhost:8000/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Example response:

```json
{
  "short_code": "c984d0",
  "url": "https://example.com"
}
```

The short code is deterministic: the same URL produces the same six-character code.

### Redirect

```http
GET /{short_code}
```

Example:

```bash
curl -i http://localhost:8000/c984d0
```

The application redirects to the stored URL.

If the short code does not exist, the API returns HTTP `404`.

## Run locally

Create a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start Redis separately, then start the API:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application defaults to:

```text
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<unset>
```

When using different Redis settings, configure:

```bash
export REDIS_HOST=<redis-host>
export REDIS_PORT=<redis-port>
export REDIS_PASSWORD=<redis-password>
```

## Run with Docker Compose

Docker Compose starts:

* FastAPI on `http://localhost:8000`
* Redis on `localhost:6379`

Start the services:

```bash
docker compose up --build
```

Test the API:

```bash
curl http://localhost:8000/health
```

Create a short URL:

```bash
curl -X POST http://localhost:8000/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

Stop the services:

```bash
docker compose down
```

The Compose configuration connects the API to the `redis` service and does not configure Redis authentication.

## Kubernetes Deployment

The application is deployed to Kubernetes using **Helm**.

The Helm chart manages the API-side Kubernetes resources:

* API Deployment
* API Service
* ServiceAccount
* NGINX Ingress
* HorizontalPodAutoscaler (HPA)
* Helm test

**Redis is deployed separately** because it represents the application's stateful data layer. The API connects to Redis through the Kubernetes Service `redis-service`.

### Prerequisites

The following components are required:

* Kubernetes cluster
* NGINX Ingress Controller
* Helm 3
* Kubernetes Metrics Server for HPA metrics
* Redis deployed as `redis-service`
* API container image available to the Kubernetes cluster

### Build the API image

Build the API image using the image name configured in `url-shortener/values.yaml`.

For example:

```bash
docker build -t url-shortener:latest .
```

If using a local Kubernetes cluster, make sure the image is available to the cluster before installing the Helm chart.

### Validate the Helm chart

Run Helm linting and template rendering before deployment:

```bash
helm lint ./url-shortener
helm template url-shortener ./url-shortener
```

### Install or upgrade

Install the release, or upgrade it if it already exists:

```bash
helm upgrade --install url-shortener ./url-shortener
```

Check the deployed resources:

```bash
kubectl get pods
kubectl get svc
kubectl get ingress
kubectl get hpa
```

Check the Helm release:

```bash
helm status url-shortener
```

### Access the application

The Helm chart exposes the API through the NGINX Ingress using:

```text
http://url-shortener.local
```

Test the health endpoint:

```bash
curl http://url-shortener.local/health
```

Expected response:

```json
{"status":"healthy"}
```

Create a shortened URL:

```bash
curl -X POST http://url-shortener.local/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

Example response:

```json
{"short_code":"c984d0","url":"https://example.com"}
```

The short code is deterministic: the same URL produces the same six-character code.

Test the redirect:

```bash
curl -i http://url-shortener.local/c984d0
```

### Redis configuration

The API connects to Redis through:

```text
REDIS_HOST=redis-service
REDIS_PORT=6379
```

Redis authentication is configured using the Kubernetes Secret `url-shortener-secret`.

The Redis workload uses a PersistentVolumeClaim so that stored URL mappings survive Redis pod replacement.

Verify the Redis resources:

```bash
kubectl get pods
kubectl get service redis-service
kubectl get pvc
```

### Health probes

The API deployment uses Kubernetes readiness and liveness probes based on:

```text
/health
```

The endpoint checks Redis connectivity.

This allows Kubernetes to:

* Remove unhealthy pods from Service endpoints
* Restart containers that become unhealthy
* Avoid sending traffic to pods that are not ready

Inspect the deployment with:

```bash
kubectl describe deployment url-shortener
```

### Helm Test

The Helm chart includes a test that verifies that the API Service is reachable from inside the Kubernetes cluster.

Run:

```bash
helm test url-shortener
```

A successful test reports:

```text
TEST SUITE:     url-shortener-test-connection

Phase:          Succeeded
```

The test pod is created by Helm and remains in the `Completed` state after the test finishes.

### Horizontal Pod Autoscaler

The Helm chart includes a HorizontalPodAutoscaler using CPU utilization.

Configuration:

```text
Minimum replicas: 2
Maximum replicas: 5
CPU target:       80%
```

Check the HPA:

```bash
kubectl get hpa url-shortener
```

View pod resource usage:

```bash
kubectl top pods -l app.kubernetes.io/instance=url-shortener
```

Metrics Server is required for CPU-based HPA metrics.

The HPA allows Kubernetes to automatically increase or decrease the number of API replicas based on CPU utilization.

### Final Helm validation

The complete deployment workflow can be validated with:

```bash
helm lint ./url-shortener
helm template url-shortener ./url-shortener
helm upgrade --install url-shortener ./url-shortener

kubectl get pods
kubectl get svc
kubectl get ingress
kubectl get hpa

helm test url-shortener
```

Application-level validation:

```bash
curl http://url-shortener.local/health
```

```bash
curl -X POST http://url-shortener.local/shorten \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com"}'
```

The deployment should show the API pods in `Running` state, the Ingress should expose `url-shortener.local`, and the Helm test should complete successfully.

> Note: HPA CPU metrics can temporarily display `<unknown>` while Kubernetes is refreshing metrics. Pod-level metrics can be checked independently with `kubectl top pods`.

## Configuration

The FastAPI application reads the following environment variables:

| Variable         | Default     | Description                                   |
| ---------------- | ----------- | --------------------------------------------- |
| `REDIS_HOST`     | `localhost` | Redis hostname or Kubernetes Service name     |
| `REDIS_PORT`     | `6379`      | Redis port                                    |
| `REDIS_PASSWORD` | unset       | Redis password when authentication is enabled |

## Useful Kubernetes commands

### Pods

```bash
kubectl get pods
```

Detailed pod information:

```bash
kubectl describe pod <pod-name>
```

### Logs

View API logs:

```bash
kubectl logs deployment/url-shortener
```

View logs from a specific pod:

```bash
kubectl logs <pod-name>
```

### Services

```bash
kubectl get services
```

### Ingress

```bash
kubectl get ingress
```

Detailed Ingress information:

```bash
kubectl describe ingress url-shortener
```

### Resource usage

```bash
kubectl top pods
```

### HPA

```bash
kubectl get hpa
```

Detailed HPA information:

```bash
kubectl describe hpa url-shortener
```

## Troubleshooting

### API pods are not starting

Check their status:

```bash
kubectl get pods
```

Then inspect the affected pod:

```bash
kubectl describe pod <pod-name>
```

Check its logs:

```bash
kubectl logs <pod-name>
```

### ImagePullBackOff or ErrImagePull

The Kubernetes deployment uses:

```yaml
imagePullPolicy: Never
```

Make sure the image exists in the image store used by the cluster:

```bash
docker images | grep url-shortener
```

Rebuild if necessary:

```bash
docker build -t url-shortener:latest .
```

### API cannot connect to Redis

Check the Redis pod:

```bash
kubectl get pods
```

Check the Redis service:

```bash
kubectl get service redis-service
```

Check the API environment:

```bash
kubectl describe deployment url-shortener
```

Verify that the API is configured to use:

```text
REDIS_HOST=redis-service
REDIS_PORT=6379
```

### Ingress does not work

Check the Ingress:

```bash
kubectl get ingress
```

Check the NGINX Ingress controller:

```bash
kubectl get pods -n ingress-nginx
```

Check the controller Service:

```bash
kubectl get service -n ingress-nginx
```

Inspect the Ingress configuration:

```bash
kubectl describe ingress url-shortener
```

Then test:

```bash
curl http://url-shortener.local/health
```

### HPA shows `<unknown>`

Check whether Metrics Server is available:

```bash
kubectl top pods
```

If metrics are unavailable, the HPA cannot calculate CPU utilization.

## Project structure

```text
.
├── app/
│   └── main.py
├── url-shortener/
│   ├── templates/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── ...
├── configmap.yaml
├── deployment.yaml
├── docker-compose.yml
├── Dockerfile
├── ingress.yaml
├── redis.yaml
├── secret.yaml
├── service.yaml
├── requirements.txt
└── README.md
```

## Kubernetes and Helm concepts demonstrated

This project demonstrates the following Kubernetes concepts:

* Deployments
* Pods
* Replica management
* Services
* ClusterIP networking
* Kubernetes DNS-based service discovery
* ConfigMaps
* Secrets
* PersistentVolumeClaims
* Persistent storage
* Readiness probes
* Liveness probes
* Resource requests and limits
* NGINX Ingress
* Horizontal Pod Autoscaling
* Metrics Server
* Helm charts
* Helm values
* Helm templating
* Helm upgrades
* Local container images

## Cleanup

Remove the Helm release:

```bash
helm uninstall url-shortener
```

If Redis is managed separately from Helm, remove its Kubernetes resources only when the stored data is no longer required.

Delete the Redis PVC if the stored data is no longer required:

```bash
kubectl delete pvc redis-pvc
```

## Future improvements

Possible extensions include:

* External Redis deployment or managed Redis
* TLS with cert-manager
* Authentication and rate limiting
* URL expiration
* Custom short-code support
* Prometheus metrics
* Grafana dashboards
* Distributed tracing
* CI/CD with GitHub Actions
* Automated container image publishing
* Production Kubernetes deployment
* NetworkPolicies
* PodDisruptionBudgets
* Redis high availability

## License

This project is intended as a portfolio and learning project and licensed under the MIT License. See the [LICENSE](LICENSE) file for details.