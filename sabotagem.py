"""Quebra cada defesa de propósito e confere que algum teste percebe.

    python sabotagem.py

## Por que isto existe

Teste que passa não prova nada — prova que passou. O que prova é o teste
**falhar** quando a defesa sai. Se eu remover o `AND loja_id = ?` e a bateria
continuar verde, o teste de isolamento entre lojas é decoração.

Cada item da lista abaixo troca um trecho do código por uma versão quebrada,
roda a bateria inteira, e devolve o arquivo ao original. O que importa é a
coluna do fim: **toda sabotagem tem que ser pega**.

## Isto já encontrou um teste fraco meu

O do ataque `alg:none`. O teste passava — mas passava porque a conferência de
assinatura salvava, não porque a checagem de algoritmo existia. Só apareceu
quando afrouxei o algoritmo de propósito e a bateria seguiu verde.

Se aparecer "ESCAPOU", não é o código que está errado: é o teste.
"""
import io
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.abspath(__file__))

SABOTAGENS = [
    # ---------------------------------------------------- isolamento de loja
    ("modelos.buscar sem o filtro de loja (IDOR de leitura)",
     "dados/modelos.py",
     '"SELECT * FROM modelos WHERE id = ? AND loja_id = ?",\n            (int(modelo_id), dono)).fetchone()\n    if not linha:\n        return None\n    return esquema.de_json',
     '"SELECT * FROM modelos WHERE id = ?",\n            (int(modelo_id),)).fetchone()\n    if not linha:\n        return None\n    return esquema.de_json'),

    ("modelos.salvar sem o filtro de loja (sobrescrever o alheio)",
     "dados/modelos.py",
     'WHERE id = ? AND loja_id = ?""",\n            ((nome or "").strip()',
     'WHERE id = ?""",\n            ((nome or "").strip()'),

    ("modelos.apagar sem o filtro de loja",
     "dados/modelos.py",
     '"DELETE FROM modelos WHERE id = ? AND loja_id = ?",\n                             (int(modelo_id), dono)',
     '"DELETE FROM modelos WHERE id = ?",\n                             (int(modelo_id),)'),

    # --------------------------------------------------------------- sessão
    ("o algoritmo do JWT lido do proprio token (alg:none frouxo)",
     "loja/assinatura.py",
     'if cabecalho.get("alg") != "HS256":',
     'if cabecalho.get("alg") not in ("HS256", "none"):'),

    # A versao fiel do bug: a biblioteca PULA a conferencia de assinatura
    # quando o token declara "none". E assim que o ataque funciona de verdade.
    ("alg:none pulando a conferencia de assinatura (o bug de verdade)",
     "loja/assinatura.py",
     '    if cabecalho.get("alg") != "HS256":\n        raise TokenInvalido("algoritmo %r não é aceito" % cabecalho.get("alg"))',
     '    _alg = cabecalho.get("alg")\n    if _alg not in ("HS256", "none"):\n        raise TokenInvalido("algoritmo %r não é aceito" % _alg)\n    if _alg == "none":\n        return {"loja": __import__("loja.dominio", fromlist=["x"]).normalizar(conteudo.get("dest", ""))}'),

    ("o token de sessao sendo exigido nas rotas de dados",
     "web/sessao.py",
     'if not registro:\n            texto, codigo = MENSAGENS.get(motivo, ("Não autorizado.", 401))\n            return jsonify({"erro": texto, "motivo": motivo}), codigo',
     'if not registro:\n            registro = lojas.buscar(request.args.get("shop", ""))\n            if not registro:\n                return jsonify({"erro": "x", "motivo": motivo}), 401'),

    # ------------------------------------------------------------ navegador
    ("o cabecalho que autoriza o iframe",
     "web/__init__.py",
     'resposta.headers["Content-Security-Policy"] = moldura',
     'pass  # sabotado'),

    ("X-Frame-Options voltando a ser mandado",
     "web/__init__.py",
     'resposta.headers.pop("X-Frame-Options", None)',
     'resposta.headers["X-Frame-Options"] = "DENY"'),

    # ---------------------------------------------------------------- banco
    ("PRAGMA foreign_keys (o CASCADE do shop/redact)",
     "dados/banco.py",
     'con.execute("PRAGMA foreign_keys = ON")',
     'pass  # sabotado'),

    ("a cifra do token de acesso no banco",
     "dados/banco.py",
     'return _chave_fernet().encrypt(texto.encode("utf-8")).decode("ascii")',
     'return texto'),

    # ------------------------------------------------------------- cobrança
    ("a conferencia de plano antes de imprimir",
     "web/rotas_api.py",
     'if not cobranca.pode_usar(plano, motor):',
     'if False:'),

    # -------------------------------------------------------------- receita
    # O codigo de barras e o motivo do app existir. Sem a reserva, o titulo come
    # a etiqueta e a barra some — foi um bug de verdade na etiqueta de joia.
    ("a reserva de altura do codigo de barras",
     "etiquetas/receitas.py",
     "            custo = BARRA_MINIMA_MM + TEXTO_DO_CODIGO_MM",
     "            custo = 0.0"),

    ("o piso de altura que faz o codigo de barras bipar",
     "etiquetas/receitas.py",
     "            altura_barra = max(BARRA_MINIMA_MM,\n                               min(BARRA_MINIMA_MM + max(0.0, orcamento),\n                                   altura * 0.42))",
     "            altura_barra = min(BARRA_MINIMA_MM + max(0.0, orcamento),\n                               altura * 0.42)"),

    # SKU e preco desalinhados por 0,34mm: os dois continuam DENTRO da etiqueta,
    # entao nenhum teste de borda pega. So um teste de base comum pega.
    #
    # Sabotar a linha do PRECO nao serve: como ele e o maior dos dois,
    # `linha_valor - linha_preco` ja e zero e tirar isso nao muda nada. Quem faz
    # o trabalho e o recuo do SKU, que e o menor. Descobri isso vendo esta
    # sabotagem escapar — o que e exatamente pra que ela existe.
    ("SKU e preco apoiados na mesma linha de base",
     "etiquetas/receitas.py",
     "                    y_mm=y_da_linha + (linha_valor - linha_normal),",
     "                    y_mm=y_da_linha,"),

    # ---------------------------------------------------------- uma regra, um lugar
    ("valores.py: a formatacao de preco voltando pra dentro do motor",
     "etiquetas/motores/svg.py",
     "    bruto = valores.do_elemento(el, dados)",
     "    bruto = (el.prefixo + campos.resolver(el.campo, dados) + el.sufixo\n             if el.campo else el.prefixo + el.sufixo)"),
]


def rodar():
    r = subprocess.run([sys.executable, "testes.py"], cwd=RAIZ,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    resumo = [l for l in r.stdout.splitlines() if l.startswith("PASSOU:")]
    falhas = [l.strip()[2:] for l in r.stdout.splitlines() if l.strip().startswith("- ")]
    return r.returncode, (resumo[0] if resumo else "SEM SAIDA"), falhas


def principal():
    print("=" * 78)
    codigo, resumo, _ = rodar()
    print("SEM SABOTAGEM: %s  (saida %d)" % (resumo, codigo))
    if codigo != 0:
        print("\nA bateria ja esta vermelha. Conserte antes de sabotar.")
        return 1
    print("=" * 78)

    pegas, escaparam = 0, []
    for nome, arquivo, antes, depois in SABOTAGENS:
        caminho = os.path.join(RAIZ, arquivo)
        original = io.open(caminho, encoding="utf-8").read()

        if antes not in original:
            # O codigo mudou e a sabotagem ficou pra tras. Isso e um aviso: a
            # defesa pode ter sumido junto e ninguem percebeu.
            print("  ??  %-62s [trecho nao existe mais]" % nome[:62])
            escaparam.append(nome + "  (trecho nao existe mais — reveja)")
            continue

        io.open(caminho, "w", encoding="utf-8").write(
            original.replace(antes, depois, 1))
        try:
            codigo, resumo, falhas = rodar()
        finally:
            io.open(caminho, "w", encoding="utf-8").write(original)

        if codigo != 0:
            pegas += 1
            print("  ok  %-62s %s" % (nome[:62], (falhas[0] if falhas else resumo)[:60]))
        else:
            escaparam.append(nome)
            print("  XX  %-62s ESCAPOU" % nome[:62])

    print("=" * 78)
    print("SABOTAGENS PEGAS: %d de %d" % (pegas, len(SABOTAGENS)))
    if escaparam:
        print("\nESCAPARAM — nao e o codigo que esta errado, e o TESTE:")
        for nome in escaparam:
            print("  - %s" % nome)
    print("=" * 78)
    return 1 if escaparam else 0


if __name__ == "__main__":
    sys.exit(principal())
