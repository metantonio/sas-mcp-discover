import os
import sys
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from auth import load_config, login, load_token, clear_token, save_token, get_config_path
from mcp_client import list_tools, call_tool, run_async, extract_text
from llm_client import LLMAgent, LLM_PRESETS


class App:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.root.title(f"{self.cfg.get('name', 'SAS Agent')} - [MCP + LLM Chat Enabled]")
        self.root.geometry("1180x780")
        self.root.minsize(920, 600)

        self.tools = []
        self._selected_tool = None
        self._fields = []
        self.llm_agent = LLMAgent(self.cfg)

        self._build_menu()
        self._build_ui()
        self._load_tools_async()

    # -------------------------------------------------------------
    # Menu Bar
    # -------------------------------------------------------------
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Reload MCP Tools", command=self._load_tools_async)
        file_menu.add_command(label="View / Edit Token...", command=self._edit_token)
        file_menu.add_command(label="Re-authenticate (OAuth Viya)", command=self._force_relogin)
        file_menu.add_separator()
        file_menu.add_command(label="View Configuration Path", command=self._show_config_info)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="SAS Connection", menu=file_menu)

        llm_menu = tk.Menu(menubar, tearoff=0)
        llm_menu.add_command(label="Configure LLM Provider & API Keys...", command=self._configure_llm_dialog)
        llm_menu.add_separator()
        llm_menu.add_command(label="Use OpenAI (gpt-4o-mini)", command=lambda: self._quick_switch_llm("openai", "gpt-4o-mini"))
        llm_menu.add_command(label="Use Anthropic Claude (claude-3-5-sonnet)", command=lambda: self._quick_switch_llm("claude", "claude-3-5-sonnet-20241022"))
        llm_menu.add_command(label="Use Local Ollama (llama3.1)", command=lambda: self._quick_switch_llm("ollama", "llama3.1"))
        llm_menu.add_separator()
        llm_menu.add_command(label="Reset Chat Conversation", command=self._reset_chat)
        menubar.add_cascade(label="LLM Agent", menu=llm_menu)

        ssl_menu = tk.Menu(menubar, tearoff=0)
        self.ssl_var = tk.BooleanVar(value=bool(self.cfg.get("verify_ssl", True)))
        ssl_menu.add_checkbutton(label="Verify SSL / HTTPS", variable=self.ssl_var, command=self._toggle_ssl)
        menubar.add_cascade(label="HTTPS Security", menu=ssl_menu)

        self.root.config(menu=menubar)

    # -------------------------------------------------------------
    # Main UI Layout
    # -------------------------------------------------------------
    def _build_ui(self):
        # Top toolbar
        toolbar = ttk.Frame(self.root, padding=6)
        toolbar.pack(fill="x", side="top")

        server_label = f"SAS Viya: {self.cfg.get('mcp_server_url', 'Not configured')}"
        self.lbl_server = ttk.Label(toolbar, text=server_label, font=("Segoe UI", 9, "bold"))
        self.lbl_server.pack(side="left", padx=4)

        provider = self.cfg.get("llm", {}).get("provider", "openai")
        model = self.cfg.get("llm", {}).get("model", "gpt-4o-mini")
        self.lbl_llm_info = ttk.Label(toolbar, text=f"|  Active LLM: {provider.upper()} ({model})", font=("Segoe UI", 9))
        self.lbl_llm_info.pack(side="left", padx=8)

        self.lbl_status = ttk.Label(toolbar, text="Initializing...", foreground="#666666")
        self.lbl_status.pack(side="right", padx=6)

        self.btn_refresh = ttk.Button(toolbar, text="↻ Refresh MCP", command=self._load_tools_async)
        self.btn_refresh.pack(side="right", padx=4)

        # Tabbed interface
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=(2, 6))

        # Tab 1: Direct Form Runner
        self.tab_form = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_form, text="  ⚡ Direct Form  ")
        self._build_form_tab()

        # Tab 2: LLM Chat Assistant
        self.tab_chat = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_chat, text="  💬 LLM Agent Chat  ")
        self._build_chat_tab()

    # -------------------------------------------------------------
    # Tab 1: Direct Form
    # -------------------------------------------------------------
    def _build_form_tab(self):
        panes = ttk.PanedWindow(self.tab_form, orient=tk.HORIZONTAL)
        panes.pack(fill="both", expand=True, padx=4, pady=4)

        left_frame = ttk.Frame(panes, width=320, padding=4)
        panes.add(left_frame, weight=0)

        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(filter_frame, text="Search:").pack(side="left", padx=(0, 4))
        self.filter_var = tk.StringVar()
        self.filter_var.trace_add("write", lambda *_: self._filter_tools())
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var)
        self.filter_entry.pack(fill="x", expand=True)

        tv_frame = ttk.Frame(left_frame)
        tv_frame.pack(fill="both", expand=True)

        self.tv = ttk.Treeview(tv_frame, columns=("desc",), show="tree headings", selectmode="browse")
        self.tv.heading("#0", text="Tool / Action")
        self.tv.column("#0", width=190, stretch=True)
        self.tv.heading("desc", text="Description")
        self.tv.column("desc", width=120, stretch=True)

        tv_scroll = ttk.Scrollbar(tv_frame, orient="vertical", command=self.tv.yview)
        self.tv.configure(yscrollcommand=tv_scroll.set)
        self.tv.pack(side="left", fill="both", expand=True)
        tv_scroll.pack(side="right", fill="y")
        self.tv.bind("<<TreeviewSelect>>", lambda _: self._on_tool_select())

        right_frame = ttk.Frame(panes, padding=4)
        panes.add(right_frame, weight=1)

        form_container = ttk.LabelFrame(right_frame, text="Input Parameters", padding=6)
        form_container.pack(fill="both", expand=True, pady=(0, 4))

        self.canvas = tk.Canvas(form_container, highlightthickness=0)
        self.form_scroll = ttk.Scrollbar(form_container, orient="vertical", command=self.canvas.yview)
        self.form_inner = ttk.Frame(self.canvas)

        self.form_inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas_window = self.canvas.create_window((0, 0), window=self.form_inner, anchor="nw")
        self.canvas.configure(yscrollcommand=self.form_scroll.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.form_scroll.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        btn_bar = ttk.Frame(right_frame, padding=(0, 4))
        btn_bar.pack(fill="x")

        self.btn_run = ttk.Button(btn_bar, text="▶ Execute Action (Run)", command=self._run_tool, state="disabled")
        self.btn_run.pack(side="left", fill="x", expand=True, padx=(0, 4))

        self.progress = ttk.Progressbar(btn_bar, mode="indeterminate", length=120)

        out_frame = ttk.LabelFrame(right_frame, text="Output / Logs", padding=6)
        out_frame.pack(fill="both", expand=True, pady=(4, 0))

        out_tools = ttk.Frame(out_frame)
        out_tools.pack(fill="x", pady=(0, 4))
        ttk.Button(out_tools, text="Clear", command=self._clear_output).pack(side="right", padx=2)
        ttk.Button(out_tools, text="Copy", command=self._copy_output).pack(side="right", padx=2)

        out_scroll = ttk.Scrollbar(out_frame, orient="vertical")
        self.out_text = tk.Text(out_frame, wrap="word", state="disabled", font=("Consolas", 10), yscrollcommand=out_scroll.set)
        out_scroll.config(command=self.out_text.yview)
        self.out_text.pack(side="left", fill="both", expand=True)
        out_scroll.pack(side="right", fill="y")

    # -------------------------------------------------------------
    # Tab 2: LLM Chat Assistant
    # -------------------------------------------------------------
    def _build_chat_tab(self):
        # Chat control bar with provider / model dropdowns
        chat_top = ttk.LabelFrame(self.tab_chat, text="Quick Agent Configuration", padding=6)
        chat_top.pack(fill="x", padx=6, pady=(4, 2))

        # Provider quick-selector
        ttk.Label(chat_top, text="Provider:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(4, 2))
        
        self.chat_provider_var = tk.StringVar(value=self.cfg.get("llm", {}).get("provider", "openai"))
        provider_options = [
            ("openai", "OpenAI (Default: GPT-4o / mini)"),
            ("claude", "Anthropic Claude (Default: 3.5 Sonnet / Haiku)"),
            ("ollama", "Ollama (Local / Private)"),
            ("llamacpp", "llama.cpp (Local GGUF)"),
        ]
        self.chat_provider_combo = ttk.Combobox(
            chat_top,
            textvariable=self.chat_provider_var,
            values=[k for k, _ in provider_options],
            state="readonly",
            width=10
        )
        self.chat_provider_combo.pack(side="left", padx=4)

        # Model quick-selector
        ttk.Label(chat_top, text="Model:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(8, 2))
        self.chat_model_var = tk.StringVar(value=self.cfg.get("llm", {}).get("model", "gpt-4o-mini"))
        self.chat_model_combo = ttk.Combobox(chat_top, textvariable=self.chat_model_var, width=24)
        self.chat_model_combo.pack(side="left", padx=4)

        # Populate model choices for current provider
        self._update_model_choices(self.chat_provider_var.get())

        self.chat_provider_combo.bind("<<ComboboxSelected>>", self._on_chat_provider_changed)
        self.chat_model_combo.bind("<<ComboboxSelected>>", self._on_chat_model_changed)
        self.chat_model_combo.bind("<Return>", lambda _: self._on_chat_model_changed())

        ttk.Button(chat_top, text="⚙ Configure API Keys", command=self._configure_llm_dialog).pack(side="right", padx=4)
        ttk.Button(chat_top, text="🗑 Reset Chat", command=self._reset_chat).pack(side="right", padx=2)

        # Chat display transcript
        chat_frame = ttk.Frame(self.tab_chat, padding=6)
        chat_frame.pack(fill="both", expand=True)

        chat_scroll = ttk.Scrollbar(chat_frame, orient="vertical")
        self.chat_display = tk.Text(chat_frame, wrap="word", font=("Segoe UI", 10), yscrollcommand=chat_scroll.set, state="disabled")
        chat_scroll.config(command=self.chat_display.yview)
        self.chat_display.pack(side="left", fill="both", expand=True)
        chat_scroll.pack(side="right", fill="y")

        self.chat_display.tag_config("user", foreground="#0044aa", font=("Segoe UI", 10, "bold"))
        self.chat_display.tag_config("assistant", foreground="#111111", font=("Segoe UI", 10))
        self.chat_display.tag_config("tool_call", foreground="#885500", font=("Consolas", 9, "italic"))
        self.chat_display.tag_config("system_msg", foreground="#666666", font=("Segoe UI", 9, "italic"))

        # Input area
        input_frame = ttk.Frame(self.tab_chat, padding=6)
        input_frame.pack(fill="x", side="bottom")

        self.chat_input = tk.Text(input_frame, height=3, font=("Segoe UI", 10), wrap="word")
        self.chat_input.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.chat_input.bind("<Return>", self._on_chat_enter)

        btn_box = ttk.Frame(input_frame)
        btn_box.pack(side="right", fill="y")

        self.btn_send = ttk.Button(btn_box, text="Send 💬", command=self._send_chat_message)
        self.btn_send.pack(fill="both", expand=True)

        self.chat_progress = ttk.Progressbar(self.tab_chat, mode="indeterminate")

    def _update_model_choices(self, provider):
        preset = LLM_PRESETS.get(provider, LLM_PRESETS["openai"])
        models = preset.get("models", [])
        self.chat_model_combo["values"] = models
        if self.chat_model_var.get() not in models:
            self.chat_model_var.set(preset.get("default_model", ""))

    def _on_chat_provider_changed(self, event=None):
        provider = self.chat_provider_var.get()
        preset = LLM_PRESETS.get(provider, LLM_PRESETS["openai"])
        
        self.cfg.setdefault("llm", {})
        self.cfg["llm"]["provider"] = provider
        self.cfg["llm"]["base_url"] = preset["base_url"]
        self.cfg["llm"]["model"] = preset["default_model"]
        self.chat_model_var.set(preset["default_model"])
        self._update_model_choices(provider)

        self._apply_llm_config()

        # If switching to cloud provider without key, prompt user
        if preset.get("requires_key"):
            key = self.llm_agent.api_key
            if not key:
                resp = messagebox.askyesno(
                    f"API Key for {preset['name']}",
                    f"You have selected {preset['name']}, but no API Key is saved.\n\n"
                    "Would you like to enter your API Key now?"
                )
                if resp:
                    self._configure_llm_dialog(preselect_provider=provider)

    def _on_chat_model_changed(self, event=None):
        model = self.chat_model_var.get().strip()
        if model:
            self.cfg.setdefault("llm", {})["model"] = model
            self._apply_llm_config()

    def _quick_switch_llm(self, provider, model):
        self.chat_provider_var.set(provider)
        self.chat_model_var.set(model)
        self._update_model_choices(provider)
        
        preset = LLM_PRESETS.get(provider, LLM_PRESETS["openai"])
        self.cfg.setdefault("llm", {})
        self.cfg["llm"]["provider"] = provider
        self.cfg["llm"]["base_url"] = preset["base_url"]
        self.cfg["llm"]["model"] = model
        self._apply_llm_config()

        self._append_chat(
            None,
            f"Switched to {provider.upper()} ({model}). Ready to query SAS Viya via MCP.",
            "system_msg"
        )

    def _apply_llm_config(self):
        self.llm_agent = LLMAgent(self.cfg)
        prov = self.cfg.get("llm", {}).get("provider", "openai")
        mod = self.cfg.get("llm", {}).get("model", "gpt-4o-mini")
        self.lbl_llm_info.config(text=f"|  Active LLM: {prov.upper()} ({mod})")
        
        # Persist to config.json
        try:
            cfg_path = get_config_path()
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, indent=2)
        except Exception as e:
            print(f"Notice: Could not write updated config.json: {e}", file=sys.stderr)

    def _append_chat(self, speaker, text, tag):
        def _add():
            self.chat_display.configure(state="normal")
            if speaker:
                self.chat_display.insert("end", f"{speaker}:\n", tag)
            self.chat_display.insert("end", f"{text}\n\n", tag)
            self.chat_display.see("end")
            self.chat_display.configure(state="disabled")
        self.root.after(0, _add)

    def _reset_chat(self):
        self.llm_agent.reset_chat()
        self.chat_display.configure(state="normal")
        self.chat_display.delete("1.0", "end")
        self.chat_display.configure(state="disabled")
        prov = self.cfg.get("llm", {}).get("provider", "openai").upper()
        mod = self.cfg.get("llm", {}).get("model", "gpt-4o-mini")
        self._append_chat(
            None,
            f"Conversation reset with {prov} ({mod}). What SAS Viya model or action would you like to evaluate?",
            "system_msg"
        )

    def _on_chat_enter(self, event):
        if not event.state & 0x0001:  # Shift not pressed
            self._send_chat_message()
            return "break"

    def _send_chat_message(self):
        user_msg = self.chat_input.get("1.0", "end-1c").strip()
        if not user_msg:
            return

        self.chat_input.delete("1.0", "end")
        self._append_chat("You", user_msg, "user")

        self.btn_send.configure(state="disabled")
        self.chat_progress.pack(fill="x", side="bottom", padx=6, pady=2)
        self.chat_progress.start(10)
        prov = self.cfg.get("llm", {}).get("provider", "openai").upper()
        self.set_status(f"Agent ({prov}) is reasoning...", "blue")

        def worker():
            try:
                tok = self._get_token_flow()
                url = self.cfg.get("mcp_server_url", "")

                def log_cb(msg):
                    self._append_chat(None, msg, "tool_call")

                response = self.llm_agent.chat_step(
                    user_text=user_msg,
                    mcp_tools=self.tools,
                    sas_url=url,
                    sas_token=tok,
                    log_callback=log_cb
                )
                self._append_chat("SAS Assistant", response, "assistant")
                self.set_status("Response generated", "#007700")
            except Exception as e:
                err = f"Agent call error: {str(e)}"
                self._append_chat("Error", err, "system_msg")
                self.set_status("Agent Error", "red")
            finally:
                def cleanup():
                    self.chat_progress.stop()
                    self.chat_progress.pack_forget()
                    self.btn_send.configure(state="normal")
                self.root.after(0, cleanup)

        threading.Thread(target=worker, daemon=True).start()

    # -------------------------------------------------------------
    # LLM Configuration Dialog
    # -------------------------------------------------------------
    def _configure_llm_dialog(self, preselect_provider=None):
        dlg = tk.Toplevel(self.root)
        dlg.title("LLM Provider & Model Configuration")
        dlg.geometry("560x480")
        dlg.transient(self.root)
        dlg.grab_set()

        llm_cfg = self.cfg.setdefault("llm", {})
        api_keys_dict = llm_cfg.setdefault("api_keys", {})

        current_prov = preselect_provider or llm_cfg.get("provider", "openai")
        if current_prov not in LLM_PRESETS:
            current_prov = "openai"

        ttk.Label(
            dlg,
            text="Select an AI model to interact with the SAS Viya MCP server:",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=16, pady=(12, 6))

        frame = ttk.Frame(dlg, padding=14)
        frame.pack(fill="both", expand=True)

        # Provider Selector
        ttk.Label(frame, text="Provider:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=6)
        provider_var = tk.StringVar(value=current_prov)
        provider_choices = [
            ("openai", "OpenAI (Default: GPT-4o / mini)"),
            ("claude", "Anthropic Claude (Default: 3.5 Sonnet / Haiku)"),
            ("ollama", "Ollama (Local / Private)"),
            ("llamacpp", "llama.cpp (Local GGUF)"),
        ]
        provider_combo = ttk.Combobox(
            frame,
            textvariable=provider_var,
            values=[k for k, _ in provider_choices],
            state="readonly",
            width=28
        )
        provider_combo.grid(row=0, column=1, sticky="ew", pady=6)

        # Model Selector with auto-fill
        ttk.Label(frame, text="Model:", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=6)
        model_var = tk.StringVar(value=llm_cfg.get("model", "gpt-4o-mini"))
        model_combo = ttk.Combobox(frame, textvariable=model_var)
        model_combo.grid(row=1, column=1, sticky="ew", pady=6)

        # Base URL
        ttk.Label(frame, text="Endpoint / Base URL:").grid(row=2, column=0, sticky="w", pady=6)
        url_var = tk.StringVar(value=llm_cfg.get("base_url", "https://api.openai.com/v1"))
        entry_url = ttk.Entry(frame, textvariable=url_var)
        entry_url.grid(row=2, column=1, sticky="ew", pady=6)

        # API Key
        ttk.Label(frame, text="API Key:").grid(row=3, column=0, sticky="w", pady=6)
        key_container = ttk.Frame(frame)
        key_container.grid(row=3, column=1, sticky="ew", pady=6)

        key_var = tk.StringVar(value=api_keys_dict.get(current_prov, "") or llm_cfg.get("api_key", ""))
        entry_key = ttk.Entry(key_container, textvariable=key_var, show="*")
        entry_key.pack(side="left", fill="x", expand=True, padx=(0, 4))

        show_key_var = tk.BooleanVar(value=False)
        def toggle_key_mask():
            if show_key_var.get():
                entry_key.config(show="")
            else:
                entry_key.config(show="*")
        cb_show = ttk.Checkbutton(key_container, text="Show", variable=show_key_var, command=toggle_key_mask)
        cb_show.pack(side="right")

        desc_lbl = ttk.Label(frame, text="", font=("Segoe UI", 8), foreground="#555555", wraplength=480)
        desc_lbl.grid(row=4, column=0, columnspan=2, sticky="w", pady=(8, 4))

        frame.columnconfigure(1, weight=1)

        def sync_form_with_provider(p):
            preset = LLM_PRESETS.get(p, LLM_PRESETS["openai"])
            url_var.set(preset["base_url"])
            model_combo["values"] = preset["models"]
            
            if not model_var.get() or model_var.get() not in preset["models"]:
                model_var.set(preset["default_model"])
            
            stored_key = api_keys_dict.get(p, "")
            if not stored_key and p == llm_cfg.get("provider"):
                stored_key = llm_cfg.get("api_key", "")
            if not stored_key and preset.get("env_key"):
                stored_key = os.environ.get(preset["env_key"], "")
            key_var.set(stored_key)

            desc_lbl.config(text=f"ℹ️ {preset['doc']}\nSuggested models: {', '.join(preset['models'])}")

        provider_combo.bind("<<ComboboxSelected>>", lambda _: sync_form_with_provider(provider_var.get()))
        sync_form_with_provider(current_prov)

        def save_and_close():
            p = provider_var.get()
            preset = LLM_PRESETS.get(p, LLM_PRESETS["openai"])

            llm_cfg["provider"] = p
            llm_cfg["base_url"] = url_var.get().strip() or preset["base_url"]
            llm_cfg["model"] = model_var.get().strip() or preset["default_model"]
            
            new_key = key_var.get().strip()
            api_keys_dict[p] = new_key
            llm_cfg["api_key"] = new_key

            self.chat_provider_var.set(p)
            self.chat_model_var.set(llm_cfg["model"])
            self._update_model_choices(p)
            self._apply_llm_config()

            dlg.destroy()
            messagebox.showinfo("Configured", f"LLM Agent updated to: {p.upper()} ({llm_cfg['model']})")

        btn_frame = ttk.Frame(dlg, padding=12)
        btn_frame.pack(fill="x", side="bottom")
        ttk.Button(btn_frame, text="Save & Apply", command=save_and_close).pack(side="right", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=dlg.destroy).pack(side="right", padx=4)

    # -------------------------------------------------------------
    # Shared Helpers & Form Logic
    # -------------------------------------------------------------
    def set_output(self, text):
        def _set():
            self.out_text.configure(state="normal")
            self.out_text.delete("1.0", "end")
            self.out_text.insert("end", text)
            self.out_text.configure(state="disabled")
        self.root.after(0, _set)

    def _clear_output(self):
        self.set_output("")

    def _copy_output(self):
        content = self.out_text.get("1.0", "end-1c")
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("Copied", "Output copied to clipboard.")

    def set_status(self, text, color=None):
        def _st():
            self.lbl_status.config(text=text, foreground=color or "#666666")
        self.root.after(0, _st)

    def _toggle_ssl(self):
        self.cfg["verify_ssl"] = self.ssl_var.get()
        state = "Enabled" if self.cfg["verify_ssl"] else "Disabled (Insecure/Self-Signed)"
        messagebox.showinfo("SSL Security", f"SSL/HTTPS certificate verification: {state}.")

    def _get_token_flow(self):
        tok = load_token(self.cfg)
        if not tok:
            resp = messagebox.askyesno(
                "SAS Viya Authentication",
                "No authentication token is configured or stored.\n\n"
                "Would you like to log in to SAS Viya via your browser now?\n\n"
                "(Select 'No' to enter a token manually)."
            )
            if resp:
                tok = login(self.cfg)
            else:
                user_token = simpledialog.askstring("Personal Token", "Enter Bearer token for SAS MCP:")
                if user_token and user_token.strip():
                    tok = user_token.strip()
                    save_token(tok)
        return tok

    def _force_relogin(self):
        try:
            clear_token()
            self.set_status("Logging in...", "blue")
            tok = login(self.cfg)
            if tok:
                messagebox.showinfo("Success", "Logged in successfully.")
                self._load_tools_async()
        except Exception as e:
            messagebox.showerror("Login Error", str(e))
            self.set_status("Authentication error", "red")

    def _edit_token(self):
        curr = load_token(self.cfg) or ""
        new_tok = simpledialog.askstring("Edit Token", "Current or new Bearer token:", initialvalue=curr)
        if new_tok is not None:
            if new_tok.strip():
                save_token(new_tok.strip())
                messagebox.showinfo("Saved", "Token updated successfully.")
                self._load_tools_async()
            else:
                clear_token()
                messagebox.showinfo("Token Cleared", "Stored token has been removed.")

    def _show_config_info(self):
        p = get_config_path()
        messagebox.showinfo("Configuration", f"Configuration file loaded from:\n{p}")

    def _load_tools_async(self):
        self.set_status("Connecting to MCP server...", "blue")
        self.btn_refresh.configure(state="disabled")
        self.btn_run.configure(state="disabled")

        def worker():
            try:
                tok = self._get_token_flow()
                url = self.cfg.get("mcp_server_url", "")
                if not url:
                    raise ValueError("MCP server URL is not configured in config.json")
                
                tools = run_async(list_tools, url, tok, self.cfg)
                self.tools = tools or []
                self.root.after(0, self._render_tools_list)
                self.set_status(f"Connected ({len(self.tools)} actions available)", "#007700")
            except Exception as e:
                err = str(e)
                self.set_output(
                    f"Error connecting to SAS MCP:\n\n{err}\n\n"
                    f"Please verify:\n"
                    f"- Server URL: {self.cfg.get('mcp_server_url')}\n"
                    f"- Token / OAuth permissions\n"
                    f"- HTTPS network connectivity and SSL certificates"
                )
                self.set_status("Connection error", "red")
            finally:
                self.root.after(0, lambda: self.btn_refresh.configure(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _render_tools_list(self):
        self._filter_tools()
        if self.tools:
            self.set_output("Select an action from the left panel to configure its parameters.")
            if not self.chat_display.get("1.0", "end-1c").strip():
                prov = self.cfg.get("llm", {}).get("provider", "openai").upper()
                mod = self.cfg.get("llm", {}).get("model", "gpt-4o-mini")
                self._append_chat(
                    None,
                    f"Hello! Connected to SAS Viya with {len(self.tools)} available tools.\n"
                    f"Active agent: {prov} ({mod}). Ask me in natural language to evaluate models or run workflows.",
                    "system_msg"
                )

    def _filter_tools(self):
        query = self.filter_var.get().strip().lower()
        for item in self.tv.get_children():
            self.tv.delete(item)

        for tool in self.tools:
            name = getattr(tool, "name", "")
            desc = getattr(tool, "description", "") or ""
            if not query or query in name.lower() or query in desc.lower():
                first_line_desc = desc.split("\n")[0][:60]
                self.tv.insert("", "end", iid=name, text=name, values=(first_line_desc,))

    def _on_tool_select(self):
        sel = self.tv.selection()
        if not sel:
            return
        tool_name = sel[0]
        tool = next((t for t in self.tools if t.name == tool_name), None)
        if not tool:
            return
        
        self._selected_tool = tool
        self._build_form(tool)
        self.btn_run.configure(state="normal")
        desc = getattr(tool, "description", "") or "(No description)"
        self.set_output(f"Selected action: {tool.name}\n\nDescription:\n{desc}")

    def _build_form(self, tool):
        for widget in self.form_inner.winfo_children():
            widget.destroy()
        self._fields = []

        schema = getattr(tool, "inputSchema", {}) or {}
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        if not properties:
            lbl = ttk.Label(self.form_inner, text="This action requires no input parameters.", font=("Segoe UI", 9, "italic"))
            lbl.pack(anchor="w", padx=10, pady=10)
            return

        grid_frame = ttk.Frame(self.form_inner)
        grid_frame.pack(fill="x", expand=True, padx=4, pady=4)
        grid_frame.columnconfigure(1, weight=1)

        row = 0
        for name, prop in properties.items():
            is_req = name in required
            label_text = f"{name} *:" if is_req else f"{name}:"
            prop_type = prop.get("type", "string")
            prop_desc = prop.get("description", "")

            lbl = ttk.Label(grid_frame, text=label_text, font=("Segoe UI", 9, "bold" if is_req else "normal"))
            lbl.grid(row=row, column=0, sticky="nw", padx=(4, 8), pady=4)

            field_container = ttk.Frame(grid_frame)
            field_container.grid(row=row, column=1, sticky="ew", padx=4, pady=4)

            if prop_type == "boolean":
                var = tk.BooleanVar(value=bool(prop.get("default", False)))
                cb = ttk.Checkbutton(field_container, text="Enabled / True", variable=var)
                cb.pack(anchor="w")
                self._fields.append((name, var, "bool"))
            elif prop_type in ("object", "array"):
                txt = tk.Text(field_container, height=4, font=("Consolas", 9), wrap="none")
                txt_scroll = ttk.Scrollbar(field_container, orient="vertical", command=txt.yview)
                txt.configure(yscrollcommand=txt_scroll.set)
                txt.pack(side="left", fill="both", expand=True)
                txt_scroll.pack(side="right", fill="y")
                
                default_val = prop.get("default")
                if default_val is not None:
                    txt.insert("1.0", json.dumps(default_val, indent=2))
                self._fields.append((name, txt, "json"))
            elif prop_type in ("integer", "number"):
                entry = ttk.Entry(field_container)
                entry.pack(fill="x", expand=True)
                default_val = prop.get("default")
                if default_val is not None:
                    entry.insert(0, str(default_val))
                self._fields.append((name, entry, prop_type))
            else:
                entry = ttk.Entry(field_container)
                entry.pack(fill="x", expand=True)
                default_val = prop.get("default")
                if default_val is not None:
                    entry.insert(0, str(default_val))
                self._fields.append((name, entry, "string"))

            if prop_desc:
                desc_lbl = ttk.Label(field_container, text=prop_desc, font=("Segoe UI", 8), foreground="#666666", wraplength=450)
                desc_lbl.pack(anchor="w", pady=(2, 0))

            row += 1

    def _collect_args(self):
        args = {}
        for name, widget, kind in self._fields:
            if kind == "bool":
                args[name] = bool(widget.get())
            elif kind == "json":
                val = widget.get("1.0", "end-1c").strip()
                if val:
                    try:
                        args[name] = json.loads(val)
                    except Exception as e:
                        raise ValueError(f"Field '{name}' contains invalid JSON: {e}")
            elif kind == "integer":
                val = widget.get().strip()
                if val:
                    try:
                        args[name] = int(val)
                    except ValueError:
                        raise ValueError(f"Field '{name}' must be an integer.")
            elif kind == "number":
                val = widget.get().strip()
                if val:
                    try:
                        args[name] = float(val)
                    except ValueError:
                        raise ValueError(f"Field '{name}' must be a number.")
            else:
                val = widget.get().strip()
                if val:
                    args[name] = val
        return args

    def _run_tool(self):
        if not self._selected_tool:
            return

        try:
            args = self._collect_args()
        except ValueError as e:
            messagebox.showwarning("Invalid Input", str(e))
            return

        tool_name = self._selected_tool.name
        self.btn_run.configure(state="disabled")
        self.progress.pack(side="left", padx=4)
        self.progress.start(10)
        self.set_status(f"Executing '{tool_name}'...", "blue")
        self.set_output(f"Executing action '{tool_name}' with arguments:\n{json.dumps(args, indent=2, ensure_ascii=False)}\n\nWaiting for SAS Viya response...")

        def worker():
            try:
                tok = self._get_token_flow()
                url = self.cfg.get("mcp_server_url", "")
                result = run_async(call_tool, url, tok, tool_name, args, self.cfg)
                formatted = extract_text(result)
                self.set_output(f"=== RESULT FOR '{tool_name}' ===\n\n{formatted}")
                self.set_status("Execution completed successfully", "#007700")
            except Exception as e:
                self.set_output(f"=== ERROR EXECUTING '{tool_name}' ===\n\n{str(e)}")
                self.set_status("Execution error", "red")
            finally:
                def cleanup():
                    self.progress.stop()
                    self.progress.pack_forget()
                    self.btn_run.configure(state="normal")
                self.root.after(0, cleanup)

        threading.Thread(target=worker, daemon=True).start()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
