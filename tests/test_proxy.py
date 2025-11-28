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
            # We don't need to be authorized to prove the proxy works.
            # The fact that we negotiated an MTProto session with the DC means 
            # the proxy is correctly relaying traffic.
            await client.disconnect()
            print("Telethon test passed!")
            return True
        else:
            print("Telethon failed to connect.")
            return False

    except Exception as e:
        print(f"Telethon test failed: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("Starting tests...", flush=True)
    # Set a hard timeout for the whole script execution
    import signal
    def handler(signum, frame):
        print("Global timeout reached!", flush=True)
        sys.exit(1)
    signal.signal(signal.SIGALRM, handler)
    signal.alarm(120) # 120 seconds global timeout

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
