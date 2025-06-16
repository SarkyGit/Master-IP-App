# Kubernetes Deployment

This folder contains basic manifests to run the application on a Kubernetes cluster in either **local** or **cloud** mode.

## Files

- `postgres.yaml` – Deployment, service and persistent volume claim for PostgreSQL
- `configmap-local.yaml` / `configmap-cloud.yaml` – environment variables for each role
- `deployment-local.yaml` / `deployment-cloud.yaml` – deploy the FastAPI app
- `service-local.yaml` / `service-cloud.yaml` – expose the app via `NodePort`

## Usage

Apply the PostgreSQL resources first:

```bash
kubectl apply -f postgres.yaml
```

### Local Role

```bash
kubectl apply -f configmap-local.yaml
kubectl apply -f deployment-local.yaml
kubectl apply -f service-local.yaml
```

### Cloud Role

```bash
kubectl apply -f configmap-cloud.yaml
kubectl apply -f deployment-cloud.yaml
kubectl apply -f service-cloud.yaml
```

The service exposes port **8000**. Edit the manifests as needed to configure ingress or persistent storage classes in your cluster.

## Differences

| Mode  | Components                              | Persistent Volume | Exposed Port |
|-------|-----------------------------------------|-------------------|--------------|
| local | FastAPI Deployment, PostgreSQL          | `postgres-data`   | 8000         |
| cloud | FastAPI Deployment, PostgreSQL          | `postgres-data`   | 8000         |

Only the cloud mode exposes cloud sync endpoints and typically sits behind a dedicated ingress controller.
