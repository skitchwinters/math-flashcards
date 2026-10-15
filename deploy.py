#!/usr/bin/env python3
"""
deploy.py - Direct Vercel Deployment for Jessup Math Flashcards
Deploys the static web application directly to Vercel production using the Vercel REST API.
Retrieves deployment tokens from Bitwarden, Windows Credential Manager, Registry, or Environment.
"""

import os
import json
import base64
import winreg
import urllib.request
import urllib.error
import subprocess
from datetime import date

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_COUNT_FILE = os.path.join(PROJECT_DIR, '.deploy_count')
VERCEL_DAILY_LIMIT = 100
PROJECT_NAME = "jessup-math-flashcards"

def get_bw_env() -> dict:
    env = os.environ.copy()
    try:
        ukey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment')
        upath, _ = winreg.QueryValueEx(ukey, 'Path')
        winreg.CloseKey(ukey)
    except OSError:
        upath = ''
    try:
        mkey = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment')
        mpath, _ = winreg.QueryValueEx(mkey, 'Path')
        winreg.CloseKey(mkey)
    except OSError:
        mpath = ''
    env['PATH'] = f"{upath};{mpath};{env.get('PATH', '')}"
    return env

def get_secret_from_bitwarden(item_name: str) -> str | None:
    try:
        import keyring
        client_id     = keyring.get_password("bitwarden_agent", "BW_CLIENTID")
        client_secret = keyring.get_password("bitwarden_agent", "BW_CLIENTSECRET")
        bw_password   = keyring.get_password("bitwarden_agent", "BW_PASSWORD")
    except Exception:
        return None

    if not all([client_id, client_secret, bw_password]):
        return None

    env = get_bw_env()
    env['BW_CLIENTID']     = client_id
    env['BW_CLIENTSECRET'] = client_secret
    env['BW_PASSWORD']     = bw_password

    try:
        status = subprocess.run(['bw', 'status'], capture_output=True, text=True, env=env, shell=True)
        if 'unauthenticated' in status.stdout:
            subprocess.run(['bw', 'login', '--apikey'], capture_output=True, text=True, env=env, shell=True, check=True)

        unlock = subprocess.run(['bw', 'unlock', '--passwordenv', 'BW_PASSWORD', '--raw'], capture_output=True, text=True, env=env, shell=True, check=True)
        session = unlock.stdout.strip()
        if not session:
            return None

        result = subprocess.run(['bw', 'get', 'password', item_name, '--session', session], capture_output=True, text=True, env=env, shell=True, check=True)
        return result.stdout.strip() or None
    except Exception as e:
        print(f"Bitwarden lookup notice: {e}")
        return None

def _from_credential_manager(key_name: str) -> str | None:
    try:
        import keyring
        return keyring.get_password("bitwarden_agent", key_name) or None
    except Exception:
        return None

def _from_registry(var_name: str) -> str | None:
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Environment')
        val, _ = winreg.QueryValueEx(key, var_name)
        winreg.CloseKey(key)
        return val or None
    except Exception:
        return None

def get_vercel_token() -> str:
    try:
        token = get_secret_from_bitwarden("Vercel Deploy Token")
        if token: return token
    except Exception: pass
    token = _from_credential_manager("VERCEL_TOKEN")
    if token: return token
    token = _from_registry("VERCEL_TOKEN")
    if token: return token
    return os.environ.get("VERCEL_TOKEN", "")

def check_deploy_limit():
    today = str(date.today())
    count = 0
    if os.path.exists(DEPLOY_COUNT_FILE):
        try:
            with open(DEPLOY_COUNT_FILE, 'r') as f:
                data = json.load(f)
            if data.get('date') == today: count = data.get('count', 0)
        except Exception: pass
    count += 1
    if count >= VERCEL_DAILY_LIMIT:
        raise RuntimeError("Daily deploy limit reached")
    with open(DEPLOY_COUNT_FILE, 'w') as f:
        json.dump({'date': today, 'count': count}, f)

def deploy():
    token = get_vercel_token()
    if not token:
        print("ERROR: VERCEL_TOKEN not found in Bitwarden, Credential Manager, Registry, or Environment.")
        print("You can set VERCEL_TOKEN environment variable or deploy via GitHub push.")
        return False

    check_deploy_limit()

    files_to_deploy = [
        'index.html',
        'style.css',
        'app.js',
        'definitions.js',
        'definitions.json',
        'manifest.json',
        'sw.js'
    ]

    files_payload = []
    for fname in files_to_deploy:
        fpath = os.path.join(PROJECT_DIR, fname)
        if os.path.exists(fpath):
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read()
            files_payload.append({
                'file': fname,
                'data': content,
                'encoding': 'utf-8'
            })
            print(f"  + Bundling {fname} ({len(content)} bytes)")

    payload = {
        'name': PROJECT_NAME,
        'files': files_payload,
        'target': 'production',
        'projectSettings': {'framework': None}
    }

    print(f"\nDeploying {len(files_payload)} files to Vercel production ({PROJECT_NAME})...")
    req = urllib.request.Request(
        'https://api.vercel.com/v13/deployments',
        data=json.dumps(payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            deployment_id = data.get('id')
            url = data.get('url')
            alias = data.get('alias', [])
            print(f"\n================ DEPLOYMENT SUCCESS ================")
            print(f"Deployment ID: {deployment_id}")
            print(f"Preview URL:   https://{url}")
            if alias:
                print(f"Production URL: https://{alias[0]}")
            else:
                print(f"Production URL: https://{PROJECT_NAME}.vercel.app")
            print("====================================================")
            return True
    except urllib.error.HTTPError as e:
        err_body = e.read().decode('utf-8')
        print(f"Deployment HTTP Error {e.code}: {err_body}")
        return False
    except Exception as e:
        print(f"Deployment failed: {e}")
        return False

if __name__ == '__main__':
    deploy()
