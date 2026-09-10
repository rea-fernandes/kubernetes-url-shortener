# Kubernetes URL Shortener

A small URL shortener built with **FastAPI**, **Redis**, **Docker**, and **Kubernetes**.

The application creates deterministic six-character short codes from submitted URLs, stores the URL mappings in Redis, and redirects requests for the generated codes to the original URL.

The project demonstrates containerization, Kubernetes deployments, service discovery, persistent storage, health probes, NGINX Ingress, Kubernetes Secrets and ConfigMaps, Helm, and Horizontal Pod Autoscaling.

## Architecture

```text
                         ┌──────────────────┐
                         │      Client      │
                         └────────┬─────────┘
                                  │
                                  │ HTTP
                                  ▼
                         ┌──────────────────┐
                         │  NGINX Ingress   │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │   FastAPI API Service    │
                    │      ClusterIP :80       │
                    └────────────┬─────────────┘
                                 │
                    ┌────────────┴─────────────┐
                    │                          │
                    ▼                          ▼
          ┌──────────────────┐       ┌──────────────────┐
          │   FastAPI Pods   │       │  Redis Service   │
          │   2–5 replicas   │       │      :6379       │
          └──────────────────┘       └────────┬─────────┘
                                              │
                                              ▼
                                     ┌──────────────────┐
                                     │    Redis PVC     │
                                     │       1 Gi       │
                                     └──────────────────┘
```

### Kubernetes components

The raw Kubernetes manifests deploy:

* FastAPI API Deployment
* Multiple API replicas
* ClusterIP Service
* Redis Deployment
* Redis ClusterIP Service
* Redis PersistentVolumeClaim
* Kubernetes Secret
* Kubernetes ConfigMap
* NGINX Ingress
* Readiness and liveness probes

The Helm chart manages the API-side Kubernetes resources and HPA. Redis is intentionally deployed separately so that the API chart can connect to an existing Redis service.

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

## Deploy to Kubernetes with manifests

The raw Kubernetes manifests deploy the application and Redis separately.

The API image is:

```text
url-shortener:latest
```

The manifests use:

```yaml
imagePullPolicy: Never
```

This is intended for a local Kubernetes cluster using the same local image store.

### Build the image

Build the image before deploying:

```bash
docker build -t url-shortener:latest .
```

If using a local cluster such as Docker Desktop or kind, make sure the image is available to the cluster.

### Apply the manifests

Create the Kubernetes Secret:

```bash
kubectl apply -f secret.yaml
```

Create the ConfigMap:

```bash
kubectl apply -f configmap.yaml
```

Deploy Redis:

```bash
kubectl apply -f redis.yaml
```

Deploy the API:

```bash
kubectl apply -f deployment.yaml
```

Create the API Service:

```bash
kubectl apply -f service.yaml
```

Create the Ingress:

```bash
kubectl apply -f ingress.yaml
```

Or apply all resources individually in the same order:

```bash
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f redis.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

### Verify the deployment

Check the pods:

```bash
kubectl get pods
```

Check services:

```bash
kubectl get services
```

Check the Ingress:

```bash
kubectl get ingress
```

Check the API:

```bash
curl http://localhost/health
```

Create a short URL through the Ingress:

```bash
curl -X POST http://localhost/shorten \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://example.com"}'
```

### Redis configuration

The manifest deployment connects to:

```text
redis-service:6379
```

Redis authentication is configured using a Kubernetes Secret.

The example Secret contains a local-test password. Replace it before using the deployment outside a local development cluster.

Do not commit production credentials or real secrets to the repository.

## Persistent storage

Redis uses a Kubernetes `PersistentVolumeClaim` with a requested capacity of `1Gi`.

The PVC allows Redis data to survive Redis pod replacement.

Verify the PVC:

```bash
kubectl get pvc
```

Example:

```text
NAME        STATUS   VOLUME   CAPACITY   ACCESS MODES
redis-pvc   Bound             1Gi        RWO
```

The storage behavior can be tested by creating a Redis key, deleting the Redis pod, and verifying that the key remains available after the new pod starts.

## Health probes

The API deployment uses Kubernetes health probes to allow Kubernetes to distinguish between healthy and unhealthy containers.

The health endpoint is:

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

## Deploy with Helm

The Helm chart is located in:

```text
url-shortener/
```

The chart deploys the API-side resources, including:

* FastAPI Deployment
* Kubernetes Service
* ServiceAccount
* NGINX Ingress
* HorizontalPodAutoscaler

Redis is not deployed by the Helm chart.

A Redis service and the `url-shortener-secret` Secret must already exist in the target namespace.

### Create the Redis Secret

For a local test deployment:

```bash
kubectl create secret generic url-shortener-secret \
  --from-literal=REDIS_PASSWORD='change-me'
```

### Install the Helm chart

```bash
helm install url-shortener ./url-shortener
```

### Upgrade an existing installation

```bash
helm upgrade url-shortener ./url-shortener
```

Or use the recommended install-or-upgrade command:

```bash
helm upgrade --install url-shortener ./url-shortener
```

### Override configuration

The default Helm values expect:

```text
Redis host: redis-service
Redis port: 6379
Ingress host: url-shortener.local
```

Values can be overridden during installation.

Example:

```bash
helm upgrade --install url-shortener ./url-shortener \
  --set redis.host=my-redis \
  --set redis.port=6379 \
  --set ingress.hosts[0].host=url-shortener.local
```

### Helm values

The chart defaults to:

```text
API replicas: 3
Minimum HPA replicas: 2
Maximum HPA replicas: 5
CPU target: 80%
Image: url-shortener:latest
Image pull policy: Never
```

## Horizontal Pod Autoscaling

The Helm deployment includes a Kubernetes HorizontalPodAutoscaler.

The HPA scales the API Deployment between:

```text
Minimum replicas: 2
Maximum replicas: 5
CPU target: 80%
```

Check the HPA:

```bash
kubectl get hpa
```

Example:

```text
NAME            REFERENCE                  TARGETS       MINPODS   MAXPODS
url-shortener   Deployment/url-shortener   cpu: 4%/80%   2         5
```

CPU utilization is provided by Kubernetes Metrics Server.

Check resource metrics:

```bash
kubectl top pods
```

If `kubectl top` does not return metrics, verify that Metrics Server is installed and available in the cluster.

## Validate the Helm chart

Before installing the chart, validate its syntax:

```bash
helm lint ./url-shortener
```

Render the Kubernetes manifests without installing them:

```bash
helm template url-shortener ./url-shortener
```

Install or upgrade the release:

```bash
helm upgrade --install url-shortener ./url-shortener
```

Verify the resulting resources:

```bash
kubectl get pods
kubectl get services
kubectl get ingress
kubectl get hpa
```

Check the Helm release:

```bash
helm list
```

Get the release status:

```bash
helm status url-shortener
```

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
curl http://localhost/health
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

Remove the raw Kubernetes resources:

```bash
kubectl delete -f ingress.yaml
kubectl delete -f service.yaml
kubectl delete -f deployment.yaml
kubectl delete -f redis.yaml
kubectl delete -f configmap.yaml
kubectl delete -f secret.yaml
```

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

This project is intended as a portfolio and learning project.
