from dataclasses import dataclass

@dataclass
class Migration:
    origem: str
    destino: str
    quantidade_movimentacoes: int