# SAS Agent — Desktop Front-Door for SAS Viya via MCP

**SAS Agent** is a lightweight, secure desktop client that connects directly to a **SAS Viya Model Context Protocol (MCP) Server** over HTTP/HTTPS.

It transforms technical SAS Viya microservices, Model Manager deployments, and Micro Analytic Services (MAS) modules into an intuitive, action-driven desktop interface designed for business teams and analysts.

---

## 🚀 Why This Matters: The Value for SAS Viya Teams

In typical SAS Viya enterprise environments, powerful predictive models, decision workflows, and analytical assets reside in **SAS Model Manager** or **SAS Micro Analytic Service (MAS)**. However:

1. **The Discovery Gap**: MCP servers are primarily designed for AI agent discovery, leaving operational users and business teams without a direct, human-friendly interface to test or run these actions.
2. **The Deployment Bottleneck**: Creating custom business front-ends usually requires extensive frontend development or complex API orchestration.
3. **Enterprise Governance**: IT and compliance require all model executions to be audited, secured, and tied to authentic corporate identities.

### How SAS Agent Solves This:
- **Democratizes Model Access**: Turns any model published to the SAS MCP server into an auto-generated GUI form with live input validation (JSON, text, numbers, booleans).
- **Reusable Across Departments**: Ship the exact same compiled `.exe` to different departments (e.g., Credit Risk, Fraud, Model Creation & Decisioning / MCD). Simply supply a department-specific `config.json`—**zero code changes required**.
- **Out-of-the-Box Viya Governance**: Because calls pass through the Viya MCP gateway using each user's OAuth/Viya token, all scoring events, decisions, and data access remain registered in SAS Viya's native audit, monitoring, and lineage logs.
- **Enterprise HTTPS & Intranet Ready**: Built to handle corporate SSL/TLS inspection, internal self-signed certificates, and custom CA authority bundles.

---

## ✨ Key Features

- **Modern MCP Protocol Support**:
  - Implements **Streamable HTTP** (the modern standard for remote MCP servers) with automatic fallback to **SSE (Server-Sent Events)**.
- **Enterprise HTTPS & Security**:
  - Full TLS/SSL support with configurable certificate verification (`verify_ssl` flag) and custom corporate CA bundles (`ssl_ca_bundle`).
  - Dedicated menu to toggle SSL verification at runtime for test environments.
- **Flexible Authentication Modes**:
  - **OAuth 2.0 PKCE** browser login with a local callback receiver (`http://localhost:8787/callback`).
  - **Client Credentials** grant for automated or machine-to-machine integrations.
  - **Static / Personal Access Tokens (PAT)** via config or environment variables (`SAS_MCP_TOKEN`).
- **Dynamic Action Discovery & Form Builder**:
  - Auto-discovers all tools/models exposed by the SAS MCP Server.
  - Real-time search and filter for quick action lookup.
  - Dynamically builds forms based on JSON Schema properties (strings, integers, floats, booleans, arrays, objects).
  - Scrollable view supporting tools with extensive parameter lists.
- **AI Agent Chat Assistant (Multi-LLM Support)**:
  - Natural language conversational tab powered by your choice of LLM: **Ollama**, **llama.cpp**, **OpenAI**, or **Anthropic Claude**.
  - Uses native **Tool / Function Calling** to reason and execute SAS Viya models autonomously.
  - Real-time tool execution tracking directly inside the chat window.
  - Interactive GUI configuration dialog for instant provider, model, and API key updates.
- **Zero-Install Single Executable**:
  - Bundles cleanly into a standalone `SASAgent.exe` via PyInstaller.

---

## 📂 Project Structure

```text
sas-mcp-http/
│
├── app.py             # Main Tkinter desktop UI (Tabbed: Direct Form + LLM Chat)
├── auth.py            # Authentication layer (OAuth 2.0 PKCE, Client Credentials, Token storage)
├── mcp_client.py      # MCP transport layer (Streamable HTTP, SSE, HTTPS/SSL handling)
├── llm_client.py      # Multi-provider LLM Agent (Ollama, llama.cpp, OpenAI, Claude)
├── config.json        # Application, SAS Viya endpoint, and LLM configuration
├── requirements.txt   # Python dependency specifications
├── build.bat          # Automated setup, virtual environment, and PyInstaller build script
│
├── dist/              # Output directory for standalone binaries
│   ├── SASAgent.exe   # Compiled standalone executable (~27MB)
│   └── config.json    # Configuration file distributed with the executable
└── .venv/             # Local Python virtual environment
```

---

## 🛠️ Quick Start & Build

### Option A: One-Click Build (`build.bat`)
If you are on Windows, simply double-click or run [build.bat](file:///c:/Repositorios/sas-mcp-http/build.bat):

```cmd
build.bat
```

**What `build.bat` does automatically:**
1. Checks for Python (Python 3.11 recommended) and creates `.venv` if missing.
2. Installs and upgrades all required dependencies from [requirements.txt](file:///c:/Repositorios/sas-mcp-http/requirements.txt).
3. Packages the project with PyInstaller (`SASAgent.exe`).
4. Copies [config.json](file:///c:/Repositorios/sas-mcp-http/config.json) into `dist/` ready for distribution.

### Option B: Running from Source
1. **Create and activate a virtual environment**:
   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\activate
   ```
2. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```powershell
   python app.py
   ```

---

## ⚙️ Configuration Reference (`config.json`)

Place `config.json` in the same directory as `SASAgent.exe` (or in `%APPDATA%\SASAgent\config.json`).

```json
{
  "name": "SAS Agent",
  "mcp_server_url": "https://your-sas-viya-host.com/mcp/v1",
  "authorize_url": "https://your-sas-viya-host.com/oauth/authorize",
  "token_url": "https://your-sas-viya-host.com/oauth/token",
  "client_id": "sas-mcp-client",
  "client_secret": "optional - only if confidential client",
  "scope": "openid",
  "redirect_uri": "http://localhost:8787/callback",
  "callback_port": 8787,
  "verify_ssl": true,
  "ssl_ca_bundle": "",
  "transport": "auto",
  "token": "",
  "llm": {
    "provider": "openai",
    "base_url": "https://api.openai.com/v1",
    "model": "gpt-4o-mini",
    "api_key": "",
    "api_keys": {
      "openai": "",
      "claude": "",
      "ollama": "",
      "llamacpp": ""
    },
    "system_prompt": "You are an intelligent SAS Viya assistant. You have access to tools and models hosted on the SAS MCP Server. Use them when the user asks questions or requests actions."
  }
}
```

---

### Detailed Variable Explanations

#### 1. General Application Settings
- **`name`** *(string)*:
  - **Description**: The window title displayed at the top of the desktop application.
  - **Use Case**: Set this to identify specific departments or environments (e.g., `"MCD Credit Risk Agent"`, `"Fraud Detection SAS Agent"`).

#### 2. SAS Viya & MCP Endpoint Settings
- **`mcp_server_url`** *(string)*:
  - **Description**: The full URL pointing to the remote SAS Viya MCP server. Supports both `http://` and secure `https://`.
  - **Example**: `"https://viya.mycompany.com/mcp/v1"`.
- **`transport`** *(string: `"auto"` | `"streamable_http"` | `"sse"`)*:
  - **Description**: The network transport protocol used to communicate with the MCP server:
    - `"auto"` (Default): Attempts modern MCP **Streamable HTTP** first; if the server does not support it or responds with SSE headers/endpoints, automatically falls back to **SSE (Server-Sent Events)**.
    - `"streamable_http"`: Enforces the newer MCP Streamable HTTP transport exclusively.
    - `"sse"`: Enforces the legacy Server-Sent Events transport.

#### 3. Security & HTTPS / TLS Settings
- **`verify_ssl`** *(boolean: `true` | `false`)*:
  - **Description**: Controls whether SSL/TLS certificates must be strictly verified against trusted Certificate Authorities (CAs).
  - **Options**:
    - `true` (Default): Secure production mode. Validates the SAS server's certificate against known CA authorities.
    - `false`: Disables certificate verification. Recommended **only** for internal testing environments that use self-signed certificates or corporate SSL inspection proxies that break standard certificate validation.
- **`ssl_ca_bundle`** *(string)*:
  - **Description**: File path to a custom corporate root CA certificate bundle (`.pem` or `.crt`).
  - **Use Case**: If your company uses an internal Root CA, provide the path here (e.g., `"C:/Certs/corporate-root-ca.pem"`). When set, `verify_ssl` will validate using this bundle instead of standard public roots.

#### 4. Authentication & OAuth 2.0 Settings
- **`authorize_url`** *(string)*:
  - **Description**: The SAS Viya OAuth authorization endpoint. Used during the browser login step of the OAuth 2.0 PKCE flow.
  - **Example**: `"https://viya.mycompany.com/SASLogon/oauth/authorize"`.
- **`token_url`** *(string)*:
  - **Description**: The SAS Viya OAuth token exchange endpoint. Exchanges authorization codes for access tokens over HTTPS.
  - **Example**: `"https://viya.mycompany.com/SASLogon/oauth/token"`.
- **`client_id`** *(string)*:
  - **Description**: The OAuth client identifier registered in SAS Viya for this application.
- **`client_secret`** *(string)*:
  - **Description**: The OAuth client secret. Optional. Leave empty (`""`) if the registered OAuth client is configured as a public PKCE native client.
- **`scope`** *(string)*:
  - **Description**: OAuth permissions/scopes requested by the token.
  - **Example**: `"openid"` or specific SAS Viya scopes like `"openid uaa.user mas.execute"`.
- **`redirect_uri`** *(string)*:
  - **Description**: The loopback redirect URI registered in the SAS Viya OAuth client for the local login callback.
  - **Default**: `"http://localhost:8787/callback"`.
- **`callback_port`** *(integer)*:
  - **Description**: The local TCP port where the temporary loopback HTTP server listens for the OAuth authorization code. Must match the port in `redirect_uri`.
  - **Default**: `8787`.
- **`token`** *(string)*:
  - **Description**: Optional pre-issued static token or Personal Access Token (PAT).
  - **Use Case**: If populated, the app uses this Bearer token directly and completely skips the browser login prompt. You can also supply it via the `SAS_MCP_TOKEN` environment variable.

#### 5. AI Agent & LLM Configuration (`llm`)
- **`llm.provider`** *(string: `"openai"` | `"claude"` | `"ollama"` | `"llamacpp"`)*:
  - **Description**: The active AI model backend used for conversational chat and autonomous tool calling.
  - **Options**:
    - `"openai"` (Default): OpenAI cloud models (`gpt-4o`, `gpt-4o-mini`).
    - `"claude"`: Anthropic Claude cloud models (`claude-3-5-sonnet`, `claude-3-5-haiku`).
    - `"ollama"`: Private local models running on your machine via Ollama.
    - `"llamacpp"`: Private local models running via llama.cpp.
- **`llm.base_url`** *(string)*:
  - **Description**: The API base endpoint for the chosen LLM service.
  - **Defaults**:
    - OpenAI: `"https://api.openai.com/v1"`
    - Claude: `"https://api.anthropic.com/v1"`
    - Ollama: `"http://localhost:11434/v1"`
    - llama.cpp: `"http://localhost:8080/v1"`
- **`llm.model`** *(string)*:
  - **Description**: The specific model identifier to load and prompt.
  - **Examples**: `"gpt-4o-mini"`, `"gpt-4o"`, `"claude-3-5-sonnet-20241022"`, `"llama3.1"`, `"qwen2.5"`.
- **`llm.api_key`** *(string)*:
  - **Description**: The currently active API key. Optional for local backends (Ollama, llama.cpp), required for cloud providers (OpenAI, Claude).
- **`llm.api_keys`** *(object)*:
  - **Description**: Dedicated per-provider dictionary that stores keys for each service (`openai`, `claude`, etc.).
  - **Benefit**: Allows you to switch between OpenAI and Claude from the UI without losing previously entered keys.
- **`llm.system_prompt`** *(string)*:
  - **Description**: The foundational instructions provided to the LLM defining its role as an analytical SAS Viya assistant with MCP tool-use capabilities.

---

## 📋 SAS Viya Admin Checklist

Before rolling this tool out to business users, verify the following with your SAS Viya administrator:

- [ ] **Endpoint URL**: Confirm whether the MCP server is hosted at `/mcp/v1` or another path, and verify that HTTP POST/GET or SSE is allowed through internal firewalls/reverse proxies.
- [ ] **OAuth Client Registration**:
  - Client ID configured with `authorization_code` grant and `code_challenge_method: S256` (PKCE).
  - Redirect URI configured: `http://localhost:8787/callback` (or `http://127.0.0.1:8787/callback`).
  - Alternatively: Provide a personal access token (PAT) for initial pilots.
- [ ] **User Scopes & Permissions**: Ensure the resulting OAuth token carries permission for the target SAS Micro Analytic Services (MAS) modules or Model Manager execution scopes.
- [ ] **TLS / Certificates**: If the Viya cluster uses an internal enterprise CA, obtain the root certificate bundle and set `ssl_ca_bundle` in `config.json`.

---

## 🖥️ How to Use the Application

### 1. Launching
Double-click `dist\SASAgent.exe`. The application reads `config.json` located next to it.

### 2. Authentication
- If no token is found, a prompt will ask if you want to log in through your browser.
- Click **Yes**: Your default browser opens to the SAS Viya login portal. Once you enter your credentials, Viya redirects to `localhost:8787/callback`, and the app stores your session token locally in `%APPDATA%\SASAgent\token.json`.
- Alternatively, use **Conexión > Ver / Editar Token...** to paste a pre-generated Bearer token.

### 3. Exploring Tools & Actions
- The left-hand panel lists all available actions (scoring models, data routines, analytical queries) exposed by the MCP server.
- Use the **Buscar** (Search) box to filter tools by name or description.

### 4. Filling Parameters & Executing
- Selecting an action renders its parameter form on the right.
- Required fields are highlighted with an asterisk (`*`).
- Text, numeric, boolean flags, and complex JSON structures are validated on input.
- Click **▶ Ejecutar Acción (Run)** to trigger the model in SAS Viya.

### 5. Reviewing Results
- Real-time output appears in the **Resultado / Logs** console.
- Use the **Copiar** button to copy the output to the clipboard or **Limpiar** to reset the console.

---

## 🏢 Distributing to Department Teams

To deploy to end-users without technical setup:

1. Run `build.bat` once on an administrative/developer machine.
2. Navigate to the `dist\` folder.
3. Edit `dist\config.json` with the target department's SAS Viya endpoint and credentials.
4. Distribute the `dist\` folder (or package it into a `.zip`) to users:
   ```text
   Department_Package/
   ├── SASAgent.exe
   └── config.json
   ```
Users only need to double-click `SASAgent.exe`—no Python installation or console knowledge required.
