"""Modal wrapper around the FastAPI relay. Does not change queue/match/confirm logic."""

import modal

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install("fastapi==0.115.12", "uvicorn[standard]==0.34.2")
    .add_local_python_source("app", "auth")
)

app = modal.App("relay-owner-ingress", image=image)

# Hub state is in-process memory. One container so WS and POST /v1/transactions
# always meet. min_containers keeps the phone's socket from dying on scale-to-zero.
_secret = modal.Secret.from_name("relay-hmac", required_keys=["RELAY_SECRET"])


@app.function(
    secrets=[_secret],
    min_containers=1,
    max_containers=1,
    timeout=86400,
    region="ap-southeast",
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app(label="relay")
def web():
    import logging

    logging.basicConfig(level=logging.INFO)
    from app import app as fastapi_app

    return fastapi_app
