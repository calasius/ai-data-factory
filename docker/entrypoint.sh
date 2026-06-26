#!/bin/sh
set -e

# The opencode generation server is started by the FastAPI app (lifespan),
# so there is nothing to bootstrap here. Kept as a hook for future setup.

exec "$@"
