from dataclasses import dataclass
from typing import Optional

@dataclass
class FornecedorEntity:
    id: int
    nome: str
    contato: Optional[str] = None
    pix: Optional[str] = None
    fornecedor_destino: Optional[int] = None
    movimentacoes: int = 0