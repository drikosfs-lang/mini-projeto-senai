from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class AnalisadorDados:
    def __init__(self, pasta_saida: str | Path) -> None:
        self.pasta_saida = str(pasta_saida)
        Path(self.pasta_saida).mkdir(parents=True, exist_ok=True)

    def carregar_csv(self, caminho_arquivo: str | Path) -> pd.DataFrame:
        dataframe = pd.read_csv(caminho_arquivo)
        print(
            f"Arquivo '{caminho_arquivo}' carregado "
            f"({dataframe.shape[0]} linhas)."
        )
        return dataframe

    def remover_outliers_iqr(
        self,
        df: pd.DataFrame,
        coluna: str,
        minimo_valido: float = 0,
    ) -> pd.Series:
        serie = df[coluna].copy()
        valores_validos = serie[serie > minimo_valido]
        primeiro_quartil = valores_validos.quantile(0.25)
        terceiro_quartil = valores_validos.quantile(0.75)
        intervalo_interquartil = terceiro_quartil - primeiro_quartil
        limite_superior = terceiro_quartil + 1.5 * intervalo_interquartil
        condicao_invalida = (serie <= minimo_valido) | (serie > limite_superior)
        quantidade_invalidos = int(condicao_invalida.sum())
        serie.loc[condicao_invalida] = np.nan
        print(
            f"[{coluna}] Valores inválidos/outliers convertidos em NaN: "
            f"{quantidade_invalidos}"
        )
        return serie

    def exportar_csv(self, dataframe: pd.DataFrame, nome_arquivo: str) -> None:
        caminho_completo = Path(self.pasta_saida) / nome_arquivo
        caminho_completo.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(caminho_completo, index=False, encoding="utf-8-sig")
        print(f"Relatório CSV salvo em: {caminho_completo}")


class AnalisadorSupermercado(AnalisadorDados):
    def __init__(
        self,
        caminho_produtos: str | Path,
        caminho_vendas: str | Path,
        pasta_saida: str | Path,
    ) -> None:
        super().__init__(pasta_saida)
        self.caminho_produtos = str(caminho_produtos)
        self.caminho_vendas = str(caminho_vendas)
        self.df_completo: pd.DataFrame | None = None
        self.logs_limpeza: list[dict[str, Any]] = []

    def _registrar_log(
        self,
        tabela: str,
        id_coluna: str,
        df_antes: pd.DataFrame,
        df_depois: pd.DataFrame,
        coluna: str,
    ) -> None:
        alterados = df_antes[coluna].isna() | (
            df_antes[coluna] != df_depois[coluna]
        )
        for indice in df_antes.index[alterados]:
            self.logs_limpeza.append(
                {
                    "tabela": tabela,
                    "id_registro": df_antes.at[indice, id_coluna],
                    "coluna": coluna,
                    "valor_original": df_antes.at[indice, coluna],
                    "valor_corrigido": df_depois.at[indice, coluna],
                }
            )

    def limpar_produtos(self, df_produtos: pd.DataFrame) -> pd.DataFrame:
        df = df_produtos.copy()
        preco_original = df["preco_unitario"].copy()
        df["preco_unitario"] = self.remover_outliers_iqr(
            df, "preco_unitario", minimo_valido=0
        )
        medianas_categoria = df.groupby("categoria")["preco_unitario"].transform(
            "median"
        )
        df["preco_unitario"] = (
            df["preco_unitario"].fillna(medianas_categoria).round(2)
        )

        if df["preco_unitario"].isna().any():
            categorias_sem_preco = df.loc[
                df["preco_unitario"].isna(), "categoria"
            ].unique()
            raise ValueError(
                "Não foi possível imputar preços para as categorias: "
                f"{categorias_sem_preco.tolist()}"
            )

        self._registrar_log(
            "produtos", "product_id", df_produtos, df, "preco_unitario"
        )
        return df

    def limpar_vendas(self, df_vendas: pd.DataFrame) -> pd.DataFrame:
        df = df_vendas.copy()
        quantidade_original = df["quantidade"].copy()
        df["quantidade"] = self.remover_outliers_iqr(
            df, "quantidade", minimo_valido=0
        )
        mediana_quantidade = df["quantidade"].median()
        if pd.isna(mediana_quantidade):
            raise ValueError("Não há quantidades válidas para calcular a mediana.")
        df["quantidade"] = df["quantidade"].fillna(mediana_quantidade).astype(int)

        self._registrar_log("vendas", "venda_id", df_vendas, df, "quantidade")
        return df

    def preparar_dados(self) -> None:
        self.logs_limpeza = []
        df_produtos_bruto = self.carregar_csv(self.caminho_produtos)
        df_vendas_bruto = self.carregar_csv(self.caminho_vendas)
        df_produtos_limpo = self.limpar_produtos(df_produtos_bruto)
        df_vendas_limpo = self.limpar_vendas(df_vendas_bruto)

        self.df_completo = pd.merge(
            df_vendas_limpo,
            df_produtos_limpo,
            on="product_id",
            how="left",
            validate="many_to_one",
        )
        self.df_completo["valor_total"] = (
            self.df_completo["quantidade"] * self.df_completo["preco_unitario"]
        )
        valores_ausentes = self.df_completo.isna().sum()
        if valores_ausentes.any():
            raise ValueError(
                "Há valores ausentes após a limpeza: "
                f"{valores_ausentes[valores_ausentes > 0].to_dict()}"
            )
        print("Verificação de qualidade: nenhuma célula ausente após a limpeza.")

    def faturamento_por_categoria(self) -> pd.DataFrame:
        if self.df_completo is None:
            raise ValueError("Execute preparar_dados() antes de gerar métricas.")
        resumo = (
            self.df_completo.groupby("categoria", as_index=False)["valor_total"]
            .sum()
            .rename(
                columns={
                    "categoria": "Categoria",
                    "valor_total": "Faturamento_Total",
                }
            )
            .sort_values(by="Faturamento_Total", ascending=False)
        )
        resumo["Faturamento_Total"] = resumo["Faturamento_Total"].round(2)
        return resumo

    def gerar_grafico_categorias(self, df_resumo: pd.DataFrame) -> None:
        plt.figure(figsize=(10, 6))
        plt.barh(
            df_resumo["Categoria"],
            df_resumo["Faturamento_Total"],
            color="#2b5c8f",
        )
        plt.xlabel("Faturamento Total (R$)")
        plt.title("Faturamento por Categoria - Supermercado (Dados Tratados)")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        caminho_imagem = Path(self.pasta_saida) / "grafico_faturamento.png"
        plt.savefig(caminho_imagem, dpi=300)
        plt.close()
        print(f"Gráfico salvo em: {caminho_imagem}")

    def exportar_auditoria(self) -> pd.DataFrame:
        colunas = [
            "tabela",
            "id_registro",
            "coluna",
            "valor_original",
            "valor_corrigido",
        ]
        auditoria = pd.DataFrame(self.logs_limpeza, columns=colunas)
        self.exportar_csv(auditoria, "auditoria_limpeza.csv")
        return auditoria


class AnalisadorExecutivo(AnalisadorSupermercado):
    def __init__(
        self,
        caminho_produtos: str | Path,
        caminho_vendas: str | Path,
        pasta_saida: str | Path,
        meta_faturamento_filial: float = 7000.0,
    ) -> None:
        super().__init__(caminho_produtos, caminho_vendas, pasta_saida)
        self.meta_faturamento_filial = meta_faturamento_filial

    def preparar_dados(self) -> None:
        super().preparar_dados()
        if self.df_completo is None:
            raise ValueError("Os dados preparados não estão disponíveis.")

        self.df_completo["data_venda"] = pd.to_datetime(
            self.df_completo["data_venda"], errors="coerce"
        )
        if self.df_completo["data_venda"].isna().any():
            raise ValueError("Existem datas de venda inválidas após a conversão.")

        dias_portugues = {
            0: "Segunda-feira",
            1: "Terça-feira",
            2: "Quarta-feira",
            3: "Quinta-feira",
            4: "Sexta-feira",
            5: "Sábado",
            6: "Domingo",
        }
        self.df_completo["dia_semana"] = self.df_completo[
            "data_venda"
        ].dt.dayofweek.map(dias_portugues)

    def kpis_por_filial(self) -> pd.DataFrame:
        if self.df_completo is None:
            raise ValueError("Execute preparar_dados() antes de calcular os KPIs.")

        resumo = (
            self.df_completo.groupby("filial", as_index=False)
            .agg(
                Qtd_Vendas=("venda_id", "count"),
                Itens_Vendidos=("quantidade", "sum"),
                Faturamento_Total=("valor_total", "sum"),
                Ticket_Medio=("valor_total", "mean"),
            )
            .sort_values("Faturamento_Total", ascending=False)
        )
        faturamento_total_rede = resumo["Faturamento_Total"].sum()
        resumo["Participacao_%"] = (
            resumo["Faturamento_Total"] / faturamento_total_rede * 100
        ).round(2)
        resumo["Atingiu_Meta"] = np.where(
            resumo["Faturamento_Total"] >= self.meta_faturamento_filial,
            "Sim",
            "Não",
        )
        resumo["Faturamento_Total"] = resumo["Faturamento_Total"].round(2)
        resumo["Ticket_Medio"] = resumo["Ticket_Medio"].round(2)
        return resumo

    def faturamento_diario(self) -> pd.DataFrame:
        if self.df_completo is None:
            raise ValueError("Execute preparar_dados() antes de calcular a série temporal.")

        diario = (
            self.df_completo.groupby("data_venda", as_index=False)["valor_total"]
            .sum()
            .sort_values("data_venda")
        )
        diario["valor_total"] = diario["valor_total"].round(2)
        diario["Media_Movel_3d"] = diario["valor_total"].rolling(
            window=3, min_periods=1
        ).mean().round(2)
        return diario

    def faturamento_por_dia_semana(self) -> pd.DataFrame:
        if self.df_completo is None:
            raise ValueError("Execute preparar_dados() antes de calcular por dia da semana.")

        ordem_dias = [
            "Segunda-feira", "Terça-feira", "Quarta-feira", "Quinta-feira",
            "Sexta-feira", "Sábado", "Domingo",
        ]
        resumo = (
            self.df_completo.groupby("dia_semana", as_index=False)["valor_total"]
            .sum()
            .rename(columns={"valor_total": "Faturamento_Total"})
        )
        resumo["dia_semana"] = pd.Categorical(
            resumo["dia_semana"], categories=ordem_dias, ordered=True
        )
        resumo = resumo.sort_values("dia_semana").reset_index(drop=True)
        resumo["Faturamento_Total"] = resumo["Faturamento_Total"].round(2)
        return resumo

    def gerar_painel_executivo(
        self,
        df_filiais: pd.DataFrame,
        df_diario: pd.DataFrame,
    ) -> None:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))

        cores = [
            "#2e7d32" if status == "Sim" else "#c62828"
            for status in df_filiais["Atingiu_Meta"]
        ]
        ax1.bar(df_filiais["filial"], df_filiais["Faturamento_Total"], color=cores)
        ax1.axhline(
            self.meta_faturamento_filial,
            color="#1a365d",
            linestyle="--",
            linewidth=2,
            label=f"Meta: R$ {self.meta_faturamento_filial:,.2f}".replace(
                ",", "X"
            ).replace(".", ",").replace("X", "."),
        )
        ax1.set_title("Faturamento por Filial vs. Meta")
        ax1.set_ylabel("Faturamento (R$)")
        ax1.tick_params(axis="x", rotation=20)
        ax1.legend()

        ax2.plot(
            df_diario["data_venda"],
            df_diario["valor_total"],
            marker="o",
            alpha=0.45,
            label="Diário",
        )
        ax2.plot(
            df_diario["data_venda"],
            df_diario["Media_Movel_3d"],
            color="#d97706",
            linewidth=2.2,
            label="Média móvel (3 dias)",
        )
        ax2.set_title("Evolução Diária de Vendas")
        ax2.set_ylabel("Faturamento (R$)")
        ax2.tick_params(axis="x", rotation=45)
        ax2.legend()

        plt.tight_layout()
        caminho_imagem = Path(self.pasta_saida) / "painel_executivo.png"
        fig.savefig(caminho_imagem, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Painel executivo salvo em: {caminho_imagem}")
