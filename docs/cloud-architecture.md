# Cloud Server with Site-Level Replicas

This document proposes an architecture where each site runs an independent local replica that synchronizes with a central cloud server. The local instances cache data and continue functioning if the connection to the cloud is lost.

This document outlines the proposed design for Phase 6 of the project. The goal is to support optional cloud replication so that multiple sites can synchronize their data with a central server.

## Core Components

- **Load Balancer** – distributes inbound traffic to multiple cloud API instances for high availability.
- **Cloud Server / API** – a public FastAPI service that aggregates data from many local servers and exposes authentication and synchronization endpoints.
- **Central Database** – stores authoritative records. Rows include a `version` column so conflicts can be detected.
- **Sync Gateway** – a background service that processes incoming batches from sites and sends back new updates.
- **Local Replica** – an on-site FastAPI instance with its own database. Changes are queued in a local **worker queue** when offline.
- **Background Sync Jobs** – workers that push changes from local sites to the cloud and pull updates down.
- **Versioned Records** – database rows contain a monotonically increasing `version` field. Updates increment the version so conflicts can be detected.

## Data Flow and Resilience

<div class="w-full flex justify-center">
<svg width="550" height="210" viewBox="0 0 550 210" xmlns="http://www.w3.org/2000/svg" class="border border-gray-400 bg-gray-50 rounded-lg">
  <defs>
    <marker id="arrow" markerWidth="10" markerHeight="10" refX="5" refY="5" orient="auto" markerUnits="strokeWidth">
      <path d="M0,0 L0,10 L10,5 z" class="fill-gray-600" />
    </marker>
  </defs>
  <rect x="190" y="20" width="170" height="60" rx="8" class="fill-blue-200 stroke-blue-600" />
  <text x="275" y="55" text-anchor="middle" class="text-sm text-black">Load Balancer</text>
  <rect x="30" y="120" width="170" height="60" rx="8" class="fill-indigo-200 stroke-indigo-600" />
  <text x="115" y="155" text-anchor="middle" class="text-sm text-black">Local Replica</text>
  <rect x="350" y="120" width="170" height="60" rx="8" class="fill-green-200 stroke-green-600" />
  <text x="435" y="155" text-anchor="middle" class="text-sm text-black">Cloud API</text>
  <line x1="115" y1="120" x2="115" y2="80" stroke="gray" stroke-width="2" marker-end="url(#arrow)" />
  <line x1="435" y1="80" x2="435" y2="120" stroke="gray" stroke-width="2" marker-end="url(#arrow)" />
  <line x1="200" y1="50" x2="350" y2="50" stroke="gray" stroke-width="2" marker-end="url(#arrow)" />
  <line x1="350" y1="60" x2="200" y2="60" stroke="gray" stroke-width="2" marker-end="url(#arrow)" />
</svg>
</div>

1. Local replicas queue updates in their worker queue.
2. The connection to the cloud is always initiated by the local site because inbound traffic may be blocked by NAT or firewalls. A periodic job posts batched updates to the cloud `/sync` API via the load balancer using the site's API key.
3. The sync gateway processes updates and responds with any newer records for the site.
4. If conflicts occur (matching IDs with different versions), the cloud marks the record as needing manual resolution.
5. If the connection fails, the queue keeps retrying until the cloud is reachable.
6. Mobile clients communicate with either the local or cloud server depending on connectivity.

## Failover and Reconciliation

- **Offline Mode:** Local replicas use their database and worker queue so site operations continue without the cloud.
- **Automatic Resync:** Once online, pending updates are sent to the cloud. The cloud returns newer records so both sides converge.
- **Conflict Detection:** Each table stores a monotonically increasing `version` field. A higher version wins. Divergent versions trigger a conflict state that requires manual resolution.

## Networking Conditions

- Sites connect to the cloud over HTTPS. The load balancer terminates TLS and forwards to API workers.
- Local replicas retry requests with exponential backoff if the connection drops.
- The sync protocol is designed for limited bandwidth so it transfers small deltas rather than entire records.

## Deployment

Docker Compose files will be provided for both local and cloud roles. Kubernetes manifests will follow the same pattern with dedicated deployments for the database and web application.

