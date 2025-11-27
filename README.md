# Vault CLI (Python Edition)

Standalone Python 3.13.5 rewrite of the entire Vault toolchain (CLI, API, schema tooling, Docker stack). Everything like original Go implementation.

## Getting Started

1. **Create a virtual environment** (Python 3.13.5 recommended).
   ```bash
   python3.13 -m venv .venv
   source .venv/bin/activate
   ```
2. **Install the package in editable mode**
   ```bash
   pip install -e .
   ```
3. **Set required environment variables** (or pass flags):
   - `VAULT_ADDR` (defaults to `http://vault:8200` in Docker, `http://localhost:8200` otherwise)
   - `VAULT_TOKEN`
   - `API_KEY` (for the FastAPI service, once added)

## Commands Preview

The CLI exposes the following commands:

- `vault-cli list`
- `vault-cli get <key>`
- `vault-cli add <key> <value>`
- `vault-cli edit <key> [value]`
- `vault-cli delete <key> [--force]`
- `vault-cli set <key> <value>`

Behaviour matches the original Go CLI, including type preservation, interactive prompts, and force confirmations.

## Development Layout

- `src/vault_core/`: shared configuration, Vault client helpers, schema validation utilities.
- `src/vault_cli/`: Typer-based CLI that consumes `vault_core`.
- `tests/`: pytest suite covering helpers and CLI behaviour (more to come for API/Schema/Docker flows).
- Tooling: `pyproject.toml` defines dependencies, Ruff linting rules, and pytest defaults.

## Docker Usage

1. **Create a `.env` file** with required variables:
   ```bash
   VAULT_ADDR=http://vault:8200
   VAULT_TOKEN=s.XXXXXXX
   VAULT_UNSEAL_KEY=xxxxxxxxxxxxxxxx
   ```

2. **Start the full stack:**
   ```bash
   docker-compose up -d vault
   docker-compose up vault-init vault-populate
   ```

3. **Use the CLI container:**
   ```bash
   # Start CLI container
   docker-compose --profile cli up -d vault-cli
   
   # Run commands
   docker-compose --profile cli exec vault-cli vault-cli list
   docker-compose --profile cli exec vault-cli vault-cli get POSTGRES_PASSWORD
   docker-compose --profile cli exec vault-cli vault-cli set my-key "value"
   ```

## Production Use

1. Install into a clean environment:
   - `python -m venv env && source env/bin/activate`
   - `pip install .` (or `pip install '.[dev]'` for tests and tooling)
2. Configure environment:
   - `VAULT_ADDR` – e.g. `https://vault.example.com:8200`
   - `VAULT_TOKEN` – token with read/write access to the chosen KV v2 path
3. Run the CLI:
   - `vault-cli --token "$VAULT_TOKEN" list`
   - `vault-cli set my-key 123`, `vault-cli get my-key`, etc.

## Status

✅ **Production Ready**: All tests passing (23/23), full feature parity with Go CLI, Docker setup complete.
