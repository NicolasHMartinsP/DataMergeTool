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

def aviso(mensagem):
    print(f"\033[93m{mensagem}\033[0m")

def erro(texto: str):
    print(f"[ERRO] {texto}")

def sucesso(texto: str):
    print(f"[SUCESSO] {texto}")