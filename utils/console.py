import os

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_title(text: str):
    print("=" * 60)
    print(text.upper())
    print("=" * 60)
    print()

def print_separator():
    print("-" * 60)
    print()

def print_warning(message: str):
    print(f"\033[93m[AVISO] {message}\033[0m")

def print_error(text: str):
    print(f"\033[91m[ERRO] {text}\033[0m")

def print_success(text: str):
    print(f"\033[92m[SUCESSO] {text}\033[0m")