from dataclasses import dataclass
from typing import Optional

@dataclass
class FornecedorEntity:
    id: str
    nome: str
    contato: Optional[str] = None
    pix: Optional[str] = None
    fornecedor_destino: Optional[str] = None
    movimentacoes: int = 0