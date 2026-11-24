# Pipeline de Análise de Dados de Supermercado

Projeto em Python para análise executiva de dados de supermercado. O pipeline usa Pandas e Matplotlib, aplica herança multinível e registra a limpeza de dados ausentes e outliers.

## Arquitetura

- `AnalisadorDados`: carga dos arquivos CSV, remoção de outliers pelo IQR e exportação de relatórios.
- `AnalisadorSupermercado`: limpeza dos produtos e vendas, auditoria e faturamento por categoria.
- `AnalisadorExecutivo`: KPIs por filial, datas e dia da semana, série temporal e painel executivo.

## Estrutura

```text
projeto_supermercado/
├── dados/
│   ├── produtos.csv
│   └── vendas.csv
├── relatorios/
├── src/
│   └── analisador.py
├── main.py
├── README.md
├── requirements.txt
└── .gitignore
```

## Como executar

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

## Relatórios gerados

O script gera em `relatorios/`:

- `faturamento_por_categoria.csv`
- `kpis_por_filial.csv`
- `auditoria_limpeza.csv`
- `faturamento_dia_semana.csv`
- `grafico_faturamento.png`
- `painel_executivo.png`
