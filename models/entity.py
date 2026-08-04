from dataclasses import dataclass, field
from typing import Optional, Dict

@dataclass
class FornecedorEntity:
    id: str
    nome: str
    contato: Optional[str] = None
    pix: Optional[str] = None
    fornecedor_destino: Optional[str] = None
    movimentacoes: int = 0
    # Novo: guarda de qual loja veio cada movimentação
    movimentacoes_por_loja: Dict[str, int] = field(default_factory=dict)