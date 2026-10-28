"""Leitor de CSV de extrato de conta corrente.

Formato esperado: algumas linhas de metadados (conta, período, saldo), uma linha
em branco e depois o cabeçalho `Data Lançamento;Histórico;Descrição;Valor;Saldo`,
com separador ";" e valores no padrão brasileiro (1.234,56). O saldo informado em
cada linha é o saldo logo após aquele lançamento.
"""

from __future__ import annotations

import csv
import hashlib
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import NamedTuple

from .modelos import TipoTransacao, Transacao, para_dinheiro

COLUNAS_ESPERADAS = ["data lancamento", "historico", "descricao", "valor", "saldo"]


class _Linha(NamedTuple):
    numero: int
    data: date
    historico: str
    descricao: str
    valor: Decimal  # com sinal: negativo = saída
    saldo: Decimal  # saldo após o lançamento


@dataclass
class ResultadoImportacao:
    transacoes: list[Transacao]  # em ordem cronológica
    saldo_inicial: Decimal  # saldo imediatamente antes da primeira transação
    saldo_final: Decimal
    avisos: list[str] = field(default_factory=list)


# --- conversões -------------------------------------------------------------


def parse_valor_br(texto: str) -> Decimal:
    """'-3.900,00' -> Decimal('-3900.00'). Aceita 'R$' e espaços."""
    limpo = "".join(texto.split()).replace("R$", "").replace(".", "").replace(",", ".")
    try:
        return para_dinheiro(Decimal(limpo))
    except InvalidOperation as erro:
        raise ValueError(f"valor inválido: {texto!r}") from erro


def _parse_data(texto: str) -> date:
    try:
        return datetime.strptime(texto.strip(), "%d/%m/%Y").date()
    except ValueError as erro:
        raise ValueError(f"data inválida: {texto!r}") from erro


def _normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, para comparar cabeçalhos com segurança."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return sem_acento.strip().lower()


def _ler_texto(caminho: Path) -> str:
    dados = caminho.read_bytes()
    try:
        return dados.decode("utf-8-sig")
    except UnicodeDecodeError:
        return dados.decode("latin-1")  # exports antigos de bancos costumam usar latin-1


def _achar_cabecalho(linhas: list[str]) -> int:
    for indice, linha in enumerate(linhas):
        colunas = [_normalizar(c) for c in linha.split(";")]
        if colunas[: len(COLUNAS_ESPERADAS)] == COLUNAS_ESPERADAS:
            return indice
    raise ValueError(
        "Cabeçalho não encontrado. Esperado: Data Lançamento;Histórico;Descrição;Valor;Saldo"
    )


def _gerar_id(linha: _Linha, ocorrencia: int) -> str:
    """Identificador estável: o mesmo lançamento gera sempre o mesmo id.

    O saldo após o lançamento torna a chave praticamente única; `ocorrencia`
    diferencia linhas totalmente idênticas dentro do mesmo arquivo.
    """
    base = "|".join(
        [
            linha.data.isoformat(),
            linha.historico,
            linha.descricao,
            str(linha.valor),
            str(linha.saldo),
            str(ocorrencia),
        ]
    )
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def _verificar_saldos(linhas: list[_Linha]) -> list[str]:
    """Confere se cada saldo = saldo anterior + valor (detecta linhas perdidas ou mal lidas)."""
    avisos = []
    for anterior, atual in zip(linhas, linhas[1:]):
        esperado = anterior.saldo + atual.valor
        if esperado != atual.saldo:
            avisos.append(
                f"Linha {atual.numero}: saldo inconsistente "
                f"(esperado {esperado}, arquivo informa {atual.saldo})."
            )
    return avisos


# --- leitura principal ------------------------------------------------------


def ler_extrato(caminho: str | Path) -> ResultadoImportacao:
    linhas_texto = _ler_texto(Path(caminho)).splitlines()
    inicio = _achar_cabecalho(linhas_texto)

    avisos: list[str] = []
    linhas: list[_Linha] = []
    leitor = csv.reader(linhas_texto[inicio + 1 :], delimiter=";")
    for numero, campos in enumerate(leitor, start=inicio + 2):
        if not any(campo.strip() for campo in campos):
            continue  # linha em branco
        if len(campos) < len(COLUNAS_ESPERADAS):
            raise ValueError(
                f"Linha {numero}: esperadas {len(COLUNAS_ESPERADAS)} colunas, "
                f"encontradas {len(campos)}."
            )
        try:
            linha = _Linha(
                numero=numero,
                data=_parse_data(campos[0]),
                historico=campos[1].strip(),
                descricao=campos[2].strip(),
                valor=parse_valor_br(campos[3]),
                saldo=parse_valor_br(campos[4]),
            )
        except ValueError as erro:
            raise ValueError(f"Linha {numero}: {erro}") from erro
        linhas.append(linha)

    if not linhas:
        raise ValueError("Nenhum lançamento encontrado após o cabeçalho.")

    # O arquivo costuma vir do mais recente para o mais antigo; trabalhamos em ordem cronológica.
    if linhas[0].data > linhas[-1].data:
        linhas.reverse()

    avisos.extend(_verificar_saldos(linhas))

    transacoes: list[Transacao] = []
    ocorrencias: dict[tuple, int] = {}
    for linha in linhas:
        if linha.valor == 0:
            avisos.append(f"Linha {linha.numero}: lançamento de valor zero ignorado.")
            continue
        chave = (linha.data, linha.historico, linha.descricao, linha.valor, linha.saldo)
        ocorrencias[chave] = ocorrencias.get(chave, 0) + 1
        descricao = (
            f"{linha.historico}: {linha.descricao}"
            if linha.historico and linha.descricao
            else linha.historico or linha.descricao
        )
        transacoes.append(
            Transacao(
                data=linha.data,
                descricao=descricao,
                tipo=TipoTransacao.ENTRADA if linha.valor > 0 else TipoTransacao.SAIDA,
                valor=abs(linha.valor),
                id=_gerar_id(linha, ocorrencias[chave] - 1),
            )
        )

    primeira, ultima = linhas[0], linhas[-1]
    return ResultadoImportacao(
        transacoes=transacoes,
        saldo_inicial=primeira.saldo - primeira.valor,
        saldo_final=ultima.saldo,
        avisos=avisos,
    )