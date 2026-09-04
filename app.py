#!/usr/bin/env python3
"""Interface gráfica modular do Organizador Inteligente."""

from __future__ import annotations

import io
import os
import queue
import subprocess
import threading
import webbrowser
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Any
import customtkinter as ctk

import organizador

COR_CARTAO = "#171D26"
COR_BORDA = "#2B3442"
COR_TEXTO_SECUNDARIO = "#9BA4B5"
COR_PRIMARIA = "#3B82F6"
COR_SUCESSO = "#22C55E"
COR_ALERTA = "#F59E0B"
COR_ERRO = "#EF4444"
COR_INFO = "#38BDF8"


def validar_max_files(valor: str) -> int | None:
    """Converte um limite de arquivos válido ou retorna None para ilimitado."""
    valor = valor.strip()
    if not valor:
        return None
    if not valor.isdigit() or int(valor) <= 0:
        raise ValueError("O limite deve ser um número inteiro maior que zero.")
    return int(valor)


class GuiLogger:
    """Envia mensagens do núcleo para o log com timestamp."""

    def __init__(self, eventos: queue.Queue[tuple[str, Any]]) -> None:
        self.eventos = eventos

    def _enviar(self, nivel: str, mensagem: str) -> None:
        horario = datetime.now().strftime("%H:%M:%S")
        self.eventos.put(("log", f"[{horario}] {nivel}: {mensagem}"))

    def info(self, mensagem: str) -> None:
        """Registra informação."""
        self._enviar("INFO", mensagem)

    def warning(self, mensagem: str) -> None:
        """Registra alerta."""
        self._enviar("AVISO", mensagem)

    def error(self, mensagem: str) -> None:
        """Registra erro."""
        self._enviar("ERRO", mensagem)


class HeaderFrame(ctk.CTkFrame):
    """Apresenta o cabeçalho da aplicação."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color="transparent")
        wrapper = ctk.CTkFrame(self, fg_color="transparent")
        wrapper.pack(anchor="w", fill="x")
        ctk.CTkLabel(wrapper, text="Organizador Inteligente", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left")
        badge = ctk.CTkLabel(wrapper, text="v1.0.0", font=ctk.CTkFont(size=11),
                              text_color=COR_TEXTO_SECUNDARIO, fg_color="#1F2937", corner_radius=6)
        badge.pack(side="left", padx=(10, 0), pady=(2, 0))
        ctk.CTkLabel(self, text="Classifique arquivos e gere resumos com IA em poucos cliques.",
                      text_color=COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=13)).pack(anchor="w", pady=(4, 0))


class DirectorySelectionFrame(ctk.CTkFrame):
    """Permite escolher UMA pasta, VARIAS pastas ou os arquivos principais do usuario."""

    MODOS = ["Uma pasta", "Varias pastas", "Principais"]

    def __init__(self, master: ctk.CTkBaseClass, pasta_var: ctk.StringVar,
                 ao_mudar: Callable[[], None] | None = None) -> None:
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.pasta_var = pasta_var
        self.ao_mudar = ao_mudar or (lambda: None)
        self.lista_pastas: list[str] = []
        self.modo_var = ctk.StringVar(value=self.MODOS[0])
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self, text="Onde organizar", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=16, pady=(14, 6), sticky="w")
        self.segmented = ctk.CTkSegmentedButton(self, values=self.MODOS, variable=self.modo_var,
                                                  command=self._trocar_modo, width=240)
        self.segmented.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="w")
        ctk.CTkLabel(self, text="O app NAO altera arquivos do sistema. Move apenas conteudo das pastas escolhidas.",
                      text_color=COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=11)).grid(
            row=2, column=0, padx=16, pady=(0, 8), sticky="w")
        # Sub-frame dinamico para o modo escolhido
        self.subframe = ctk.CTkFrame(self, fg_color="transparent")
        self.subframe.grid(row=3, column=0, padx=16, pady=(0, 14), sticky="ew")
        self.subframe.grid_columnconfigure(0, weight=1)
        # Constroi os 3 sub-frames
        self._frame_unica = self._criar_frame_unica()
        self._frame_multipla = self._criar_frame_multipla()
        self._frame_principais = self._criar_frame_principais()
        self._trocar_modo(self.MODOS[0])

    def _criar_frame_unica(self) -> ctk.CTkFrame:
        wrapper = ctk.CTkFrame(self.subframe, fg_color="transparent")
        wrapper.grid_columnconfigure(0, weight=1)
        self.entrada = ctk.CTkEntry(wrapper, textvariable=self.pasta_var, state="readonly")
        self.entrada.grid(row=0, column=0, sticky="ew")
        ctk.CTkButton(wrapper, text="Procurar...", width=120, command=self._procurar).grid(
            row=0, column=1, padx=(8, 0))
        return wrapper

    def _criar_frame_multipla(self) -> ctk.CTkFrame:
        wrapper = ctk.CTkFrame(self.subframe, fg_color="transparent")
        wrapper.grid_columnconfigure(0, weight=1)
        self.lista_box = ctk.CTkTextbox(wrapper, height=80, state="disabled")
        self.lista_box.grid(row=0, column=0, sticky="ew")
        botoes = ctk.CTkFrame(wrapper, fg_color="transparent")
        botoes.grid(row=1, column=0, pady=(8, 0), sticky="w")
        ctk.CTkButton(botoes, text="Adicionar pasta", command=self._adicionar_pasta).pack(side="left", padx=(0, 8))
        ctk.CTkButton(botoes, text="Limpar lista", fg_color="#374151",
                       command=self._limpar_lista).pack(side="left")
        return wrapper

    def _criar_frame_principais(self) -> ctk.CTkFrame:
        wrapper = ctk.CTkFrame(self.subframe, fg_color="transparent")
        wrapper.grid_columnconfigure(0, weight=1)
        self.principais_info = ctk.CTkLabel(wrapper,
            text="Inclui: Desktop, Downloads, Documents, Pictures e, se existirem, Music e Videos.",
            text_color=COR_TEXTO_SECUNDARIO, font=ctk.CTkFont(size=12), justify="left")
        self.principais_info.grid(row=0, column=0, sticky="w")
        return wrapper

    def _trocar_modo(self, modo: str) -> None:
        """Mostra o sub-frame correspondente ao modo escolhido."""
        for f in (self._frame_unica, self._frame_multipla, self._frame_principais):
            f.grid_forget()
        if modo == self.MODOS[0]:
            self._frame_unica.grid(row=0, column=0, sticky="ew")
        elif modo == self.MODOS[1]:
            self._frame_multipla.grid(row=0, column=0, sticky="ew")
        else:
            self._frame_principais.grid(row=0, column=0, sticky="ew")
        self.ao_mudar()

    def _procurar(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione a pasta para organizar")
        if pasta:
            self.pasta_var.set(pasta)
            self.ao_mudar()

    def _adicionar_pasta(self) -> None:
        pasta = filedialog.askdirectory(title="Selecione uma pasta para adicionar")
        if pasta and pasta not in self.lista_pastas:
            self.lista_pastas.append(pasta)
            self._atualizar_lista()
            self.ao_mudar()

    def _limpar_lista(self) -> None:
        self.lista_pastas.clear()
        self._atualizar_lista()
        self.ao_mudar()

    def _atualizar_lista(self) -> None:
        texto = "\n".join(self.lista_pastas) if self.lista_pastas else "(nenhuma pasta)"
        self.lista_box.configure(state="normal")
        self.lista_box.delete("1.0", "end")
        self.lista_box.insert("1.0", texto)
        self.lista_box.configure(state="disabled")

    def pastas_selecionadas(self) -> list[str]:
        """Retorna a lista de pastas a organizar conforme o modo atual."""
        modo = self.modo_var.get()
        if modo == self.MODOS[0]:
            pasta = self.pasta_var.get().strip()
            return [pasta] if pasta else []
        if modo == self.MODOS[1]:
            return list(self.lista_pastas)
        # Principais: resolver em tempo real
        pastas, _ = organizador.resolver_pastas_principais()
        return [str(p) for p in pastas]

    def definir_estado(self, estado: str) -> None:
        """Ativa ou bloqueia os controles do frame."""
        self.entrada.configure(state="normal" if estado == "normal" else "disabled")
        try:
            for botao in self._frame_multipla.winfo_children()[1].winfo_children():
                botao.configure(state=estado)
        except (IndexError, AttributeError):
            pass


class SettingsFrame(ctk.CTkFrame):
    """Reúne configurações da API e da operação."""

    MODELOS = ["qwen/qwen3.6-27b", "openai/gpt-oss-120b", "openai/gpt-oss-20b", "groq/compound"]

    def __init__(self, master: ctk.CTkBaseClass, chave_var: ctk.StringVar, modelo_var: ctk.StringVar,
                 ia_var: ctk.BooleanVar, teste_var: ctk.BooleanVar, max_files_var: ctk.StringVar,
                 abrir_chaves: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Configurações", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, columnspan=4, padx=16, pady=(14, 8), sticky="w")
        ctk.CTkLabel(self, text="Chave Groq").grid(row=1, column=0, padx=(16, 8), pady=6, sticky="w")
        chave = ctk.CTkEntry(self, textvariable=chave_var, show="*")
        chave.grid(row=1, column=1, padx=8, pady=6, sticky="ew")
        obter = ctk.CTkButton(self, text="Obter Chave Grátis", width=150, command=abrir_chaves)
        obter.grid(row=1, column=2, padx=8, pady=6)
        ia = ctk.CTkSwitch(self, text="Ativar resumos com IA", variable=ia_var)
        ia.grid(row=1, column=3, padx=(8, 16), pady=6, sticky="w")
        ctk.CTkLabel(self, text="Modelo").grid(row=2, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        modelo = ctk.CTkComboBox(self, variable=modelo_var, values=self.MODELOS)
        modelo.grid(row=2, column=1, columnspan=2, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkLabel(self, text="Modelo usado para gerar os resumos.", text_color=COR_TEXTO_SECUNDARIO).grid(row=3, column=1, columnspan=2, padx=8, sticky="w")
        teste = ctk.CTkCheckBox(self, text="Modo Simulação (Dry Run)", variable=teste_var)
        teste.grid(row=2, column=3, padx=(8, 16), pady=(6, 14), sticky="w")
        ctk.CTkLabel(self, text="Máximo de arquivos").grid(row=4, column=0, padx=(16, 8), pady=(6, 14), sticky="w")
        maximo = ctk.CTkEntry(self, textvariable=max_files_var, placeholder_text="Todos")
        maximo.grid(row=4, column=1, columnspan=2, padx=8, pady=(6, 14), sticky="ew")
        ctk.CTkLabel(self, text="O Dry Run apenas simula a operação.", text_color=COR_TEXTO_SECUNDARIO).grid(row=4, column=3, padx=(8, 16), pady=(6, 14), sticky="w")
        self.controles = [chave, obter, ia, modelo, teste, maximo]

    def definir_estado(self, estado: str) -> None:
        """Ativa ou bloqueia os controles do frame."""
        for controle in self.controles:
            controle.configure(state=estado)


class ConsoleLogFrame(ctk.CTkFrame):
    """Exibe e exporta o log da operação."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Log de execução", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, padx=16, pady=(14, 8), sticky="w")
        self.caixa = ctk.CTkTextbox(self, wrap="word", state="disabled", font=ctk.CTkFont(family="Courier", size=12))
        self.caixa.grid(row=1, column=0, padx=16, pady=(0, 8), sticky="nsew")
        utilitarios = ctk.CTkFrame(self, fg_color="transparent")
        utilitarios.grid(row=2, column=0, padx=16, pady=(0, 12), sticky="e")
        ctk.CTkButton(utilitarios, text="Limpar Log", width=110, command=self.limpar).pack(side="left", padx=4)
        ctk.CTkButton(utilitarios, text="Exportar Log", width=120, command=self.exportar).pack(side="left", padx=4)

    def adicionar(self, mensagem: str) -> None:
        """Adiciona uma linha ao log."""
        self.caixa.configure(state="normal")
        self.caixa.insert("end", mensagem + "\n")
        self.caixa.see("end")
        self.caixa.configure(state="disabled")

    def limpar(self) -> None:
        """Limpa todo o conteúdo do log."""
        self.caixa.configure(state="normal")
        self.caixa.delete("1.0", "end")
        self.caixa.configure(state="disabled")

    def exportar(self) -> None:
        """Salva o conteúdo do log em um arquivo de texto."""
        caminho = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Texto", "*.txt")])
        if caminho:
            conteudo = self.caixa.get("1.0", "end-1c")
            Path(caminho).write_text(conteudo, encoding="utf-8")


class ExecutionControlFrame(ctk.CTkFrame):
    """Apresenta progresso e ações de execução."""

    def __init__(self, master: ctk.CTkBaseClass, iniciar: Callable[[], None], cancelar: Callable[[], None]) -> None:
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.barra = ctk.CTkProgressBar(self, mode="determinate", progress_color=COR_INFO, height=10)
        self.barra.set(0)
        self.barra.grid(row=0, column=0, columnspan=2, padx=14, pady=(14, 6), sticky="ew")
        self.status = ctk.CTkLabel(self, text="Pronto para iniciar", text_color=COR_TEXTO_SECUNDARIO, anchor="w",
                                    font=ctk.CTkFont(size=12))
        self.status.grid(row=1, column=0, padx=14, sticky="w")
        botoes = ctk.CTkFrame(self, fg_color="transparent")
        botoes.grid(row=1, column=1, padx=14, pady=(0, 14), sticky="e")
        self.iniciar = ctk.CTkButton(botoes, text="Iniciar Organização", height=38,
                                       fg_color=COR_PRIMARIA, hover_color="#2563EB", command=iniciar)
        self.iniciar.pack(side="left", padx=(0, 8))
        self.cancelar = ctk.CTkButton(botoes, text="Cancelar", height=38, state="disabled",
                                        fg_color=COR_ALERTA, hover_color="#D97706", command=cancelar)
        self.cancelar.pack(side="left")

    def atualizar_progresso(self, valor: float, total: int) -> None:
        """Atualiza a barra e o contador X/Y de arquivos processados."""
        valor = max(0.0, min(1.0, valor))
        self.barra.set(valor)
        processados = min(total, int(valor * total)) if total else 0
        self.status.configure(text=f"{processados}/{total} arquivos ({int(valor*100)}%)",
                              text_color=COR_INFO)

    def atualizar_status(self, texto: str, cor: str = COR_TEXTO_SECUNDARIO) -> None:
        """Atualiza o estado textual da execução."""
        self.status.configure(text=texto, text_color=cor)
        # Mapeia cor semantica para cor da barra
        if cor == COR_SUCESSO:
            self.barra.configure(progress_color=COR_SUCESSO)
        elif cor == COR_ALERTA:
            self.barra.configure(progress_color=COR_ALERTA)
        elif cor == COR_ERRO:
            self.barra.configure(progress_color=COR_ERRO)
        else:
            self.barra.configure(progress_color=COR_INFO)


class StatisticsFrame(ctk.CTkFrame):
    """Exibe o resumo da última execução."""

    def __init__(self, master: ctk.CTkBaseClass) -> None:
        super().__init__(master, fg_color=COR_CARTAO, border_width=1, border_color=COR_BORDA, corner_radius=12)
        self.grid_columnconfigure(0, weight=1)
        self.texto = ctk.CTkLabel(self, text="Nenhuma execução concluída.", anchor="w")
        self.texto.grid(row=0, column=0, padx=14, pady=10, sticky="ew")
        self.abrir = ctk.CTkButton(self, text="Abrir Pasta de Destino", width=170, state="disabled", command=self._abrir)
        self.abrir.grid(row=0, column=1, padx=14, pady=8)
        self.destino = ""

    def atualizar(self, estatisticas: list[organizador.Estatisticas] | organizador.Estatisticas,
                  duracao: float) -> None:
        """Atualiza as estatísticas apresentadas ao usuário."""
        if isinstance(estatisticas, dict):
            estatisticas = [estatisticas]
        movidos = sum(e["movidos"] for e in estatisticas)
        sucessos = sum(e["resumos_sucesso"] for e in estatisticas)
        falhas = sum(e["resumos_falha"] for e in estatisticas)
        contagem: dict[str, int] = {}
        for e in estatisticas:
            for cat, qtd in e["por_categoria"].items():
                contagem[cat] = contagem.get(cat, 0) + qtd
        categorias = ", ".join(f"{k}: {v}" for k, v in contagem.items()) or "nenhuma"
        plural = "s" if len(estatisticas) > 1 else ""
        self.texto.configure(text=(f"{len(estatisticas)} pasta{plural} | Tempo: {duracao:.1f}s | Movidos: {movidos} | "
                                   f"Resumos: {sucessos} OK, {falhas} falha(s) | "
                                   f"Categorias: {categorias}"))
        self.destino = estatisticas[-1]["destino"] if estatisticas else ""
        self.abrir.configure(state="normal" if self.destino else "disabled")

    def _abrir(self) -> None:
        """Abre a pasta de destino no gerenciador de arquivos."""
        if os.name == "nt":
            os.startfile(self.destino)
        elif os.name == "posix":
            subprocess.Popen(["xdg-open", self.destino])
        else:
            webbrowser.open(Path(self.destino).as_uri())


class OrganizadorApp(ctk.CTk):
    """Janela principal do organizador."""

    def __init__(self) -> None:
        # No Windows, define o AppUserModelID do processo antes de criar a
        # janela raiz para garantir o agrupamento correto do ícone na
        # barra de tarefas e evitar instâncias duplicadas ou telas em branco.
        if sys.platform == "win32":
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "meuorganizador.app"
                )
            except Exception:
                pass

        super().__init__()
        self.title("Organizador Inteligente")
        self.geometry("960x820")
        self.minsize(800, 700)
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        organizador.carregar_ambiente()
        self.estado = "ocioso"
        self.total_arquivos = 0
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
        self.pasta_frame = DirectorySelectionFrame(self, self.pasta_var)
        self.pasta_frame.grid(row=1, column=0, padx=28, pady=8, sticky="ew")
        self.config_frame = SettingsFrame(self, self.chave_var, self.modelo_var, self.ia_var, self.teste_var, self.max_files_var, self._abrir_chaves_groq)
        self.config_frame.grid(row=2, column=0, padx=28, pady=8, sticky="ew")
        self.log_frame = ConsoleLogFrame(self)
        self.log_frame.grid(row=3, column=0, padx=28, pady=8, sticky="nsew")
        self.estatisticas_frame = StatisticsFrame(self)
        self.estatisticas_frame.grid(row=4, column=0, padx=28, pady=8, sticky="ew")
        self.controles = ExecutionControlFrame(self, self._iniciar, self._cancelar)
        self.controles.grid(row=5, column=0, padx=28, pady=(8, 24), sticky="ew")

    def _abrir_chaves_groq(self) -> None:
        webbrowser.open_new_tab(organizador.URL_CHAVES_GROQ)

    def _definir_estado_interface(self, estado: str) -> None:
        """Atualiza o estado de todos os controles da aplicação."""
        self.pasta_frame.definir_estado(estado)
        self.config_frame.definir_estado(estado)
        self.controles.iniciar.configure(state=estado)

    def _salvar_chave(self) -> bool:
        chave = self.chave_var.get().strip()
        if not organizador.salvar_chave_api(chave):
            messagebox.showerror("Falha ao salvar chave", "Não foi possível salvar a chave da API.")
            return False
        return True

    def _iniciar(self) -> None:
        pastas = self.pasta_frame.pastas_selecionadas()
        if not pastas:
            messagebox.showwarning("Nenhuma pasta", "Selecione ou configure pastas antes de iniciar.")
            return
        try:
            max_files = validar_max_files(self.max_files_var.get())
        except ValueError as erro:
            messagebox.showwarning("Limite inválido", str(erro))
            return
        # max_files limita arquivos por execucao (regra global; documentada no codigo)
        resumo: list[str] = []
        total_geral = 0
        for p in pastas:
            try:
                qtd = len(organizador.listar_arquivos_elegiveis(p, None))
            except (ValueError, OSError):
                qtd = 0
            total_geral += qtd
            nome = Path(p).name or p
            resumo.append(f"  {nome}: {qtd} arquivo(s)")
        if total_geral == 0:
            messagebox.showwarning("Nenhum arquivo", "Nenhum arquivo elegivel encontrado nas pastas selecionadas.")
            return
        msg = f"Resumo das pastas a organizar:\n\n" + "\n".join(resumo) + f"\n\nTotal: {total_geral} arquivo(s)\n\nContinuar?"
        if not messagebox.askyesno("Confirmar organização", msg):
            return
        if not self._salvar_chave():
            return
        self.estado = "executando"
        self.total_arquivos = total_geral
        self.pastas_para_organizar = pastas
        self.pasta_idx = 0
        self.cancelamento.clear()
        self._definir_estado_interface("disabled")
        self.controles.cancelar.configure(state="normal")
        self.controles.atualizar_progresso(0.0, self.total_arquivos)
        self.controles.atualizar_status(f"Processando 0/{len(pastas)} pastas...", COR_INFO)
        threading.Thread(target=self._executar, daemon=True).start()

    def _executar(self) -> None:
        dry_run = self.teste_var.get()
        no_ai = not self.ia_var.get()
        modelo = self.modelo_var.get()
        max_files = self.max_files_var.get().strip()
        max_files_val = validar_max_files(max_files)
        logger = GuiLogger(self.eventos)
        inicio = datetime.now()
        resultados = []
        try:
            for idx, pasta in enumerate(self.pastas_para_organizar, 1):
                if self.cancelamento.is_set():
                    raise organizador.OperacaoCancelada
                self.pasta_idx = idx
                self.eventos.put(("log", f"[{datetime.now().strftime('%H:%M:%S')}] INFO: Iniciando pasta {idx}/{len(self.pastas_para_organizar)}: {pasta}"))
                # max_files e regra global: aplica apenas na primeira pasta para respeitar o limite
                limite = max_files_val if idx == 1 else None
                resultado = organizador.organizar_pasta(
                    pasta, dry_run=dry_run, no_ai=no_ai, model=modelo, max_files=limite,
                    logger=logger,
                    progresso=lambda valor: self.eventos.put(("progresso", valor)),
                    cancel_event=self.cancelamento,
                )
                resultados.append(resultado)
            self.eventos.put(("estatisticas", (resultados, (datetime.now() - inicio).total_seconds())))
            self.eventos.put(("fim", "Organizacao concluida."))
        except organizador.OperacaoCancelada:
            self.eventos.put(("cancelado", "Operacao cancelada."))
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
                    self.controles.atualizar_progresso(valor, self.total_arquivos)
                elif tipo == "estatisticas":
                    self.estatisticas_frame.atualizar(valor[0], valor[1])
                elif tipo in {"fim", "cancelado", "erro"}:
                    self.estado = "ocioso" if tipo != "erro" else "erro"
                    self._adicionar_log(valor if tipo != "erro" else f"ERRO: {valor}")
                    self._definir_estado_interface("normal")
                    self.controles.cancelar.configure(state="disabled")
                    if tipo == "fim":
                        self.controles.atualizar_status("Concluído", COR_SUCESSO)
                    elif tipo == "cancelado":
                        self.controles.atualizar_status("Cancelado", COR_ALERTA)
                    else:
                        self.controles.atualizar_status("Erro", COR_ERRO)
                    if tipo == "erro":
                        messagebox.showerror("Erro na organização", valor)
        except queue.Empty:
            pass
        self.after(100, self._processar_eventos)


if __name__ == "__main__":
    sys.setrecursionlimit(10000)
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")
    app = OrganizadorApp()
    app.mainloop()
