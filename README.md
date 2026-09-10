# Kubernetes URL Shortener

A small URL shortener built with FastAPI and Redis. The API creates deterministic six-character short codes from the submitted URL and redirects requests for those codes to the original URL.

## Requirements

- Python 3.12 or newer
- Docker and Docker Compose for local containers
- Kubernetes with an NGINX Ingress controller for the ingress examples
- Helm 3 for the Helm deployment

## API

The application listens on port `8000`.

### Health check

```http
GET /health
```

Returns `{"status":"healthy"}` when Redis is reachable, or HTTP `503` when it is not.

### Shorten a URL

```bash
curl -X POST http://localhost:8000/shorten \
	-H 'Content-Type: application/json' \
	-d '{"url":"https://example.com"}'
```

The response contains the generated `short_code` and the original `url`.

### Redirect

```http
GET /{short_code}
```

Redirects to the stored URL, or returns HTTP `404` if the code does not exist.

## Run locally

Install the Python dependencies and start Redis separately:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The application defaults to `REDIS_HOST=localhost`, `REDIS_PORT=6379`, and no Redis password. Set `REDIS_HOST`, `REDIS_PORT`, and `REDIS_PASSWORD` when using different Redis settings.

## Run with Docker Compose

Compose starts the API on `http://localhost:8000` and Redis on `localhost:6379`:

```bash
docker compose up --build
```

The Compose configuration connects the API to the `redis` service and does not configure a Redis password. Stop the services with:

```bash
docker compose down
```

## Deploy to Kubernetes with manifests

The raw manifests create three API replicas, a ClusterIP service, an NGINX ingress, one Redis replica, and a `1Gi` Redis persistent volume claim. The API image is configured as `url-shortener:latest` with `imagePullPolicy: Never`, so build the image in the same image store used by the cluster first:

```bash
docker build -t url-shortener:latest .
```

Apply the resources:

```bash
kubectl apply -f secret.yaml
kubectl apply -f configmap.yaml
kubectl apply -f redis.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml
```

The manifest deployment uses `redis-service:6379` and the Redis password `myredispassword` from `secret.yaml`. Replace that example secret before using it outside a local test cluster. The ingress host is `localhost` and requires an NGINX Ingress controller.

Check the deployment with:

```bash
kubectl get pods,services,ingress
curl http://localhost/health
```

## Deploy with Helm

The chart in `url-shortener/` deploys the API, service account, ClusterIP service, NGINX ingress, and an HPA. It does not deploy Redis, so a Redis service and the `url-shortener-secret` secret must already exist in the target namespace. The default chart values expect Redis at `redis-service:6379` and ingress at `url-shortener.local`.

Create the secret, then install the chart:

```bash
kubectl create secret generic url-shortener-secret \
	--from-literal=REDIS_PASSWORD='change-me'

helm install url-shortener ./url-shortener
```

To use different Redis settings or an ingress host, provide a values file or override values at install time. For example:

```bash
helm upgrade --install url-shortener ./url-shortener \
	--set redis.host=my-redis \
	--set redis.port=6379 \
	--set ingress.hosts[0].host=url-shortener.local
```

The chart defaults to three API replicas, enables autoscaling from two to five replicas at 80% CPU utilization, and uses the local image `url-shortener:latest` with `imagePullPolicy: Never`.

## Configuration

The application reads these environment variables:

| Variable | Default | Description |
| --- | --- | --- |
| `REDIS_HOST` | `localhost` | Redis hostname or service name |
| `REDIS_PORT` | `6379` | Redis port |
| `REDIS_PASSWORD` | unset | Redis password, when authentication is enabled |