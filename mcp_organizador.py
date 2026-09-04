from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("OrganizadorInteligenteTools")

BASE_DIR = Path(__file__).parent.resolve()

@mcp.tool()
def ler_contexto() -> str:
    caminho = BASE_DIR / "contexto.txt"
    if caminho.exists():
        return caminho.read_text(encoding="utf-8")
    return "Arquivo contexto.txt não encontrado."

@mcp.tool()
def atualizar_contexto(novo_conteudo: str) -> str:
    caminho = BASE_DIR / "contexto.txt"
    caminho.write_text(novo_conteudo, encoding="utf-8")
    return "contexto.txt atualizado com sucesso!"

@mcp.tool()
def listar_arquivos_dist() -> str:
    pasta_dist = BASE_DIR / "dist"
    if not pasta_dist.exists():
        return "A pasta dist/ ainda não foi criada."
    
    arquivos = [f.name for f in pasta_dist.iterdir() if f.is_file()]
    if not arquivos:
        return "A pasta dist/ está vazia."
    
    return f"Arquivos encontrados em dist/: {', '.join(arquivos)}"

if __name__ == "__main__":
    mcp.run()
