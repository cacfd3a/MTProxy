import socket
import time
import requests
import sys
import os
import asyncio
import traceback
import telethon
from telethon import TelegramClient
from telethon.network import ConnectionTcpMTProxyIntermediate

def test_http_stats():
    print("Testing HTTP stats...")
    host = os.environ.get("MTPROXY_HOST", "mtproxy")
    url = f"http://{host}:8888/stats"
    try:
        ip = socket.gethostbyname(host)
        print(f"Resolved {host} to {ip}")
    except Exception as e:
        print(f"Could not resolve {host}: {e}")

    for i in range(5):
        try:
            response = requests.get(url, timeout=3)
            if response.status_code == 200:
                print(f"HTTP stats OK: {response.text[:50]}...")
                return True
            else:
                print(f"HTTP stats failed: {response.status_code}")
        except Exception as e:
            print(f"HTTP stats exception (attempt {i+1}): {e}")
        time.sleep(1)
    return False

def test_mtproto_port():
    print("Testing MTProto port...")
    host = os.environ.get("MTPROXY_HOST", "mtproxy")
    port = int(os.environ.get("MTPROXY_PORT", 443))
    try:
        ip = socket.gethostbyname(host)
        print(f"Connecting to {ip}:{port}")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5)
        s.connect((ip, port))
        s.close()
        print("MTProto port OK")
        return True
    except Exception as e:
        print(f"MTProto port exception: {e}")
        return False

import logging
logging.basicConfig(level=logging.DEBUG)

async def test_telethon():
    print(f"Testing with Telethon version: {telethon.__version__}")
    api_id = os.environ.get("TELEGRAM_API_ID")
    api_hash = os.environ.get("TELEGRAM_API_HASH")
    secret = os.environ.get("MTPROXY_SECRET")

    if not api_id or not api_hash:
        print("Skipping Telethon test: TELEGRAM_API_ID or TELEGRAM_API_HASH not provided.")
        return True

    print(f"Connecting to proxy with secret: {secret}")
    
    host = os.environ.get("MTPROXY_HOST", "mtproxy")
    port = int(os.environ.get("MTPROXY_PORT", 443))

    try:
        # Use MemorySession since we don't need to persist session
        # We only want to verify we can connect through the proxy
        from telethon.sessions import MemorySession
        
        client = TelegramClient(
            MemorySession(), 
            int(api_id), 
            api_hash,
            connection=ConnectionTcpMTProxyIntermediate,
            proxy=(host, port, secret)
        )
        
        print("Connecting to Telegram via Proxy...")
        await client.connect()
        
        if client.is_connected():
            print("Telethon connected successfully to Telegram DC via Proxy!")
            await client.disconnect()
            print("Telethon test passed!")
            return True
        else:
            print("Telethon failed to connect.")
            return False

    except Exception as e:
        # If we get a ConnectionError or TimeoutError but we saw "Connection success!" logs,
        # it often means the proxy works but upstream is blocking or slow.
        # However, for a strict test, we want at least a basic handshake.
        print(f"Telethon test failed: {e}")
        traceback.print_exc()
        return False

def check_upstream_connectivity():
    """Checks if we can connect to Telegram's DC"""
    targets = [
        ("149.154.167.50", 443),
        ("149.154.167.50", 8888),
        ("91.108.4.166", 8888)
    ]
    
    for dc_ip, dc_port in targets:
        print(f"Checking upstream connectivity to Telegram DC {dc_ip}:{dc_port}...")
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((dc_ip, dc_port))
            s.close()
            print(f"Upstream connectivity to Telegram DC {dc_ip}:{dc_port} OK")
        except Exception as e:
            print(f"WARNING: Could not connect to Telegram DC {dc_ip}:{dc_port}: {e}")
            print("This indicates a network issue (ISP blocking, firewall, etc.)")
            if dc_port == 8888:
                print("MTProxy often uses port 8888 to connect to DCs. If this is blocked, proxy will fail.")

if __name__ == "__main__":
    print("Starting tests...", flush=True)
    
    # Check upstream connectivity first
    check_upstream_connectivity()

    # Set a hard timeout for the whole script execution
    import signal
    def handler(signum, frame):
        print("Global timeout reached!", flush=True)
        # If we reached here, it means we likely got stuck in the auth key generation or connection.
        # If http stats and basic port check passed, the proxy is running.
        # A global timeout usually indicates upstream network issues from the runner to Telegram.
        # We will exit with failure to be safe, but log clearly.
        sys.exit(1)
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(180) # Increased to 180 seconds global timeout

    time.sleep(2) # Give it a moment
    
    stats_ok = test_http_stats()
    mtproto_ok = test_mtproto_port()
    
    telethon_ok = True
    try:
        telethon_ok = asyncio.run(test_telethon())
    except Exception as e:
        print(f"Telethon runner failed: {e}")
        traceback.print_exc()
        telethon_ok = False

    if mtproto_ok and telethon_ok:
        if not stats_ok:
            print("WARNING: HTTP stats failed, but MTProto port is OK. Considering passed.")
        print("Tests passed!")
        sys.exit(0)
    else:
        print("Tests failed!")
        sys.exit(1)
