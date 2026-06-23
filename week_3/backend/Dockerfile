FROM python:3.14.4-bookworm
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
COPY . /app
ENV UV_NO_DEV=1
WORKDIR /app
RUN uv sync --locked
ENTRYPOINT ["uv", "run", "uvicorn"]
CMD ["--app-dir", "src", "--host", "0.0.0.0", "app:app"]
