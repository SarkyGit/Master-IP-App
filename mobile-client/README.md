# Mobile Client

This directory contains a lightweight React Native application using Expo. It performs a simple health check against the FastAPI server on launch.

## Setup

1. Install dependencies:
   ```bash
   npm install
   ```
2. Copy the environment file and set the server address:
   ```bash
   cp .env.example .env
   # edit .env and set BASE_URL
   ```
3. Start the development server:
   ```bash
   npm start
   ```

Use an Android or iOS emulator, or the Expo Go app on a device connected to the same LAN, to open the project. The home screen will display whether the API server responded to `/api/ping`.
