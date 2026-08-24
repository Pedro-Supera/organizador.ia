#!/usr/bin/env python3
"""Interface gráfica do Organizador Inteligente."""

import os
import queue
import threading
from pathlib import Path

import customtkinter as ctk
from dotenv import load_dotenv, set_key
from tkinter import filedialog, messagebox
from rich.console import Console

import organizador


class LogWriter:
    def __init__(self, eventos):
        self.eventos = eventos

    def write(self, texto):
        if texto.strip():
            self.eventos.put(("log", texto.rstrip()))

    def flush(self):
        pass


class OrganizadorApp(ctk.CTk):
    MODELOS = [
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound",
    ]

    def __init__(self):
        super().__init__()
        self.title("Organizador Inteligente")
        self.geometry("880x680")
        self.minsize(720, 560)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        load_dotenv()
        self.eventos = queue.Queue()
        self.pasta_var = ctk.StringVar()
        self.chave_var = ctk.StringVar(value=os.getenv("GROQ_API_KEY", ""))
        self.modelo_var = ctk.StringVar(value=self.MODELOS[0])
        self.ia_var = ctk.BooleanVar(value=True)
        self.teste_var = ctk.BooleanVar(value=False)
        self.progresso = 0.0
        self._criar_interface()
        self.after(100, self._processar_eventos)

    def _criar_interface(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        cabecalho = ctk.CTkFrame(self, fg_color="transparent")
        cabecalho.grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        ctk.CTkLabel(cabecalho, text="Organizador Inteligente", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(cabecalho, text="Classifique arquivos e gere resumos em poucos cliques.", text_color="#9BA4B5").pack(anchor="w", pady=(4, 0))

        pasta_frame = ctk.CTkFrame(self)
        pasta_frame.grid(row=1, column=0, padx=28, pady=8, sticky="ew")
        pasta_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(pasta_frame, text="Pasta para organizar", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 6), sticky="w")
        self.pasta_entry = ctk.CTkEntry(pasta_frame, textvariable=self.pasta_var, state="readonly")
        self.pasta_entry.grid(row=1, column=0, padx=(16, 8), pady=(0, 14), sticky="ew")
        ctk.CTkButton(pasta_frame, text="Procurar...", width=120, command=self._procurar_pasta).grid(row=1, column=1, padx=(0, 16), pady=(0, 14))

        opcoes = ctk.CTkFrame(self)
        opcoes.grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        opcoes.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(opcoes, text="Configurações", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=3, padx=16, pady=(14, 8), sticky="w")
        ctk.CTkLabel(opcoes, text="Chave Groq").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        ctk.CTkEntry(opcoes, textvariable=self.chave_var, show="*").grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkSwitch(opcoes, text="Ativar resumos com IA", variable=self.ia_var).grid(row=1, column=2, padx=(8, 16), pady=6, sticky="w")
        ctk.CTkLabel(opcoes, text="Modelo").grid(row=2, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        ctk.CTkComboBox(opcoes, variable=self.modelo_var, values=self.MODELOS).grid(row=2, column=1, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkCheckBox(opcoes, text="Modo Teste / Dry Run", variable=self.teste_var).grid(row=2, column=2, padx=(8, 16), pady=(6, 14), sticky="w")

        log_frame = ctk.CTkFrame(self)
        log_frame.grid(row=3, column=0, padx=28, pady=8, sticky="nsew")
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(log_frame, text="Log de execução", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        self.log_box = ctk.CTkTextbox(log_frame, wrap="word", state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.log_box.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")

        rodape = ctk.CTkFrame(self, fg_color="transparent")
        rodape.grid(row=4, column=0, padx=28, pady=(8, 24), sticky="ew")
        rodape.grid_columnconfigure(0, weight=1)
        self.barra = ctk.CTkProgressBar(rodape, mode="determinate")
        self.barra.set(0)
        self.barra.grid(row=0, column=0, padx=(0, 14), sticky="ew")
        self.iniciar_btn = ctk.CTkButton(rodape, text="Iniciar Organização", height=38, command=self._iniciar)
        self.iniciar_btn.grid(row=0, column=1)

    def _procurar_pasta(self):
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_var.set(pasta)

    def _adicionar_log(self, texto):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", texto + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _salvar_chave(self):
        chave = self.chave_var.get().strip()
        if chave:
            set_key(str(Path(__file__).with_name(".env")), "GROQ_API_KEY", chave)
            os.environ["GROQ_API_KEY"] = chave

    def _iniciar(self):
        pasta = self.pasta_var.get().strip()
        if not pasta:
            messagebox.showwarning("Pasta não selecionada", "Escolha uma pasta antes de iniciar.")
            return
        if not Path(pasta).is_dir():
            messagebox.showerror("Pasta inválida", "A pasta selecionada não existe.")
            return
        if self.ia_var.get() and not self.chave_var.get().strip():
            messagebox.showwarning("Chave ausente", "Informe a GROQ_API_KEY ou desative os resumos com IA.")
            return

        self._salvar_chave()
        self._adicionar_log("Iniciando organização...\n")
        self.progresso = 0.0
        self.barra.set(0)
        self.iniciar_btn.configure(state="disabled", text="Processando...")
        configuracoes = (self.teste_var.get(), not self.ia_var.get(), self.modelo_var.get())
        thread = threading.Thread(target=self._executar, args=(pasta, configuracoes), daemon=True)
        thread.start()

    def _executar(self, pasta, configuracoes):
        dry_run, no_ai, modelo = configuracoes
        console_anterior = organizador.console
        organizador.console = Console(file=LogWriter(self.eventos), no_color=True, force_terminal=False)
        try:
            organizador.organizar_pasta(
                pasta,
                dry_run=dry_run,
                no_ai=no_ai,
                model=modelo,
                progresso=lambda valor: self.eventos.put(("progresso", valor)),
            )
            self.eventos.put(("fim", "Organização concluída."))
        except Exception as erro:
            self.eventos.put(("erro", str(erro)))
        finally:
            organizador.console = console_anterior

    def _processar_eventos(self):
        try:
            while True:
                tipo, valor = self.eventos.get_nowait()
                if tipo == "log":
                    self._adicionar_log(valor)
                elif tipo == "progresso":
                    self.progresso = min(1.0, self.progresso + valor)
                    self.barra.set(self.progresso)
                elif tipo == "fim":
                    self.barra.set(1)
                    self._adicionar_log("\n" + valor)
                    self.iniciar_btn.configure(state="normal", text="Iniciar Organização")
                elif tipo == "erro":
                    self._adicionar_log("\nERRO: " + valor)
                    self.iniciar_btn.configure(state="normal", text="Iniciar Organização")
                    messagebox.showerror("Erro na organização", valor)
        except queue.Empty:
            pass
        self.after(100, self._processar_eventos)


if __name__ == "__main__":
    app = OrganizadorApp()
    app.mainloop()
