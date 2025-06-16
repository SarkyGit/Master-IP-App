# Web Client

This directory contains all HTML templates and static assets used by the
FastAPI server. The interface is styled using UnoCSS. To rebuild the CSS run:

```bash
npm run build:web
```

The command looks for templates under `web-client/templates/` and writes the
compiled stylesheet to `web-client/static/css/unocss.css`.
