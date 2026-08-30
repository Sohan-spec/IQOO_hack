"""Modal wrapper. Confirm POST and status GET share one in-memory map."""

import modal

image = (
    modal.Image.debian_slim(python_version="3.13")
    .pip_install(
        "fastapi==0.115.12",
        "uvicorn[standard]==0.34.2",
        "segno==1.6.6",
    )
    .add_local_python_source("app")
    .add_local_file("index.html", "/root/index.html")
)

app = modal.App("relay-checkout", image=image)

_secret = modal.Secret.from_name(
    "checkout-merchant",
    required_keys=[
        "CHECKOUT_VPA",
        "CHECKOUT_PAYEE_NAME",
        "CHECKOUT_MERCHANT_ID",
        "CHECKOUT_CONFIRM_SECRET",
    ],
)


@app.function(
    secrets=[_secret],
    min_containers=1,
    max_containers=1,
    timeout=300,
    region="ap-southeast",
)
@modal.concurrent(max_inputs=50)
@modal.asgi_app(label="pay")
def web():
    import logging

    logging.basicConfig(level=logging.INFO)
    from app import app as fastapi_app

    return fastapi_app
