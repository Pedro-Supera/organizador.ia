#!/usr/bin/env python3
"""Worker que monitora mensagens MCP e entrega hand-offs a um comando local."""

from __future__ import annotations

import argparse
import asyncio
import json
import shlex
import subprocess
import sys
from collections.abc import Sequence

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def construir_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Monitora hand-offs do mailbox MCP.")
    parser.add_argument("--agent", default="cline", help="Agente que receberá as mensagens.")
    parser.add_argument("--interval", type=float, default=2.0, help="Intervalo de polling em segundos.")
    parser.add_argument("--once", action="store_true", help="Processa uma consulta e encerra.")
    parser.add_argument(
        "--handler",
        help="Comando local que receberá uma mensagem JSON pela entrada padrão; sem handler, apenas exibe mensagens.",
    )
    return parser


def executar_handler(comando: str, mensagem: dict[str, object]) -> bool:
    """Entrega uma mensagem ao comando configurado e retorna seu sucesso."""
    processo = subprocess.run(
        shlex.split(comando),
        input=json.dumps(mensagem, ensure_ascii=False),
        text=True,
        check=False,
    )
    return processo.returncode == 0


async def processar_mensagens(session: ClientSession, agente: str, handler: str | None) -> int:
    resultado = await session.call_tool("ler_mensagens", {"destinatario": agente})
    mensagens = json.loads(resultado.content[0].text)
    processadas = 0
    for mensagem in mensagens:
        print(json.dumps(mensagem, ensure_ascii=False), flush=True)
        sucesso = handler is None or executar_handler(handler, mensagem)
        if sucesso and handler is not None:
            await session.call_tool("marcar_mensagem_lida", {"mensagem_id": mensagem["id"]})
            processadas += 1
    return processadas


async def executar(args: argparse.Namespace) -> None:
    parametros = StdioServerParameters(command=sys.executable, args=["mcp_organizador.py"])
    async with stdio_client(parametros) as streams:
        async with ClientSession(*streams) as session:
            await session.initialize()
            while True:
                await processar_mensagens(session, args.agent, args.handler)
                if args.once:
                    return
                await asyncio.sleep(max(0.1, args.interval))


def main(argv: Sequence[str] | None = None) -> None:
    args = construir_parser().parse_args(argv)
    asyncio.run(executar(args))


if __name__ == "__main__":
    main()