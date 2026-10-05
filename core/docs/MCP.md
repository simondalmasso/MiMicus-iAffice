# MCP and ChatGPT setup

MiMicus uses the official Python MCP SDK v2.0.0 and serves Streamable HTTP at `/mcp`.

```bash
mimicus serve --profile offline --host 127.0.0.1 --port 8765
```

The MCP transport is intentionally loopback-only because the server exposes mutating tools and does not yet implement transport authentication. Binding to non-loopback addresses fails closed. Use an authenticated/approved tunnel or gateway for any remote exposure.

The exact-head E2E launches this server in a subprocess, connects with the official MCP `Client`, calls `run_mimicus`, then calls `get_mimicus_run` and verifies the persisted ledger replay. `OPENAI_API_KEY` is removed from that subprocess environment.

## ChatGPT

As of 2026-08-17, OpenAI documents custom MCP apps through ChatGPT developer mode. Current OpenAI guidance says ChatGPT connects to **remote** MCP servers, not a bare localhost endpoint; a private/local service needs an approved remote exposure mechanism such as Secure MCP Tunnel. Full MCP capabilities are plan/workspace dependent and the UI can change during beta.

Current official references:

- https://help.openai.com/en/articles/12584461-developer-mode-and-full-mcp-connectors-in-chatgpt
- https://help.openai.com/en/articles/11487775-connectors-in

For eligible workspaces, enable developer mode in the workspace/user Apps settings described by OpenAI, create a custom app, and supply the remote Streamable HTTP endpoint ending in `/mcp`. Review permissions before publishing. Refresh the app after changing exposed tools because server updates are not automatically enabled.

The local process-level test is protocol compatibility evidence; it is not a claim that `127.0.0.1:8765` is directly reachable by chatgpt.com.
