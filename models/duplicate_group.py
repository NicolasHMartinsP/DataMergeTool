from dataclasses import dataclass
from typing import List
from models.entity import FornecedorEntity

@dataclass
class DuplicateGroup:
    nome: str
    mestre: FornecedorEntity
    duplicados: List[FornecedorEntity]