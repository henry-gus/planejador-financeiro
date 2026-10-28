# Planejador Financeiro

Aplicação em Python para organização financeira pessoal: importar extratos e faturas em CSV, categorizar transações, acompanhar gastos fixos, reserva de emergência, saldo livre e objetivos.

> **Status:** em desenvolvimento. Esta versão contém o domínio (modelos) e o importador de extrato em CSV.

## Princípios

- **Privacidade primeiro.** Todos os dados ficam na máquina do usuário. O programa não faz chamadas a APIs externas nem a modelos de linguagem.
- **Núcleo independente da interface.** Toda a lógica fica em `src/planejador/` e não conhece telas. A interface (a ser construída) apenas chama essas funções, o que permite trocar ou aprimorar o front-end sem alterar o que já foi testado.
- **Valores monetários com `Decimal`**, para evitar erros de ponto flutuante (`0.1 + 0.2`).

## O que existe hoje

| Componente | Descrição |
|---|---|
| `TipoTransacao` | Enum de entrada (`1`) e saída (`0`) |
| `Transacao` | Data, descrição, tipo, valor, categoria, marcação de gasto fixo e id estável, com validação (valor positivo) |
| `Conta` | Saldo calculado a partir das transações, totais de entradas e saídas, gastos por categoria (filtro por ano e mês) e importação sem duplicatas |
| `ler_extrato` | Lê o CSV de extrato de conta corrente (padrão brasileiro), valida a coluna de saldo e gera ids para evitar duplicatas ao reimportar |

## Estrutura

```
planejador-financeiro/
├── pytest.ini
├── requirements.txt
└── src/
    └── planejador/
        ├── __init__.py
        ├── modelos.py
        └── importador.py
```

## Como rodar

Requer Python 3.10 ou superior.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Testes

A suíte de testes é mantida apenas localmente: a pasta `tests/` está no `.gitignore` e não é versionada.

## Dados pessoais e Git

Extratos reais nunca devem ser versionados. Coloque-os em `data/raw/`. O `.gitignore` bloqueia a pasta `data/` (exceto `data/sample/`, reservada para exemplos sintéticos), qualquer arquivo `.csv` fora de `data/sample/`, bancos locais, arquivos `.env` e a pasta `tests/`.

## Roadmap

- [x] Modelos de domínio (`Transacao`, `Conta`)
- [x] Importador de CSV de extrato, sem duplicar transações
- [ ] Importador de CSV de fatura de cartão
- [ ] Persistência local em SQLite
- [ ] Categorias com grupos (essencial, discricionário, poupança) e categorização manual com regras aprendidas
- [ ] Cálculos: gastos fixos, reserva de emergência e saldo livre
- [ ] Objetivos financeiros (valor-alvo, prazo e aporte mensal necessário)
- [ ] Gráficos de gastos por categoria e evolução mensal
- [ ] Interface web local