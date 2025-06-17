# Mobile Client

This directory contains a lightweight React Native application built with Expo. It allows logging in to the API server and viewing devices.

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
4. Scan the QR code printed by Expo or launch an Android/iOS emulator to open the app.

The screens use colours from the web client's "Dark Colourful" UnoCSS theme for a consistent look.

Use an Android or iOS emulator, or the Expo Go app on a device connected to the same LAN, to open the project. After logging in you can browse the device list which is loaded from the FastAPI `/api/v1/devices` endpoint.
