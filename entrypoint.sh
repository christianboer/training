#!/bin/sh

# Start uvicorn in background (only if API key is set)
if [ -n "$ANTHROPIC_API_KEY" ]; then
    cd /app
    uvicorn server:app --host 127.0.0.1 --port 8000 &
fi

# Start nginx in foreground
nginx -g 'daemon off;'
