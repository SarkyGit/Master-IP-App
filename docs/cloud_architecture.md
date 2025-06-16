# Cloud Architecture Overview

This document outlines the proposed design for Phase 6 of the project. The goal is to support optional cloud replication so that multiple sites can synchronize their data with a central server.

## Components

- **Local Servers** – instances of the FastAPI application running on-premises. Each manages devices for a single site.
- **Cloud Server** – a public instance that aggregates data from many local servers.
- **Background Sync Jobs** – workers that push changes from local sites to the cloud and pull updates down.
- **Versioned Records** – database rows contain a monotonically increasing `version` field. Updates increment the version so conflicts can be detected.

## Data Flow

1. Local servers operate independently and queue outgoing changes.
2. A periodic job posts batched updates to the cloud `/sync` API.
3. The cloud server stores updates and responds with any newer records for the site.
4. When conflicts occur (matching IDs with different versions), the cloud marks the record as needing manual resolution.
5. Mobile clients communicate with either the local or cloud server depending on connectivity.

## Deployment

Docker Compose files will be provided for both local and cloud roles. Kubernetes manifests will follow the same pattern with dedicated deployments for the database and web application.

