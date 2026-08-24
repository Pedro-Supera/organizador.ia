#!/usr/bin/env python3
"""Interface gráfica do Organizador Inteligente."""

import os
import queue
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from dotenv import load_dotenv, set_key
from rich.console import Console

import organizador


class LogWriter:
    """Redireciona a saída do Rich para a fila de eventos da GUI."""

    def __init__(self, eventos: queue.Queue[tuple[str, Any]]) -> None:
        self.eventos = eventos

    def write(self, texto: str) -> None:
        if texto.strip():
            self.eventos.put(("log", texto.rstrip()))

    def flush(self) -> None:
        pass


class OrganizadorApp(ctk.CTk):
    """Janela principal do organizador de arquivos."""

    MODELOS = [
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "groq/compound",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.title("Organizador Inteligente")
        self.geometry("880x680")
        self.minsize(720, 560)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        load_dotenv(dotenv_path=organizador.CAMINHO_ENV)
        self.eventos = queue.Queue()
        self.pasta_var = ctk.StringVar()
        self.chave_var = ctk.StringVar(value=os.getenv("GROQ_API_KEY", ""))
        self.modelo_var = ctk.StringVar(value=self.MODELOS[0])
        self.ia_var = ctk.BooleanVar(value=True)
        self.teste_var = ctk.BooleanVar(value=False)
        self.max_files_var = ctk.StringVar()
        self.cancelamento = threading.Event()
        self.progresso = 0.0
        self._criar_interface()
        self.after(100, self._processar_eventos)

    def _criar_interface(self) -> None:
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
        ctk.CTkLabel(opcoes, text="Configurações", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, padx=16, pady=(14, 8), sticky="w")
        ctk.CTkLabel(opcoes, text="Chave Groq").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        ctk.CTkEntry(opcoes, textvariable=self.chave_var, show="*").grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkButton(opcoes, text="Obter Chave Grátis", width=150, command=self._abrir_chaves_groq).grid(row=1, column=2, padx=8, pady=6)
        ctk.CTkSwitch(opcoes, text="Ativar resumos com IA", variable=self.ia_var).grid(row=1, column=3, padx=(8, 16), pady=6, sticky="w")
        ctk.CTkLabel(opcoes, text="Modelo").grid(row=2, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        ctk.CTkComboBox(opcoes, variable=self.modelo_var, values=self.MODELOS).grid(row=2, column=1, columnspan=2, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkCheckBox(opcoes, text="Modo Teste / Dry Run", variable=self.teste_var).grid(row=2, column=3, padx=(8, 16), pady=(6, 14), sticky="w")
        ctk.CTkLabel(opcoes, text="Máximo de arquivos").grid(row=3, column=0, padx=(16, 8), pady=(0, 14), sticky="w")
        ctk.CTkEntry(opcoes, textvariable=self.max_files_var, placeholder_text="Todos").grid(row=3, column=1, columnspan=2, padx=8, pady=(0, 14), sticky="ew")

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
        self.iniciar_btn.grid(row=0, column=1, padx=(0, 8))
        self.cancelar_btn = ctk.CTkButton(rodape, text="Cancelar", height=38, state="disabled", command=self._cancelar)
        self.cancelar_btn.grid(row=0, column=2)

    def _abrir_chaves_groq(self) -> None:
        webbrowser.open_new_tab("https://console.groq.com/keys")

    def _procurar_pasta(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_var.set(pasta)

    def _adicionar_log(self, texto: str) -> None:
        self.log_box.configure(state="normal")
        self.log_box.insert("end", texto + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _salvar_chave(self) -> bool:
        chave = self.chave_var.get().strip()
        if not chave:
            return True
        try:
            set_key(str(organizador.CAMINHO_ENV), "GROQ_API_KEY", chave)
            os.environ["GROQ_API_KEY"] = chave
        except OSError as erro:
            mensagem = f"Não foi possível salvar a chave no arquivo .env: {erro}"
            self._adicionar_log(mensagem)
            messagebox.showerror("Falha ao salvar chave", mensagem)
            return False
        return True

    def _iniciar(self) -> None:
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
        max_files = None
        if self.max_files_var.get().strip():
            try:
                max_files = int(self.max_files_var.get())
                if max_files < 1:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Limite inválido", "O máximo de arquivos deve ser um número maior que zero.")
                return
        arquivos = [item for item in Path(pasta).iterdir() if item.is_file() and item.name not in organizador.ARQUIVOS_INTERNOS]
        quantidade = min(len(arquivos), max_files) if max_files else len(arquivos)
        if not messagebox.askyesno("Confirmar organização", f"Serão processados {quantidade} arquivo(s). Deseja continuar?"):
            return

        if not self._salvar_chave():
            return
        self._adicionar_log("Iniciando organização...\n")
        self.progresso = 0.0
        self.barra.set(0)
        self.iniciar_btn.configure(state="disabled", text="Processando...")
        self.cancelar_btn.configure(state="normal")
        self.cancelamento.clear()
        configuracoes = (self.teste_var.get(), not self.ia_var.get(), self.modelo_var.get(), max_files)
        thread = threading.Thread(target=self._executar, args=(pasta, configuracoes), daemon=True)
        thread.start()

    def _executar(self, pasta: str, configuracoes: tuple[bool, bool, str, int | None]) -> None:
        dry_run, no_ai, modelo, max_files = configuracoes
        console_anterior = organizador.console
        organizador.console = Console(file=LogWriter(self.eventos), no_color=True, force_terminal=False)
        try:
            organizador.organizar_pasta(
                pasta,
                dry_run=dry_run,
                no_ai=no_ai,
                model=modelo,
                max_files=max_files,
                progresso=lambda valor: self.eventos.put(("progresso", valor)),
                cancel_event=self.cancelamento,
            )
            self.eventos.put(("fim", "Organização concluída."))
        except organizador.OperacaoCancelada:
            self.eventos.put(("cancelado", "Operação cancelada."))
        except Exception as erro:
            self.eventos.put(("erro", str(erro)))
        finally:
            organizador.console = console_anterior

    def _cancelar(self) -> None:
        self.cancelamento.set()
        self.cancelar_btn.configure(state="disabled")
        self._adicionar_log("Cancelamento solicitado; aguardando a etapa atual terminar...")

    def _processar_eventos(self) -> None:
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
                    self.cancelar_btn.configure(state="disabled")
                elif tipo == "cancelado":
                    self._adicionar_log("\n" + valor)
                    self.iniciar_btn.configure(state="normal", text="Iniciar Organização")
                    self.cancelar_btn.configure(state="disabled")
                elif tipo == "erro":
                    self._adicionar_log("\nERRO: " + valor)
                    self.iniciar_btn.configure(state="normal", text="Iniciar Organização")
                    self.cancelar_btn.configure(state="disabled")
                    messagebox.showerror("Erro na organização", valor)
        except queue.Empty:
            pass
        self.after(100, self._processar_eventos)


if __name__ == "__main__":
    app = OrganizadorApp()
    app.mainloop()
