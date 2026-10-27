from datetime import date
from decimal import Decimal

import pytest

from planejador.modelos import Conta, TipoTransacao, Transacao


def nova(tipo, valor, categoria="Sem categoria", dia=date(2026, 10, 5)):
    return Transacao(dia, "teste", tipo, valor, categoria)


def test_saldo_apos_entrada_e_saida():
    conta = Conta("henrique")
    conta.adicionar_transacao(nova(TipoTransacao.ENTRADA, 1000))
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 250.50))
    assert conta.saldo == Decimal("749.50")


def test_saldo_inicial_entra_no_calculo():
    conta = Conta("henrique", saldo_inicial=100)
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 30))
    assert conta.saldo == Decimal("70.00")


def test_float_nao_gera_erro_de_precisao():
    conta = Conta("henrique")
    conta.adicionar_transacao(nova(TipoTransacao.ENTRADA, 0.1))
    conta.adicionar_transacao(nova(TipoTransacao.ENTRADA, 0.2))
    assert conta.saldo == Decimal("0.30")


def test_tipo_aceita_convencao_antiga_de_1_e_0():
    assert nova(True, 10).tipo == TipoTransacao.ENTRADA
    assert nova(0, 10).tipo == TipoTransacao.SAIDA


@pytest.mark.parametrize("valor", [0, -5])
def test_valor_nao_positivo_e_rejeitado(valor):
    with pytest.raises(ValueError):
        nova(TipoTransacao.SAIDA, valor)


def test_reserva_negativa_e_rejeitada():
    with pytest.raises(ValueError):
        Conta("henrique", reserva=-1)


def test_gastos_por_categoria_filtra_mes_e_ignora_entradas():
    conta = Conta("henrique")
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 50, "Mercado"))
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 200, "Moradia"))
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 30, "Mercado"))
    conta.adicionar_transacao(nova(TipoTransacao.SAIDA, 99, "Lazer", dia=date(2026, 9, 1)))
    conta.adicionar_transacao(nova(TipoTransacao.ENTRADA, 3000, "Salário"))

    gastos = conta.gastos_por_categoria(ano=2026, mes=10)

    assert gastos == {"Moradia": Decimal("200.00"), "Mercado": Decimal("80.00")}
    assert list(gastos) == ["Moradia", "Mercado"]  # ordenado do maior para o menor
    assert conta.total_entradas(2026, 10) == Decimal("3000.00")
    assert conta.total_saidas(2026, 10) == Decimal("280.00")