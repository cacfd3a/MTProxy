# Testing MTProxy

This repository includes a test suite to verify the functionality of the MTProxy server. The tests run in Docker or directly on the host and check:
1.  **HTTP Stats**: Verifies the stats endpoint (port 8888) is accessible.
2.  **MTProto Port**: Verifies the MTProto port (443) accepts TCP connections.
3.  **End-to-End Connection**: Uses the `telethon` Python library to connect to Telegram via the proxy (requires credentials).

## Prerequisites

-   Docker and Docker Compose (for containerized testing)
-   `make` (for running the test command)
-   Python 3.9+ (for local script execution without Docker)

## Configuration

The tests are configured via environment variables. You can set these in your shell before running the tests.

**Required:**
- `MTPROXY_SECRET`: The secret for the MTProxy server (32 hex characters).

**Optional (but recommended for full verification):**
- `TELEGRAM_API_ID`: Your Telegram API ID (get from https://my.telegram.org).
- `TELEGRAM_API_HASH`: Your Telegram API Hash.

## Manual Connectivity Check

If tests are failing with timeouts, you can manually verify connectivity to Telegram servers from your environment (or inside the Docker container):

```bash
# Check connectivity to Telegram DC 2 (Europe)
nc -zv 149.154.167.50 443
# Expected output: Connection to 149.154.167.50 443 port [tcp/https] succeeded!
```

If this fails, your network (ISP, firewall, or hosting provider) is blocking connections to Telegram.

## Running Tests

### Using Make (Docker)

To run the tests in Docker, simply run `make test`. You need to export the environment variables first:

```bash
export MTPROXY_SECRET=d7f04aa6631130af1a153e7a5e12c291
export TELEGRAM_API_ID=12345
export TELEGRAM_API_HASH=your_api_hash

make test
```

This will:
1.  Build the MTProxy Docker image.
2.  Build the test runner Docker image.
3.  Start the proxy and test runner.
4.  Execute the connectivity checks.

### Running Locally (No Docker)

If you want to run the tests against a local instance or remotely:

1.  Install Python dependencies:
    ```bash
    pip install -r tests/requirements.txt
    ```
2.  Set environment variables:
    ```bash
    export MTPROXY_HOST=localhost  # or IP of your proxy
    export MTPROXY_SECRET=...
    export TELEGRAM_API_ID=...
    export TELEGRAM_API_HASH=...
    ```
3.  Run the script:
    ```bash
    python3 tests/test_proxy.py
    ```

## Troubleshooting

-   **Timeout**: If tests time out, check your network connection. MTProto proxies may be blocked by some ISPs.
-   **Telethon Connection Failed**: Ensure your API ID and Hash are correct.
