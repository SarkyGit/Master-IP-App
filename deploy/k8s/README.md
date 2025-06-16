# Kubernetes Deployment

This folder contains manifests to run the application on a Kubernetes cluster. Resources are split so you can enable the **local** or **cloud** role as needed.

## Files

- `app-config.yaml` – ConfigMap providing `ROLE` and `DATABASE_URL`
- `app-secret.yaml` – Secret containing `SECRET_KEY`
- `app-deployment.yaml` – FastAPI Deployment with migrations volume
- `app-service.yaml` – ClusterIP service exposing the app
- `db-deployment.yaml` – PostgreSQL Deployment and PVC
- `db-service.yaml` – ClusterIP service for PostgreSQL
- `ingress.yaml` – Optional ingress for the cloud role

## Usage

Create the namespace if it does not exist:

```bash
kubectl create namespace master-ip
```

Validate the manifests:

```bash
kubectl apply --dry-run=client -f db-deployment.yaml
kubectl apply --dry-run=client -f db-service.yaml
kubectl apply --dry-run=client -f app-config.yaml
kubectl apply --dry-run=client -f app-secret.yaml
kubectl apply --dry-run=client -f app-deployment.yaml
kubectl apply --dry-run=client -f app-service.yaml
# Cloud role only
kubectl apply --dry-run=client -f ingress.yaml
```

Edit `app-config.yaml` to set the desired `ROLE` (`local` or `cloud`) and database connection string. Apply the files without `--dry-run=client` to create the resources.

The cloud role requires the ingress manifest to expose the sync API over HTTPS. Local sites run the sync workers but typically do not need ingress.
