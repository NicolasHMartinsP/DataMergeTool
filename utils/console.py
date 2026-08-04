import os

def limpar_tela():
    os.system('cls' if os.name == 'nt' else 'clear')

def titulo(texto: str):
    print("=" * 60)
    print(texto.upper())
    print("=" * 60)
    print()

def separador():
    print("-" * 60)
    print()

def erro(texto: str):
    print(f"[ERRO] {texto}")

def sucesso(texto: str):
    print(f"[SUCESSO] {texto}")