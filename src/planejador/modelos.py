"""Modelos de domínio do planejador financeiro."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from enum import IntEnum

CENTAVOS = Decimal("0.01")
SEM_CATEGORIA = "Sem categoria"


def para_dinheiro(valor) -> Decimal:
    """Converte para Decimal com 2 casas decimais.

    Passa por str() para evitar o ruído de float: Decimal(0.1) vira
    0.1000000000000000055..., enquanto Decimal(str(0.1)) vira 0.1.
    """
    return Decimal(str(valor)).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


class TipoTransacao(IntEnum):
    """Mantém a convenção original: 1 = entrada, 0 = saída.

    Como é IntEnum, TipoTransacao(True) e TipoTransacao(0) continuam funcionando.
    """

    SAIDA = 0
    ENTRADA = 1


@dataclass
class Transacao:
    data: date
    descricao: str
    tipo: TipoTransacao
    valor: Decimal
    categoria: str = SEM_CATEGORIA
    fixo: bool = False  # marcação manual de gasto fixo
    id: str | None = None  # identificador estável gerado na importação (evita duplicatas)

    def __post_init__(self):
        self.tipo = TipoTransacao(self.tipo)
        self.valor = para_dinheiro(self.valor)
        if self.valor <= 0:
            raise ValueError("O valor deve ser positivo; o sinal vem do tipo.")

    @property
    def valor_assinado(self) -> Decimal:
        """Positivo para entrada, negativo para saída."""
        return self.valor if self.tipo == TipoTransacao.ENTRADA else -self.valor


class Conta:
    def __init__(self, usuario: str, saldo_inicial=0, reserva=0):
        self.usuario = usuario
        self.saldo_inicial = para_dinheiro(saldo_inicial)
        self.reserva = para_dinheiro(reserva)  # quanto já está guardado
        if self.reserva < 0:
            raise ValueError("A reserva não pode ser negativa.")
        self.transacoes: list[Transacao] = []

    # --- escrita -----------------------------------------------------------

    def adicionar_transacao(self, transacao: Transacao) -> None:
        self.transacoes.append(transacao)

    def adicionar_transacoes(self, transacoes) -> int:
        """Adiciona várias transações, ignorando as que já existem (mesmo id).

        Retorna quantas eram novas. Reimportar o mesmo arquivo retorna 0.
        """
        ids_existentes = {t.id for t in self.transacoes if t.id is not None}
        novas = 0
        for transacao in transacoes:
            if transacao.id is not None:
                if transacao.id in ids_existentes:
                    continue
                ids_existentes.add(transacao.id)
            self.transacoes.append(transacao)
            novas += 1
        return novas

    # --- leitura -----------------------------------------------------------

    @property
    def saldo(self) -> Decimal:
        """Calculado a partir das transações: uma única fonte da verdade.

        Se uma transação for editada ou removida, o saldo continua correto.
        """
        return self.saldo_inicial + sum(
            (t.valor_assinado for t in self.transacoes), Decimal("0")
        )

    def _filtrar(self, tipo: TipoTransacao, ano: int | None, mes: int | None):
        for t in self.transacoes:
            if t.tipo != tipo:
                continue
            if ano is not None and t.data.year != ano:
                continue
            if mes is not None and t.data.month != mes:
                continue
            yield t

    def total_entradas(self, ano: int | None = None, mes: int | None = None) -> Decimal:
        return sum((t.valor for t in self._filtrar(TipoTransacao.ENTRADA, ano, mes)), Decimal("0"))

    def total_saidas(self, ano: int | None = None, mes: int | None = None) -> Decimal:
        return sum((t.valor for t in self._filtrar(TipoTransacao.SAIDA, ano, mes)), Decimal("0"))

    def gastos_por_categoria(
        self, ano: int | None = None, mes: int | None = None
    ) -> dict[str, Decimal]:
        """Soma das saídas por categoria, da maior para a menor."""
        totais: dict[str, Decimal] = {}
        for t in self._filtrar(TipoTransacao.SAIDA, ano, mes):
            totais[t.categoria] = totais.get(t.categoria, Decimal("0")) + t.valor
        return dict(sorted(totais.items(), key=lambda item: item[1], reverse=True))