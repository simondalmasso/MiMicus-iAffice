#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

BASE=os.environ.get("IAFFICE_BASE_URL","https://agent-os.simondalmasso44.workers.dev").rstrip("/")
EXPECTED_SHA=os.environ.get("ARIA_HEAD_SHA","")
TIMEOUT=15

if not EXPECTED_SHA:
    raise SystemExit("ARIA_HEAD_SHA_REQUIRED")

def get(path:str):
    url=BASE+path
    req=urllib.request.Request(url,headers={"user-agent":"iaffice-live-acceptance/1.0","accept":"*/*"})
    try:
        with urllib.request.urlopen(req,timeout=TIMEOUT) as res:
            body=res.read(2_000_000)
            return res.status,{k.lower():v for k,v in res.headers.items()},body
    except urllib.error.HTTPError as exc:
        body=exc.read(200_000)
        raise RuntimeError(f"HTTP_{exc.code}:{path}:{body[:300]!r}") from exc

checks=[]

status,headers,body=get("/api/health")
health=json.loads(body)
assert status==200,(status,health)
assert health.get("ok") is True,health
assert health.get("service")=="iAffice",health
assert health.get("worker")=="agent-os",health
assert health.get("sha")==EXPECTED_SHA,(health.get("sha"),EXPECTED_SHA)
assert health.get("costPolicy")=="ZERO_SPEND_HARD_LOCK",health
assert health.get("agentWriteCredentials")==0,health
assert health.get("modelProviderCredentials")==0,health
checks.append("health-exact-head")

status,headers,body=get("/")
text=body.decode("utf-8","replace")
assert status==200,status
assert len(body)>1000,len(body)
assert "iAffice" in text,text[:200]
assert "Revenue" in text,text[:500]
assert headers.get("content-type","").lower().startswith("text/html"),headers
for h in ("content-security-policy","x-content-type-options","referrer-policy","x-frame-options","permissions-policy","strict-transport-security"):
    assert headers.get(h),f"MISSING_SECURITY_HEADER:{h}"
checks.append("cockpit-html-security")

for path in (
    "/api/sniper/global",
    "/api/sniper/operations",
    "/api/sniper/discovery/sources",
    "/api/sniper/demos",
    "/api/sniper/executors",
    "/api/sniper/telemetry",
    "/api/compute/budget",
):
    status,headers,body=get(path)
    assert status==200,(path,status,body[:300])
    json.loads(body)
    assert headers.get("x-content-type-options")=="nosniff",(path,headers)
    checks.append(path)

result={
    "taxonomy":"LIVE_ACCEPTANCE",
    "order":"ORDER-004",
    "base":BASE,
    "head_sha":EXPECTED_SHA,
    "checks":checks,
    "pass":True,
}
print(json.dumps(result,indent=2))
