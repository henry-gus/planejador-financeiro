"""Confere a leitura de um extrato real.

Uso (na raiz do projeto, com a .venv ativada):
    python scripts/verificar_extrato.py data/raw/SEU_ARQUIVO.csv

Tudo roda localmente e nada é enviado para fora.
"""

import sys
from collections import Counter
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from planejador.importador import _ler_texto, ler_extrato, parse_valor_br  # noqa: E402
from planejador.modelos import Conta  # noqa: E402


def saldo_do_cabecalho(caminho: Path) -> Decimal | None:
    """Procura a linha 'Saldo ;valor' nos metadados, antes da tabela."""
    for linha in _ler_texto(caminho).splitlines():
        campos = linha.split(";")
        primeiro = campos[0].strip().lower()
        if primeiro.startswith("data"):
            break
        if primeiro == "saldo" and len(campos) > 1:
            try:
                return parse_valor_br(campos[1])
            except ValueError:
                return None
    return None


def marca(ok: bool) -> str:
    return "OK       " if ok else "ATENÇÃO  "


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Uso: python scripts/verificar_extrato.py data/raw/SEU_ARQUIVO.csv")
    caminho = Path(sys.argv[1])
    r = ler_extrato(caminho)

    conta = Conta("verificacao", saldo_inicial=r.saldo_inicial)
    conta.adicionar_transacoes(r.transacoes)

    datas = [t.data for t in r.transacoes]
    print(f"Transações lidas : {len(r.transacoes)}")
    print(f"Período          : {min(datas):%d/%m/%Y} a {max(datas):%d/%m/%Y}")
    print(f"Saldo inicial    : {r.saldo_inicial}")
    print(f"Saldo final      : {r.saldo_final}")
    print()

    print("--- Verificações automáticas ---")
    print(marca(not r.avisos), "cadeia de saldos consistente (sem avisos)")
    for aviso in r.avisos:
        print("           ->", aviso)
    print(marca(conta.saldo == r.saldo_final), "saldo calculado pela Conta == saldo final do arquivo")
    ids = [t.id for t in r.transacoes]
    print(marca(len(set(ids)) == len(ids)), "ids únicos (nenhuma transação repetida)")
    cabecalho = saldo_do_cabecalho(caminho)
    if cabecalho is None:
        print("NÃO CHECADO", "saldo do cabeçalho do arquivo não encontrado")
    else:
        print(marca(cabecalho == r.saldo_final), f"saldo do cabeçalho ({cabecalho}) == saldo final")
    print()

    print("--- Totais por mês (compare com o app do banco) ---")
    meses = sorted({(t.data.year, t.data.month) for t in r.transacoes})
    for ano, mes in meses:
        print(
            f"{mes:02d}/{ano}  entradas {conta.total_entradas(ano, mes):>12}   "
            f"saídas {conta.total_saidas(ano, mes):>12}"
        )
    print()

    print("--- Tipos de lançamento encontrados ---")
    tipos = Counter(t.descricao.split(":")[0] for t in r.transacoes)
    for nome, qtd in tipos.most_common(10):
        print(f"{qtd:>5}  {nome}")


if __name__ == "__main__":
    main()