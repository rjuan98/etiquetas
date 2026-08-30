"""Arquivo-espelho: a saída de ontem congelada, pra comparar com a de hoje.

Esta é a peça que transforma a promessa do produto em garantia técnica.

A promessa é *"seu template não muda sozinho, nunca"*. Ela nasceu de uma
reclamação real: o Shopify mudou a fonte numa atualização de julho de 2026 e as
etiquetas de todos os lojistas pararam de combinar. Um deles escreveu *"todas as
minhas etiquetas não combinam mais"*.

Teste de substring — "tem `^BE` na saída", "tem `R$ 24,90`" — não protege disso.
Ele passa feliz enquanto cada elemento anda meio milímetro pro lado.

O arquivo-espelho compara **byte a byte**. Se um dot mudou de lugar, quebra.

## Como usar

    python espelho.py           confere (é o que roda dentro de testes.py)
    python espelho.py gravar    regrava os espelhos

**`gravar` é o comando perigoso.** Ele aceita a saída de hoje como a verdade.
Só se usa quando a mudança foi deliberada — e aí o `git diff` dos espelhos mostra
exatamente o que mudou na etiqueta de cada lojista. Se o diff surpreender, é bug.
"""
import os
import sys

from etiquetas import esquema
from etiquetas.modelo import Calibracao, CodigoBarras, Midia, Preco, Template, Texto
from etiquetas.motores import zpl

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "espelhos")

PRODUTO = {
    "produto": {"titulo": "Canudo de Vidro Reto 20cm - Kit 4 unidades",
                "fornecedor": "EcoCasa"},
    "variante": {"sku": "CAN-VD-20", "codigo_barras": "789123456789",
                 "preco": "24.90"},
}
PRODUTO["produto"]["url"] = "https://ecocasa.com.br/p/canudo-vidro-reto-20cm"

# Um produto de catálogo bagunçado: título gigante, sem código, preço com milhar.
BAGUNCADO = {
    "produto": {"titulo": "Kit Completo Sustentavel com 12 Canudos de Vidro "
                          "Borossilicato Reto e Curvo mais Escova de Limpeza"},
    "variante": {"sku": "KIT-SUST-12-BOROSSILICATO-RC", "preco": "1234.5"},
}


def _t(nome, midia, elementos, calibracao=None):
    return Template(nome=nome, midia=midia, elementos=elementos,
                    calibracao=calibracao or Calibracao())


def casos():
    """Os cenários congelados. Acrescentar caso é acrescentar uma entrada aqui.

    Cada um mira uma decisão que a gente tomou e que não pode mudar sozinha.
    """
    varejo = [
        Texto(x_mm=2, y_mm=1, campo="produto.titulo",
              largura_mm=46.75, tamanho_pt=7.8, linhas_max=2),
        Texto(x_mm=2, y_mm=7.75, campo="variante.sku", prefixo="SKU: ", tamanho_pt=6.4),
        Preco(x_mm=2, y_mm=7.25, campo="variante.preco",
              largura_mm=46.75, tamanho_pt=10, alinhamento="dir"),
        CodigoBarras(x_mm=2, y_mm=11.5, campo="variante.codigo_barras",
                     simbologia="EAN13", altura_mm=7.5, modulo_dots=2),
    ]
    m2x1 = Midia(50.8, 25.4)

    return [
        # O caso de referência: é esta etiqueta que foi conferida no Labelary.
        ("varejo_2x1", _t("2x1", m2x1, varejo), PRODUTO),

        # Calibração nos dois sentidos — a funcionalidade principal do produto.
        ("varejo_calibrado", _t("2x1", m2x1, varejo, Calibracao(1.0, -0.5)), PRODUTO),

        # Título que estoura, SKU longo, preço com milhar, e SEM código de barras.
        # Congela três decisões de uma vez: onde o texto corta, como o milhar é
        # escrito, e que campo vazio some com o rótulo junto.
        ("catalogo_baguncado", _t("2x1", m2x1, varejo), BAGUNCADO),

        # Moeda europeia: símbolo à direita e espaço como milhar. Nasceu da loja
        # francesa que não conseguia pôr o € do lado certo.
        ("preco_europeu", _t("2x1", m2x1, [
            Preco(x_mm=2, y_mm=2, campo="variante.preco", largura_mm=46.75,
                  tamanho_pt=10, alinhamento="dir", simbolo="€",
                  simbolo_depois=True, separador_decimal=",", separador_milhar=" "),
        ]), BAGUNCADO),

        # Code128 aceita texto, e o SKU vira código quando não há EAN.
        ("code128_por_sku", _t("2x1", m2x1, [
            CodigoBarras(x_mm=2, y_mm=2, campo="variante.sku",
                         simbologia="CODE128", altura_mm=12, modulo_dots=2),
        ]), PRODUTO),

        # Texto fixo sem campo nenhum — o rodapé da etiqueta.
        ("texto_fixo", _t("2x1", m2x1, [
            Texto(x_mm=2, y_mm=2, campo="", prefixo="Industria Brasileira",
                  tamanho_pt=6),
            Texto(x_mm=2, y_mm=8, campo="produto.fornecedor", prefixo="Por ",
                  tamanho_pt=6),
        ]), PRODUTO),

        # SENTINELA. Este caso não descreve nenhuma etiqueta real — ele existe
        # só pra ser frágil de propósito.
        #
        # A primeira versão dos espelhos não pegou uma mudança de 0,8% na
        # proporção da fonte: nos sete casos "normais", nenhuma quebra de linha
        # se moveu, e todos passaram felizes. Um espelho que só quebra com
        # mudança grande não protege de nada — mudança grande a gente percebe
        # sozinho.
        #
        # A conta: a 7,8pt e 32mm de largura, cabem 20,05 caracteres. O título
        # abaixo quebra em "Canudo de Vidro Reto", que tem exatamente 20. Basta
        # a estimativa de largura mudar 0,3% pra quebra virar outra e este caso
        # gritar.
        ("sentinela_limiar", _t("sentinela", Midia(40, 20), [
            Texto(x_mm=2, y_mm=2, campo="produto.titulo", largura_mm=32,
                  tamanho_pt=7.8, linhas_max=3),
        ]), PRODUTO),

        # QR apontando pra URL do produto. Congela o formato do comando ^BQ,
        # incluindo o prefixo "MA," (correção média, modo automático) que vai
        # DENTRO do ^FD e não no comando — detalhe do ZPL fácil de errar.
        ("qr_do_produto", _t("qr", Midia(50.8, 25.4), [
            Texto(x_mm=2, y_mm=2, campo="produto.titulo", largura_mm=26,
                  tamanho_pt=7, linhas_max=2),
            CodigoBarras(x_mm=30, y_mm=4, campo="produto.url",
                         simbologia="QR", altura_mm=18, modulo_dots=4),
        ]), PRODUTO),

        # ITF-14: o código da caixa de atacado. Está aqui porque ele é o único
        # com BARRA LARGA, e a razão larga/fina é o número que faz o mesmo
        # código sair de larguras diferentes em impressoras diferentes. Se
        # alguém mexer nela, este arquivo grita.
        ("itf14_da_caixa", _t("caixa", Midia(101.6, 50.8), [
            Texto(x_mm=3, y_mm=3, campo="produto.titulo", largura_mm=95,
                  tamanho_pt=10, linhas_max=1),
            CodigoBarras(x_mm=3, y_mm=10, campo="variante.codigo_barras",
                         simbologia="ITF14", altura_mm=14, modulo_dots=2),
        ]), {"produto": {"titulo": "Caixa com 12 canudos"},
             "variante": {"codigo_barras": "10789123456785"}}),

        # Etiqueta de joia, minúscula: é onde o texto encolhe em vez de cortar.
        ("joia_encolhe", _t("joia", Midia(25, 12), [
            Texto(x_mm=1, y_mm=1, campo="produto.titulo", largura_mm=23,
                  tamanho_pt=7, linhas_max=2, excesso="encolher"),
            Preco(x_mm=1, y_mm=8, campo="variante.preco", largura_mm=23,
                  tamanho_pt=7, alinhamento="dir"),
        ]), PRODUTO),
    ]


def _saida(template, dados) -> str:
    """O que é congelado: o ZPL, mais o template em JSON.

    O JSON entra junto porque um campo novo com padrão errado muda a etiqueta
    sem mudar uma linha de motor.
    """
    return (zpl.render(template, dados)
            + "\n\n--- template ---\n"
            + esquema.para_json(template))


def gravar():
    os.makedirs(PASTA, exist_ok=True)
    for nome, template, dados in casos():
        caminho = os.path.join(PASTA, nome + ".txt")
        with open(caminho, "w", encoding="utf-8", newline="\n") as f:
            f.write(_saida(template, dados))
        print("  gravado  %s" % nome)


def conferir() -> list:
    """Devolve a lista de casos que mudaram. Vazia quando está tudo igual."""
    mudaram = []
    for nome, template, dados in casos():
        caminho = os.path.join(PASTA, nome + ".txt")
        if not os.path.exists(caminho):
            mudaram.append((nome, "espelho não existe — rode `python espelho.py gravar`"))
            continue
        with open(caminho, encoding="utf-8") as f:
            esperado = f.read()
        atual = _saida(template, dados)
        if atual != esperado:
            mudaram.append((nome, _primeira_diferenca(esperado, atual)))
    return mudaram


def _primeira_diferenca(esperado: str, atual: str) -> str:
    """A primeira linha que difere, com o antes e o depois.

    Dizer só "mudou" obriga a pessoa a caçar. Dizer QUAL linha e COMO ela era
    transforma o teste em explicação.
    """
    linhas_e = esperado.splitlines()
    linhas_a = atual.splitlines()
    for i in range(max(len(linhas_e), len(linhas_a))):
        e = linhas_e[i] if i < len(linhas_e) else "(acabou)"
        a = linhas_a[i] if i < len(linhas_a) else "(acabou)"
        if e != a:
            return "linha %d:\n        era:  %s\n        hoje: %s" % (i + 1, e, a)
    return "diferença só em espaço no fim"


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "gravar":
        print("Regravando os espelhos. Confira o `git diff` antes de aceitar.\n")
        gravar()
    else:
        problemas = conferir()
        if not problemas:
            print("Todos os espelhos batem.")
        else:
            print("MUDARAM %d caso(s):\n" % len(problemas))
            for nome, detalhe in problemas:
                print("  %s\n    %s\n" % (nome, detalhe))
        sys.exit(1 if problemas else 0)
