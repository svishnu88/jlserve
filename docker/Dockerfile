# serverless_jlserve: the runtime image for jlserve deployments on JarvisLabs serverless.
#
# One image for every jlserve deployment. The customer's app file is not baked in;
# it arrives on the deployment filesystem, which the platform mounts at
# /model_weights, and the entrypoint finds it through JLSERVE_APP.
#
# Build from the repo root:
#   docker build -f docker/Dockerfile -t serverless_jlserve:latest .
#
# The heavy packages are preinstalled so a worker never needs the network to
# start: a worker boots with no network and only gets attached a few seconds
# later. The entrypoint installs only what the app declares and the image lacks.

FROM pytorch/pytorch:2.8.0-cuda12.8-cudnn9-runtime

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_NO_CACHE=1 \
    JLSERVE_APP=/model_weights/jlserve/app.py \
    JLSERVE_PORT=8000

# No apt step: the base carries CA certificates and Python, and the
# entrypoint needs nothing else. Keeps the build working on hosts that only
# allow HTTPS out (the Ubuntu mirrors are plain HTTP).

# uv: what jlserve uses to install an app's requirements at startup.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

# Common heavy packages, so the usual diffusers / transformers apps start offline.
RUN uv pip install \
      "diffusers>=0.31" "transformers>=4.45" accelerate safetensors \
      sentencepiece protobuf pillow

# jlserve itself, from this checkout (the deploy branch is not on PyPI yet).
COPY pyproject.toml README.md /opt/jlserve/
COPY jlserve /opt/jlserve/jlserve
RUN uv pip install /opt/jlserve

COPY docker/entrypoint.sh /usr/local/bin/jlserve-entrypoint
RUN chmod +x /usr/local/bin/jlserve-entrypoint

EXPOSE 8000
ENTRYPOINT ["/usr/local/bin/jlserve-entrypoint"]
