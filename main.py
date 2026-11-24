from pathlib import Path

from src.analisador import AnalisadorExecutivo


def executar_pipeline() -> None:
    pasta_projeto = Path(__file__).resolve().parent
    analisador = AnalisadorExecutivo(
        caminho_produtos=pasta_projeto / "dados" / "produtos.csv",
        caminho_vendas=pasta_projeto / "dados" / "vendas.csv",
        pasta_saida=pasta_projeto / "relatorios",
        meta_faturamento_filial=7000.0,
    )

    analisador.preparar_dados()

    relatorio_categoria = analisador.faturamento_por_categoria()
    analisador.exportar_csv(
        relatorio_categoria, "faturamento_por_categoria.csv"
    )
    analisador.gerar_grafico_categorias(relatorio_categoria)

    relatorio_filiais = analisador.kpis_por_filial()
    analisador.exportar_csv(relatorio_filiais, "kpis_por_filial.csv")

    relatorio_diario = analisador.faturamento_diario()

    relatorio_dia_semana = analisador.faturamento_por_dia_semana()
    analisador.exportar_csv(
        relatorio_dia_semana, "faturamento_dia_semana.csv"
    )

    analisador.gerar_painel_executivo(relatorio_filiais, relatorio_diario)
    auditoria = analisador.exportar_auditoria()

    print("\nKPIs por filial:")
    print(relatorio_filiais.to_string(index=False))
    print(f"\nRegistros de auditoria: {len(auditoria)}")


if __name__ == "__main__":
    executar_pipeline()
