#!/usr/bin/env python3
"""Interface gráfica modular do Organizador Inteligente."""

from __future__ import annotations

import os
import queue
import threading
import webbrowser
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk
from dotenv import load_dotenv, set_key

import organizador


class GuiLogger:
    """Envia mensagens do núcleo para o log da interface com timestamp."""

    def __init__(self, eventos: queue.Queue[tuple[str, Any]]) -> None:
        self.eventos = eventos

    def _enviar(self, nivel: str, mensagem: str) -> None:
        horario = datetime.now().strftime("%H:%M:%S")
        self.eventos.put(("log", f"[{horario}] {nivel}: {mensagem}"))

    def info(self, mensagem: str) -> None:
        """Registra uma informação."""
        self._enviar("INFO", mensagem)

    def warning(self, mensagem: str) -> None:
        """Registra um alerta."""
        self._enviar("AVISO", mensagem)

    def error(self, mensagem: str) -> None:
        """Registra um erro."""
        self._enviar("ERRO", mensagem)


class HeaderFrame(ctk.CTkFrame):
    """Apresenta o título e a descrição do aplicativo."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        ctk.CTkLabel(self, text="Organizador Inteligente", font=ctk.CTkFont(size=28, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(self, text="Classifique arquivos e gere resumos em poucos cliques.", text_color="#9BA4B5").pack(anchor="w", pady=(4, 0))


class DirectorySelectionFrame(ctk.CTkFrame):
    """Controla a seleção da pasta de trabalho."""

    def __init__(self, master: ctk.CTkBaseClass, pasta_var: ctk.StringVar) -> None:
        super().__init__(master)
        self.pasta_var = pasta_var
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Pasta para organizar", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=2, padx=16, pady=(14, 6), sticky="w")
        ctk.CTkEntry(self, textvariable=pasta_var, state="readonly").grid(row=1, column=0, padx=(16, 8), pady=(0, 14), sticky="ew")
        ctk.CTkButton(self, text="Procurar...", width=120, command=self._procurar).grid(row=1, column=1, padx=(0, 16), pady=(0, 14))

    def _procurar(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_var.set(pasta)


class SettingsFrame(ctk.CTkFrame):
    """Reúne configurações da API e da operação."""

    MODELOS = ["qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"]

    def __init__(self, master: ctk.CTkBaseClass, chave_var: ctk.StringVar, modelo_var: ctk.StringVar,
                 ia_var: ctk.BooleanVar, teste_var: ctk.BooleanVar, max_files_var: ctk.StringVar,
                 abrir_chaves: Callable[[], None]) -> None:
        super().__init__(master)
        self.chave_var = chave_var
        self.modelo_var = modelo_var
        self.ia_var = ia_var
        self.teste_var = teste_var
        self.max_files_var = max_files_var
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, padx=16, pady=(14, 8), sticky="w")
        ctk.CTkLabel(self, text="Chave Groq").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        ctk.CTkEntry(self, textvariable=chave_var, show="*").grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        ctk.CTkButton(self, text="Obter Chave Grátis", width=150, command=abrir_chaves).grid(row=1, column=2, padx=8, pady=6)
        ctk.CTkSwitch(self, text="Ativar resumos com IA", variable=ia_var).grid(row=1, column=3, padx=(8, 16), pady=6, sticky="w")
        ctk.CTkLabel(self, text="Modelo").grid(row=2, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        modelo = ctk.CTkComboBox(self, variable=modelo_var, values=self.MODELOS)
        modelo.grid(row=2, column=1, columnspan=2, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkLabel(self, text="Modelo usado para gerar os resumos.", text_color="#9BA4B5").grid(row=3, column=1, columnspan=2, padx=8, sticky="w")
        ctk.CTkCheckBox(self, text="Modo Teste / Dry Run", variable=teste_var).grid(row=2, column=3, padx=(8, 16), pady=(6, 14), sticky="w")
        ctk.CTkLabel(self, text="Máximo de arquivos").grid(row=4, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        ctk.CTkEntry(self, textvariable=max_files_var, placeholder_text="Todos").grid(row=4, column=1, columnspan=2, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkLabel(self, text="O Dry Run apenas simula a operação.", text_color="#9BA4B5").grid(row=4, column=3, padx=(8, 16), pady=(6, 14), sticky="w")


class ConsoleLogFrame(ctk.CTkFrame):
    """Exibe o log da operação."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Log de execução", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        self.caixa = ctk.CTkTextbox(self, wrap="word", state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.caixa.grid(row=1, column=0, padx=16, pady=(0, 16), sticky="nsew")

    def adicionar(self, mensagem: str) -> None:
        """Adiciona uma linha ao log."""
        self.caixa.configure(state="normal")
        self.caixa.insert("end", mensagem + "\n")
        self.caixa.see("end")
        self.caixa.configure(state="disabled")


class ExecutionControlFrame(ctk.CTkFrame):
    """Apresenta progresso e ações de execução."""

    def __init__(self, master: ctk.CTkBaseClass, iniciar: Callable[[], None], cancelar: Callable[[], None]) -> None:
        super().__init__(master, fg_color="transparent")
        self.grid_columnconfigure(0, weight=1)
        self.barra = ctk.CTkProgressBar(self, mode="determinate")
        self.barra.set(0)
        self.barra.grid(row=0, column=0, padx=(0, 14), sticky="ew")
        self.iniciar = ctk.CTkButton(self, text="Iniciar Organização", height=38, command=iniciar)
        self.iniciar.grid(row=0, column=1, padx=(0, 8))
        self.cancelar = ctk.CTkButton(self, text="Cancelar", height=38, state="disabled", command=cancelar)
        self.cancelar.grid(row=0, column=2)


class OrganizadorApp(ctk.CTk):
    """Janela principal com estado de execução centralizado."""

    def __init__(self) -> None:
        super().__init__()
        self.title("Organizador Inteligente")
        self.geometry("920x720")
        self.minsize(760, 620)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        organizador.carregar_ambiente()
        self.estado = "ocioso"
        self.eventos: queue.Queue[tuple[str, Any]] = queue.Queue()
        self.pasta_var = ctk.StringVar()
        self.chave_var = ctk.StringVar(value=os.getenv("GROQ_API_KEY", ""))
        self.modelo_var = ctk.StringVar(value=organizador.MODELO_PADRAO)
        self.ia_var = ctk.BooleanVar(value=True)
        self.teste_var = ctk.BooleanVar(value=False)
        self.max_files_var = ctk.StringVar()
        self.cancelamento = threading.Event()
        self._criar_interface()
        self.after(100, self._processar_eventos)

    def _criar_interface(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        HeaderFrame(self).grid(row=0, column=0, padx=28, pady=(24, 12), sticky="ew")
        DirectorySelectionFrame(self, self.pasta_var).grid(row=1, column=0, padx=28, pady=8, sticky="ew")
        SettingsFrame(self, self.chave_var, self.modelo_var, self.ia_var, self.teste_var, self.max_files_var, self._abrir_chaves_groq).grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        self.log_frame = ConsoleLogFrame(self)
        self.log_frame.grid(row=3, column=0, padx=28, pady=8, sticky="nsew")
        self.controles = ExecutionControlFrame(self, self._iniciar, self._cancelar)
        self.controles.grid(row=4, column=0, padx=28, pady=(8, 24), sticky="ew")

    def _abrir_chaves_groq(self) -> None:
        webbrowser.open_new_tab(organizador.URL_CHAVES_GROQ)

    def _salvar_chave(self) -> bool:
        chave = self.chave_var.get().strip()
        if not chave:
            return True
        try:
            caminho = organizador.caminho_env_gravavel()
            set_key(str(caminho), "GROQ_API_KEY", chave)
            os.environ["GROQ_API_KEY"] = chave
            return True
        except OSError as erro:
            self._adicionar_log(f"Falha ao salvar .env: {erro}")
            messagebox.showerror("Falha ao salvar chave", str(erro))
            return False

    def _iniciar(self) -> None:
        pasta = self.pasta_var.get().strip()
        if not pasta or not Path(pasta).is_dir():
            messagebox.showwarning("Pasta inválida", "Selecione uma pasta válida antes de iniciar.")
            return
        max_files: int | None = None
        if self.max_files_var.get().strip():
            try:
                max_files = int(self.max_files_var.get())
                if max_files < 1:
                    raise ValueError
            except ValueError:
                messagebox.showwarning("Limite inválido", "Informe um número maior que zero.")
                return
        arquivos = [item for item in Path(pasta).iterdir() if item.is_file() and item.name not in organizador.ARQUIVOS_INTERNOS]
        quantidade = min(len(arquivos), max_files) if max_files else len(arquivos)
        if not messagebox.askyesno("Confirmar organização", f"Serão processados {quantidade} arquivo(s). Deseja continuar?"):
            return
        if not self._salvar_chave():
            return
        self.estado = "executando"
        self.cancelamento.clear()
        self.controles.iniciar.configure(state="disabled", text="Processando...")
        self.controles.cancelar.configure(state="normal")
        self.controles.barra.set(0)
        configuracoes = (self.teste_var.get(), not self.ia_var.get(), self.modelo_var.get(), max_files)
        threading.Thread(target=self._executar, args=(pasta, configuracoes), daemon=True).start()

    def _executar(self, pasta: str, configuracoes: tuple[bool, bool, str, int | None]) -> None:
        dry_run, no_ai, modelo, max_files = configuracoes
        logger = GuiLogger(self.eventos)
        try:
            organizador.organizar_pasta(pasta, dry_run=dry_run, no_ai=no_ai, model=modelo, max_files=max_files,
                                        logger=logger, progresso=lambda valor: self.eventos.put(("progresso", valor)),
                                        cancel_event=self.cancelamento)
            self.eventos.put(("fim", "Organização concluída."))
        except organizador.OperacaoCancelada:
            self.eventos.put(("cancelado", "Operação cancelada."))
        except Exception as erro:
            self.eventos.put(("erro", str(erro)))

    def _cancelar(self) -> None:
        self.cancelamento.set()
        self.controles.cancelar.configure(state="disabled")
        self._adicionar_log("Cancelamento solicitado; aguardando a etapa atual terminar...")

    def _adicionar_log(self, mensagem: str) -> None:
        self.log_frame.adicionar(mensagem)

    def _processar_eventos(self) -> None:
        try:
            while True:
                tipo, valor = self.eventos.get_nowait()
                if tipo == "log":
                    self._adicionar_log(valor)
                elif tipo == "progresso":
                    self.controles.barra.set(min(1.0, self.controles.barra.get() + valor))
                elif tipo in {"fim", "cancelado", "erro"}:
                    self.estado = "ocioso" if tipo != "erro" else "erro"
                    self._adicionar_log(valor if tipo != "erro" else f"ERRO: {valor}")
                    self.controles.iniciar.configure(state="normal", text="Iniciar Organização")
                    self.controles.cancelar.configure(state="disabled")
                    if tipo == "erro":
                        messagebox.showerror("Erro na organização", valor)
        except queue.Empty:
            pass
        self.after(100, self._processar_eventos)


if __name__ == "__main__":
    OrganizadorApp().mainloop()
