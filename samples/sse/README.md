# Samples: Server-Sent Events (SSE)

Deploys a minimal Server-Sent Events (SSE) backend and exposes it through Azure API Management (APIM) so you can validate APIM SSE recommendations such as disabling response buffering.

⚙️ **Supported infrastructures**: apim-aca, afd-apim-pe, appgw-apim, appgw-apim-pe

👟 **Expected *Run All* runtime (excl. infrastructure prerequisite): ~6 minutes**

## 🎯 Objectives

1. Deploy a minimal SSE backend (FastAPI) that emits small, periodic events.
1. Expose the backend via APIM using an SSE-optimized policy (`buffer-response="false"`).
1. Compare behavior with a deliberately misconfigured policy (`buffer-response="true"`) to observe buffering.

## 🛩️ Lab Components

- A minimal SSE backend app (FastAPI + Uvicorn) built into a container.
- An APIM backend named `sse-backend` pointing at the deployed backend.
- An APIM API exposing two streaming operations:
  - `/good` - streaming relay (recommended)
  - `/buffered` - response buffering enabled (not recommended for SSE)

## ⚙️ Configuration

1. Decide which of the [Infrastructure Architectures](../../README.md#infrastructure-architectures) you wish to use.
1. If the infrastructure does not yet exist, deploy one of the supported infrastructures.
1. Run the notebook and only modify entries under `USER CONFIGURATION`.

## Notes

- APIM SSE guidance: https://learn.microsoft.com/azure/api-management/how-to-server-sent-events
- `forward-request` buffering behavior: https://learn.microsoft.com/azure/api-management/forward-request-policy
- For SSE, avoid enabling request/response body logging in APIM diagnostics because it can introduce buffering.
