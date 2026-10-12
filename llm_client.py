import os
import json
import logging
import requests
from mcp_client import call_tool, extract_text, run_async

logger = logging.getLogger("llm_client")

LLM_PRESETS = {
    "openai": {
        "name": "OpenAI",
        "label": "OpenAI (Cloud)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": ["gpt-4o-mini", "gpt-4o", "o1-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
        "requires_key": True,
        "env_key": "OPENAI_API_KEY",
        "doc": "Requires an OpenAI API Key (platform.openai.com)",
    },
    "claude": {
        "name": "Claude",
        "label": "Anthropic Claude (Cloud)",
        "base_url": "https://api.anthropic.com/v1",
        "default_model": "claude-3-5-sonnet-20241022",
        "models": ["claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022", "claude-3-opus-20240229"],
        "requires_key": True,
        "env_key": "ANTHROPIC_API_KEY",
        "doc": "Requires an Anthropic API Key (console.anthropic.com)",
    },
    "ollama": {
        "name": "Ollama",
        "label": "Ollama (Local)",
        "base_url": "http://localhost:11434/v1",
        "default_model": "llama3.1",
        "models": ["llama3.1", "llama3.2", "qwen2.5", "mistral", "phi3"],
        "requires_key": False,
        "env_key": "",
        "doc": "Runs models locally on your machine without cloud dependencies.",
    },
    "llamacpp": {
        "name": "llama.cpp",
        "label": "llama.cpp (Local GGUF)",
        "base_url": "http://localhost:8080/v1",
        "default_model": "default",
        "models": ["default"],
        "requires_key": False,
        "env_key": "",
        "doc": "Local llama.cpp server with OpenAI-compatible API.",
    },
}


def mcp_to_openai_tools(mcp_tools):
    """Convert MCP tools into OpenAI Function Calling format."""
    openai_tools = []
    for t in mcp_tools or []:
        name = getattr(t, "name", "")
        desc = getattr(t, "description", "") or ""
        schema = getattr(t, "inputSchema", {}) or {}
        if not isinstance(schema, dict) or not schema:
            schema = {"type": "object", "properties": {}}

        openai_tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": desc,
                "parameters": schema,
            }
        })
    return openai_tools


def mcp_to_anthropic_tools(mcp_tools):
    """Convert MCP tools into Anthropic Claude tool format."""
    anthropic_tools = []
    for t in mcp_tools or []:
        name = getattr(t, "name", "")
        desc = getattr(t, "description", "") or ""
        schema = getattr(t, "inputSchema", {}) or {}
        if not isinstance(schema, dict) or not schema:
            schema = {"type": "object", "properties": {}}

        anthropic_tools.append({
            "name": name,
            "description": desc,
            "input_schema": schema,
        })
    return anthropic_tools


class LLMAgent:
    def __init__(self, cfg):
        self.cfg = cfg
        self.llm_cfg = cfg.get("llm", {})
        self.provider = self.llm_cfg.get("provider", "openai").lower()
        if self.provider not in LLM_PRESETS:
            self.provider = "openai"

        preset = LLM_PRESETS.get(self.provider, LLM_PRESETS["openai"])

        self.base_url = self.llm_cfg.get("base_url") or preset["base_url"]
        self.base_url = self.base_url.rstrip("/")

        self.model = self.llm_cfg.get("model") or preset["default_model"]

        # Resolve API key with fallback to per-provider keys and env vars
        keys_dict = self.llm_cfg.get("api_keys", {})
        env_var = preset.get("env_key")
        env_val = os.environ.get(env_var, "") if env_var else ""

        self.api_key = (
            keys_dict.get(self.provider)
            or self.llm_cfg.get("api_key", "")
            or env_val
        ).strip()

        self.system_prompt = self.llm_cfg.get(
            "system_prompt",
            "You are an expert AI assistant connected to SAS Viya via Model Context Protocol (MCP). "
            "You have direct access to analytical tools and models. "
            "Whenever the user asks a question that requires running a model, calculating scores, or fetching data, "
            "use the available tools and clearly explain the results."
        )
        self.messages = []
        self._init_history()

    def _init_history(self):
        self.messages = []
        if self.provider in ("openai", "ollama", "llamacpp"):
            self.messages.append({"role": "system", "content": self.system_prompt})

    def reset_chat(self):
        self._init_history()

    def chat_step(self, user_text, mcp_tools, sas_url, sas_token, log_callback=None):
        """
        Execute one conversational agent step with automatic tool execution loop.
        log_callback(msg: str) is invoked when tools are executed or status changes.
        Returns final text reply from the LLM.
        """
        preset = LLM_PRESETS.get(self.provider, {})
        if preset.get("requires_key") and not self.api_key:
            err = (
                f"API Key is not configured for {self.provider.upper()}.\n\n"
                f"Please open '⚙ Configure API Keys' from the top bar or menu to enter your API Key."
            )
            if log_callback:
                log_callback(err)
            return err

        if self.provider == "claude":
            return self._chat_step_claude(user_text, mcp_tools, sas_url, sas_token, log_callback)
        else:
            return self._chat_step_openai_compat(user_text, mcp_tools, sas_url, sas_token, log_callback)

    # -------------------------------------------------------------
    # OpenAI & OpenAI-compatible (Ollama, llama.cpp, vLLM, LM Studio)
    # -------------------------------------------------------------
    def _chat_step_openai_compat(self, user_text, mcp_tools, sas_url, sas_token, log_callback):
        self.messages.append({"role": "user", "content": user_text})
        tools = mcp_to_openai_tools(mcp_tools)

        endpoint = f"{self.base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        elif self.provider == "ollama":
            headers["Authorization"] = "Bearer ollama"

        max_turns = 6
        for turn in range(max_turns):
            payload = {
                "model": self.model,
                "messages": self.messages,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            try:
                resp = requests.post(endpoint, headers=headers, json=payload, timeout=90)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                err_msg = f"Error communicating with {self.provider} ({endpoint}):\n{e}"
                if log_callback:
                    log_callback(err_msg)
                return err_msg

            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            self.messages.append(msg)

            tool_calls = msg.get("tool_calls")
            if not tool_calls:
                return msg.get("content", "")

            # Execute each requested tool in SAS Viya
            for tc in tool_calls:
                func = tc.get("function", {})
                tool_name = func.get("name", "")
                raw_args = func.get("arguments", "{}")
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except Exception:
                    args = {}

                if log_callback:
                    log_callback(f"⚙️ Calling SAS Viya: {tool_name}({json.dumps(args, ensure_ascii=False)})")

                try:
                    res = run_async(call_tool, sas_url, sas_token, tool_name, args, self.cfg)
                    output_str = extract_text(res)
                except Exception as ex:
                    output_str = f"Error executing tool '{tool_name}': {str(ex)}"

                if log_callback:
                    log_callback(f"✓ SAS Viya responded successfully ({len(output_str)} characters)")

                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tc.get("id", f"call_{tool_name}"),
                    "name": tool_name,
                    "content": output_str,
                })

        return "Exceeded maximum consecutive SAS Viya tool call limit."

    # -------------------------------------------------------------
    # Anthropic Claude Native API (/v1/messages)
    # -------------------------------------------------------------
    def _chat_step_claude(self, user_text, mcp_tools, sas_url, sas_token, log_callback):
        self.messages.append({"role": "user", "content": user_text})
        tools = mcp_to_anthropic_tools(mcp_tools)

        endpoint = f"{self.base_url}/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

        max_turns = 6
        for turn in range(max_turns):
            payload = {
                "model": self.model,
                "max_tokens": 4096,
                "system": self.system_prompt,
                "messages": self.messages,
            }
            if tools:
                payload["tools"] = tools

            try:
                resp = requests.post(endpoint, headers=headers, json=payload, timeout=90)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                err_msg = f"Error communicating with Claude ({endpoint}):\n{e}"
                if log_callback:
                    log_callback(err_msg)
                return err_msg

            content_blocks = data.get("content", [])
            self.messages.append({"role": "assistant", "content": content_blocks})

            tool_uses = [b for b in content_blocks if b.get("type") == "tool_use"]
            if not tool_uses:
                text_parts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                return "\n".join(text_parts)

            for tu in tool_uses:
                tool_name = tu.get("name", "")
                args = tu.get("input", {})
                tool_id = tu.get("id", "")

                if log_callback:
                    log_callback(f"⚙️ Calling SAS Viya: {tool_name}({json.dumps(args, ensure_ascii=False)})")

                try:
                    res = run_async(call_tool, sas_url, sas_token, tool_name, args, self.cfg)
                    output_str = extract_text(res)
                except Exception as ex:
                    output_str = f"Error executing tool '{tool_name}': {str(ex)}"

                if log_callback:
                    log_callback(f"✓ SAS Viya responded successfully ({len(output_str)} characters)")

                self.messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_id,
                        "content": output_str,
                    }]
                })

        return "Exceeded maximum consecutive SAS Viya tool call limit."
