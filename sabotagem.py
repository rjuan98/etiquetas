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

# O console do Windows e cp1252, e o nome dos testes tem travessao e acento.
# Sem isto a ferramenta MORRE no meio da rodada ao reimprimir o nome de um teste
# que falhou — e morrer no meio e pior que nao rodar: parece que passou.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

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
     "        registro, motivo = loja_atual()",
     '        registro, motivo = loja_atual()\n        if not registro:\n            registro = lojas.buscar(request.args.get("shop", ""))\n            motivo = "" if registro else motivo'),

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

    # O buraco que a medicao achou: o webhook gravava "conferir" DENTRO da
    # coluna do plano, e o lojista que acabou de pagar caia pro gratis — em
    # silencio e pra sempre, porque nada resolvia esse estado de volta.
    ("o webhook marcando vencido sem destruir o plano conhecido",
     "web/rotas_webhooks.py",
     '            lojas.marcar_plano_vencido(registro["id"])',
     '            lojas.marcar_plano(registro["id"], "conferir")'),

    # Cair pro gratis quando o Shopify nao responde e uma instabilidade DELES
    # virando prejuizo pro lojista que esta pagando, no meio do trabalho.
    ("o pagante nao ser rebaixado quando o Shopify nao responde",
     "web/rotas_api.py",
     '    except (rede.ErroDeRede, KeyError, ValueError) as erro:',
     '    except (rede.ErroDeRede, KeyError, ValueError) as erro:\n        plano = "gratis"'),

    # Sem validade, um cancelamento cujo webhook se perdeu daria acesso pago pra
    # sempre. E webhook se perde.
    ("a validade que reconfere o plano mesmo sem webhook",
     "dados/lojas.py",
     "    idade = datetime.now(timezone.utc) - lido\n    return idade.total_seconds() > VALIDADE_DO_PLANO_EM_HORAS * 3600",
     "    return False"),

    # ------------------------------------------------------------- cobrança
    # Cobrar de verdade numa loja de desenvolvimento e motivo de REPROVACAO na
    # revisao — e cobrar de teste numa loja real e entregar o produto de graca.
    # Antes isso dependia de alguem lembrar de trocar uma variavel.
    ("o tipo de cobranca sendo perguntado ao Shopify",
     "web/rotas_api.py",
     "            desenvolvimento=tipo)",
     "            desenvolvimento=True)"),

    # Plano inexistente e erro de quem chamou. Validar DEPOIS da ida ao Shopify
    # gasta chamada a toa e vira um 502 confuso quando a rede falha.
    ("a validacao do plano antes de ir a rede",
     "web/rotas_api.py",
     '        cobranca.corpo_para_assinar(codigo, "https://validacao")',
     "        pass"),

    # Sem saber o tipo, nao da pra decidir — e chutar erra caro dos dois lados.
    ("a recusa quando nao da pra saber o tipo da loja",
     "web/rotas_api.py",
     "    if tipo is None:",
     "    if False:"),

    # userErrors vem DENTRO de uma resposta 200. Sem tratar, o lojista e mandado
    # pra lugar nenhum achando que assinou.
    ("o tratamento de userErrors ao criar a assinatura",
     "web/rotas_api.py",
     "        url = cobranca.url_de_confirmacao(resposta)",
     '        url = ((resposta.get("data") or {}).get("appSubscriptionCreate")\n               or {}).get("confirmationUrl") or "https://exemplo"'),

    # A volta da cobranca nao pode promover ninguem por conta propria: quem diz
    # se a assinatura existe e o Shopify, nao um clique num link.
    ("a volta da cobranca so marcando pra reconferir",
     "web/rotas_cobranca.py",
     "        lojas.marcar_plano_vencido(registro[\"id\"])",
     "        lojas.marcar_plano(registro[\"id\"], \"pro\")"),

    # -------------------------------------------------------------- receita
    # O codigo de barras e o motivo do app existir. Sem a reserva, o titulo come
    # a etiqueta e a barra some — foi um bug de verdade na etiqueta de joia.
    ("a reserva de altura do codigo de barras",
     "etiquetas/receitas.py",
     "            custo = BARRA_MINIMA_MM + altura_dos_digitos + folga_do_codigo",
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

    # O modelo_id vem do navegador. Sem conferir de quem e, o historico desta
    # loja guardaria o id de um modelo de outra — e o suporte olharia o registro
    # errado. E o mesmo IDOR de sempre, so que num campo de anotacao.
    ("a conferencia de dono do modelo_id que vem do navegador",
     "web/rotas_api.py",
     "        if modelo_id and not tabela_modelos.buscar_cru(loja[\"id\"], modelo_id):\n            modelo_id = None",
     "        pass  # sabotado"),

    # A receita e o que reabre o editor. Sem guardar, da pra imprimir e nao da
    # pra editar: o modelo abriria com todos os botoes no padrao.
    ("a receita sendo guardada junto do modelo",
     "dados/modelos.py",
     "            (dono, nome, texto, json.dumps(receita or {}), momento, momento))",
     "            (dono, nome, texto, '{}', momento, momento))"),

    # A rota de retorno da instalacao era a unica sem teste, porque fala com a
    # rede. E foi ela que quebrou na cara do lojista: renomeei uma variavel e
    # deixei um uso antigo pra tras. Agora a rede e substituida e o resto do
    # caminho e testado.
    ("a gravacao da loja no fim da instalacao",
     "web/rotas_instalacao.py",
     '    lojas.salvar(loja, token, ",".join(oauth.ESCOPOS),\n                 refresh=credenciais["refresh"],\n                 expira_em=credenciais["expira_em"],\n                 refresh_expira_em=credenciais["refresh_expira_em"])',
     "    pass  # sabotado"),

    ("a assinatura dos webhooks na instalacao",
     "web/rotas_instalacao.py",
     "        _assinar_webhooks(loja, token)",
     "        pass  # sabotado"),

    # ------------------------------------------------------------- desempenho
    # O conteudo da etiqueta vem do navegador. Achar o ponto de corte tirando um
    # caractere por vez custava 472ms em 40 mil caracteres, crescendo com o
    # QUADRADO — e um titulo de 2 MB, que o Flask aceita, travava um processo.
    ("a conta direta do ponto de corte (era quadratica)",
     "etiquetas/texto.py",
     "            corte = min(len(palavra) - 1, quantos_cabem(largura_mm, tamanho_pt))",
     "            corte = len(palavra) - 1"),

    ("o teto de caracteres que entram na conta",
     "etiquetas/texto.py",
     "    if texto and len(texto) > TETO_DE_CARACTERES:\n        texto = texto[:TETO_DE_CARACTERES]",
     "    pass  # sabotado"),

    # No modo padrao do SQLite uma escrita bloqueia TODAS as leituras.
    ("o WAL, que impede escritor e leitor de travarem um ao outro",
     "dados/banco.py",
     'con.execute("PRAGMA journal_mode = WAL")',
     'pass  # sabotado'),

    # A tela lia so os 50 primeiros produtos: a API devolvia o cursor e ninguem
    # usava. Numa loja com 200 produtos, 150 nao existiam.
    ("o cursor de paginacao chegando na tela",
     "web/rotas_api.py",
     '        "itens": itens, "tem_mais": tem_mais, "cursor": cursor,\n        "variantes_cortadas": catalogo.produtos_com_variantes_cortadas(itens),',
     '        "itens": itens, "tem_mais": False, "cursor": None,\n        "variantes_cortadas": [],'),

    # Grade de roupa grande passa de 100 variantes, e o lojista imprimiria a
    # prateleira faltando tamanhos sem nada avisar.
    ("o aviso de produto com variantes cortadas",
     "loja/catalogo.py",
     '        cortado = bool((bloco.get("pageInfo") or {}).get("hasNextPage"))',
     "        cortado = False"),

    # ---------------------------------------------------------------- idioma
    # Ingles e o padrao porque as 565 avaliacoes que embasaram a ideia sao em
    # ingles. Cair no portugues seria servir a lingua errada pro mercado inteiro.
    ("o ingles como idioma padrao",
     "web/textos.py",
     'PADRAO = "en"',
     'PADRAO = "pt"'),

    # Sem isto a tela fica na lingua do lojista e as mensagens de erro voltam no
    # padrao — metade traduzida, que parece mais quebrado que nada traduzido.
    ("o idioma viajando nas chamadas de API",
     "web/rotas_tela.py",
     '  caminho += (caminho.indexOf("?") < 0 ? "?" : "&") + "idioma=" + IDIOMA;',
     "  // sabotado"),

    # O motor tem arquivo-espelho justamente pra nao mudar. Se texto de tela
    # entrar nele, traduzir passa a exigir mexer no motor.
    ("os nomes de campo traduzidos na borda, nao no motor",
     "web/rotas_api.py",
     '"campos": [{"chave": k, "nome": _t("campo_" + k)} for k in receitas.CAMPOS],',
     '"campos": [{"chave": k, "nome": v["nome"]} for k, v in receitas.CAMPOS.items()],'),

    # A altura de linha poe a linha de base no fim do bloco, e a letra desce
    # abaixo dela. Contra o codigo de barras, que e tinta solida, a descida cai
    # em cima das barras. Apareceu numa captura de tela: os testes de borda nao
    # pegavam porque tudo continuava DENTRO da etiqueta.
    ("a folga entre o texto e as barras",
     "etiquetas/receitas.py",
     "            custo = BARRA_MINIMA_MM + altura_dos_digitos + folga_do_codigo",
     "            custo = BARRA_MINIMA_MM + altura_dos_digitos"),

    # Folga fixa resolvia nas etiquetas pequenas e continuava colidindo na de
    # 3x2 polegadas, onde a fonte e o dobro e a letra desce o dobro junto.
    ("a folga sendo proporcional a fonte, nao fixa",
     "etiquetas/receitas.py",
     "_mm_da_fonte(pt_preco) * (DESCIDA_DA_LETRA + 0.04))",
     "FOLGA_MINIMA_MM)"),

    # ------------------------------------------- o codigo cabendo na LARGURA
    # A etiqueta de 1"x1" mostrou o buraco: so a ALTURA era conferida. Um
    # EAN-13 legivel precisa de 28,3mm e o papel tem 25,4mm, entao o codigo
    # saia serrado pela borda — o defeito que este app existe pra corrigir.
    ("a receita conferindo se o codigo cabe na largura",
     "etiquetas/receitas.py",
     "        codigo_cabe_na_largura = margem_x + codigos.largura_minima_mm(",
     "        codigo_cabe_na_largura = True or codigos.largura_minima_mm("),

    # O motor e a segunda rede: um Code128 comprido cabe no template e nao cabe
    # no papel, e isso so da pra saber com o dado do produto na mao.
    ("o ZPL recusando codigo que vaza pela borda",
     "etiquetas/motores/zpl.py",
     "    if not codigos.cabe_na_largura(simbologia, valor, el.modulo_dots, dpi,\n"
     "                                   el.x_mm, template.midia.largura_mm,\n"
     "                                   el.altura_mm):\n        return []",
     "    if False:\n        return []"),

    ("a previa recusando o mesmo codigo que o ZPL recusa",
     "etiquetas/motores/svg.py",
     "    if not codigos.cabe_na_largura(simbologia, valor, el.modulo_dots,\n"
     "                                   unidades.ZEBRA_203, el.x_mm,\n"
     "                                   template.midia.largura_mm, el.altura_mm):\n        return []",
     "    if False:\n        return []"),

    ("a zona muda entrando na conta de largura",
     "etiquetas/codigos.py",
     "    return (barras\n            + margem_esquerda_mm(simbologia, modulo_dots, dpi)\n"
     "            + margem_direita_mm(simbologia, modulo_dots, dpi))",
     "    return barras"),

    # ------------------------------------------------- o QR do mesmo tamanho
    # Medido: o mesmo modelo saia 18,0mm no PDF/SVG e 16,5mm no ZPL, porque o
    # ^BQ recebe uma MAGNIFICACAO inteira e o motor passava o `modulo_dots` —
    # que e a largura da barra fina de um codigo linear e nao diz nada sobre
    # QR. Com URL longa (matriz 57) isso da 28,5mm num campo de 18mm.
    ("a magnificacao do QR saindo da altura pedida, nao do modulo_dots",
     "etiquetas/motores/zpl.py",
     "        _lado_mm, magnificacao = codigos.lado_do_qr_mm(\n"
     "            valor, el.altura_mm, dpi, correcao)",
     "        magnificacao = max(1, el.modulo_dots)"),

    ("a previa desenhando o QR no mesmo lado que o ZPL",
     "etiquetas/motores/svg.py",
     "        lado_mm, _mag = codigos.lado_do_qr_mm(\n"
     "            valor, el.altura_mm, unidades.ZEBRA_203, el.correcao_qr)\n"
     "        lado = unidades.mm_para_pontos(lado_mm)",
     "        lado = unidades.mm_para_pontos(el.altura_mm)"),

    # ------------------------------------- os digitos sob o codigo custam 2,6mm
    # Numa Avery 5167 faltavam 0,07mm pro SKU. Os digitos repetem o que as
    # barras ja carregam; o SKU nao esta em outro lugar da etiqueta. Se o custo
    # deixar de responder a escolha, o lojista perde o SKU sem ter escolhido.
    ("os digitos sob o codigo devolvendo os 2,6mm quando desligados",
     "etiquetas/receitas.py",
     "    altura_dos_digitos = TEXTO_DO_CODIGO_MM if digitos_do_codigo else 0.0",
     "    altura_dos_digitos = TEXTO_DO_CODIGO_MM"),

    # ------------------------------------------------------- medida livre
    # Sem limite, o lojista digita 4000 e recebe uma etiqueta que impressora
    # nenhuma aceita — e um SVG gigante que trava a prova na tela.
    ("os limites de bom senso da medida livre",
     "etiquetas/formatos.py",
     "        if not (MENOR_MEDIDA_MM <= valor <= MAIOR_MEDIDA_MM):",
     "        if False:"),

    # Sem a conversao, texto vira medida e o erro sai como TypeError la no
    # fundo do motor, em vez de um 400 que o lojista consegue ler.
    ("medida livre recusando o que nao e numero",
     "etiquetas/formatos.py",
     "        try:\n            valor = float(valor)\n        except (TypeError, ValueError):\n            raise ValueError(\"%s tem que ser um número\" % nome)",
     "        pass"),

    # ------------------------------------------- o token que agora vence
    # O Shopify parou de aceitar token de acesso que nao expira: a Admin API
    # responde 403. O app instalava bonito e nao lia produto nenhum.
    ("a instalacao pedindo token que expira",
     "loja/oauth.py",
     '"code": codigo, "expiring": EXPIRANDO}',
     '"code": codigo}'),

    # Sem isto, quem instalou ANTES da mudanca tomaria 403 pra sempre. A
    # alternativa seria pedir pra reinstalar — e lojista que precisa reinstalar
    # pra o app voltar a funcionar desinstala e nao volta.
    ("a troca automatica do token da era anterior",
     "web/credenciais.py",
     "    if not registro.get(\"refresh\") and not registro.get(\"token_expira_em\"):",
     "    if False:"),

    # Cada renovacao INVALIDA o par anterior. Nao guardar o novo deixa a loja
    # orfa: sem acesso e sem como renovar.
    ("o par novo sendo guardado depois de renovar",
     "web/credenciais.py",
     "    lojas.guardar_credenciais(registro[\"id\"], novo[\"token\"], novo[\"refresh\"],\n                              novo[\"expira_em\"], novo[\"refresh_expira_em\"])",
     "    pass"),

    # A renovacao mora no PORTAO. Tirar dali significa cada rota se virar
    # sozinha — e o sintoma e o app funcionar por uma hora depois de instalar.
    ("a renovacao acontecendo no portao de toda rota",
     "web/sessao.py",
     "        if not loja_de_mentira(registro):\n            registro = credenciais.garantir(registro)",
     "        pass"),

    # Refresh vale 90 dias e gera acesso novo sozinho. Deixar no banco depois da
    # desinstalacao e guardar a chave da casa de quem ja se mudou.
    ("o refresh morrendo junto com a desinstalacao",
     "dados/lojas.py",
     "                       SET ativa = 0, token_cifrado = '', refresh_cifrado = '',",
     "                       SET ativa = 0, token_cifrado = '',"),

    # Sem margem, o token pode vencer ENTRE a conferencia e a chamada ao
    # Shopify. Corrida rara, e impossivel de reproduzir depois.
    ("a margem que renova antes da hora",
     "web/credenciais.py",
     "MARGEM_EM_SEGUNDOS = 300",
     "MARGEM_EM_SEGUNDOS = 0"),

    # -------------------------------------------------- a corrida da renovacao
    # A tela dispara tres chamadas em paralelo ao abrir. Com o token vencido,
    # sem trava, as tres renovam com o MESMO refresh — e o Shopify invalida o
    # refresh no primeiro uso. Medido: duas das tres mandavam reinstalar.
    ("a trava que impede duas renovacoes ao mesmo tempo",
     "web/credenciais.py",
     "    with _trava_da_loja(registro[\"id\"]):",
     "    if True:"),

    # Reler DENTRO da trava e o que faz a espera valer. Sem isso, quem esperou
    # renova de novo com o refresh que o primeiro ja gastou.
    ("a releitura dentro da trava",
     "web/credenciais.py",
     "        atual = lojas.por_id(registro[\"id\"]) or registro\n        falta = _o_que_falta(atual)",
     "        atual = registro\n        falta = _o_que_falta(atual)"),

    # Com varios processos a trava nao alcanca. Perder a corrida pra outro
    # processo nao pode virar "reinstale" — basta olhar o que ficou guardado.
    ("a checagem de quem ganhou a corrida entre processos",
     "web/credenciais.py",
     "            if salvo and salvo.get(\"token\") and not _o_que_falta(salvo):",
     "            if False:"),

    # Contar os modulos de um QR custa 10ms; um EAN-13 custa 0,01ms. Cada
    # etiqueta pergunta duas vezes. Sem cache, 300 etiquetas = 6,4s de CPU.
    ("o cache da contagem de modulos do QR",
     "etiquetas/codigos.py",
     "@functools.lru_cache(maxsize=512)\ndef modulos_do_qr(",
     "def modulos_do_qr("),

    # Perguntar a simbologia sempre quebrava etiqueta que nem tem codigo.
    ("a simbologia so sendo exigida quando o codigo esta ligado",
     "etiquetas/receitas.py",
     "    if \"codigo_barras\" in ligados:",
     "    if True:"),

    # --------------------------------------------------- ITF-14 e o verificador
    # O reportlab usa razao 2,2 e o ^BY do ZPL usa 3,0. Sem fixar, o MESMO
    # ITF-14 sai 21% mais largo na Zebra que no PDF e na previa.
    ("a razao barra-larga igual nos dois motores",
     "etiquetas/motores/pdf.py",
     "        extras[\"ratio\"] = simbologia.razao_larga",
     "        pass"),

    # O reportlab acrescenta digito verificador por padrao. Com o codigo ja
    # completo isso vira um 15o digito, e o codigo para de bipar.
    ("o reportlab sendo proibido de acrescentar digito",
     "etiquetas/motores/pdf.py",
     "        extras[\"checksum\"] = 0",
     "        extras[\"checksum\"] = 1"),

    # Idem do lado da impressora: com Y no ^B2 ela calcula outro.
    ("o ^B2 nao pedindo verificador extra a impressora",
     "etiquetas/motores/zpl.py",
     "    extra = \",N\" if simbologia.verificador_no_zpl else \"\"",
     "    extra = \",Y\" if simbologia.verificador_no_zpl else \"\""),

    # Estava escrito `if simbologia is EAN13`: UPC-A com verificador errado
    # passava e ia pro papel. Codigo errado bipa o PRODUTO ERRADO no caixa.
    ("o verificador conferido em TODAS as simbologias numericas",
     "etiquetas/codigos.py",
     "        esperado = digito_verificador_gs1(valor[:-1])\n        if valor[-1] != esperado:",
     "        esperado = digito_verificador_gs1(valor[:-1]) if simbologia is EAN13 else valor[-1]\n        if valor[-1] != esperado:"),

    # A conta do GS1 conta da DIREITA. Contando da esquerda ela acerta no
    # EAN-13 por sorte do comprimento par e erra no UPC-A e no ITF-14.
    ("a conta do verificador contando da direita",
     "etiquetas/codigos.py",
     "    for i, char in enumerate(reversed(digitos)):",
     "    for i, char in enumerate(digitos):"),

    # Sumir calado e o defeito que este app existe pra corrigir. O lojista
    # escolhe ITF-14, o codigo some da previa, e ele acha que o app quebrou.
    ("o motivo de o codigo ter sumido da previa",
     "web/rotas_api.py",
     '        "codigo_invalido": _por_que_o_codigo_sumiu(template, item),',
     '        "codigo_invalido": "",'),

    # A ficha e um contrato publico. Prometer 200 etiquetas quando o codigo da
    # 100 e reclamacao no primeiro dia — e o tipo de divergencia que ninguem ve
    # porque ficha e codigo moram em arquivos diferentes.
    # `webhookSubscriptionCreate` nao aceita topico de conformidade. Mandar os
    # tres pela API gerava erro engolido pelo `except` e a falsa impressao de
    # que estavam ligados — e sem a declaracao estatica a revisao REPROVA.
    ("a instalacao nao tentando assinar os webhooks de privacidade",
     "web/rotas_instalacao.py",
     "    for topico in webhooks.ASSINADOS_NA_INSTALACAO:",
     "    for topico in webhooks.TODOS:"),

    ("a ficha da loja prometendo o mesmo que o codigo entrega",
     "docs/ficha-loja-de-apps.md",
     "| Free | US$ 0 | 1 template, 200 labels/month, sheet labels (PDF) |",
     "| Free | US$ 0 | 1 template, 500 labels/month, sheet labels (PDF) |"),

    # "Read-only" e a unica frase da ficha que nenhum concorrente pode escrever.
    # Se um dia entrar escopo de escrita, a ficha tem que perder essa linha no
    # MESMO commit — senao ela vira mentira.
    ("a promessa de so-leitura batendo com os escopos pedidos",
     "loja/oauth.py",
     'ESCOPOS = ("read_products", "read_inventory")',
     'ESCOPOS = ("read_products", "read_inventory", "write_products")'),

    ("o plano gratis acompanhando o que o mercado da",
     "loja/cobranca.py",
     '"limite_etiquetas_mes": 200,',
     '"limite_etiquetas_mes": 100,'),

    # ---------------------------------------------------- a fila e o leitor
    # Medido no navegador: escolher um produto, buscar outra coisa e escolher o
    # segundo dava contador "2 produto(s), 52 etiqueta(s)" e fila com 1. O
    # primeiro sumia do PDF em silencio, no momento de imprimir.
    ("a fila saindo do que foi escolhido, nao da busca atual",
     "web/rotas_tela.py",
     "  escolhidos.forEach(function (e) {\n    saida.push(Object.assign({}, e.item, {quantidade: e.quantidade}));\n  });",
     "  itens.forEach(function (it) {\n    if (escolhidos.has(it.variante.id)) saida.push(it);\n  });"),

    ("o item inteiro sendo guardado, e nao so a quantidade",
     "web/rotas_tela.py",
     "  escolhidos.set(it.variante.id,\n                 {item: it, quantidade: Math.max(1, quantidade || 1)});",
     "  escolhidos.set(it.variante.id, Math.max(1, quantidade || 1));"),

    # A regra do leitor e o casamento EXATO. Trocar por "a busca devolveu um so"
    # faz quem digita "caneca" ter o produto escolhido sem ter pedido.
    ("o leitor casando por codigo exato, e nao por 'so deu um resultado'",
     "web/rotas_tela.py",
     '    return (it.variante.codigo_barras || "").trim() === lido',
     '    return true'),

    ("o leitor nao duplicando quando bipam duas vezes",
     "web/rotas_tela.py",
     "  if (escolhidos.has(it.variante.id)) return;   // bipou duas vezes: não duplica",
     "  if (false) return;"),

    # ------------------------------------------------------ gerador de SKU
    # SKU em uso esta em planilha, em etiqueta ja impressa e na cabeca de quem
    # trabalha na loja. Sobrescrever quebra os tres de uma vez, em silencio.
    ("o SKU que ja existe nao sendo tocado",
     "etiquetas/skus.py",
     "        if atual:",
     "        if False:"),

    # SKU repetido faz pegar o produto errado no estoque — e, se virar codigo de
    # barras depois, bipa errado no caixa.
    ("o desvio de SKU repetido",
     "etiquetas/skus.py",
     "            if candidato and candidato.upper() not in usados:",
     "            if candidato:"),

    # Comparar sem normalizar caixa faz o desvio falhar justamente quando a loja
    # ja tem o SKU escrito em minusculas.
    ("a colisao ignorando maiusculas",
     "etiquetas/skus.py",
     "    usados = {str(s).strip().upper() for s in (ja_usados or ()) if str(s).strip()}",
     "    usados = {str(s).strip() for s in (ja_usados or ()) if str(s).strip()}"),

    # Produto sem fornecedor, tipo nem variante existe de verdade em catalogo
    # importado as pressas. Gerar "0001" pra ele e dar um SKU que nao diz nada.
    ("o produto sem texto sendo pulado em vez de virar numero puro",
     "etiquetas/skus.py",
     "        if not sku or not any(c.isalpha() for c in sku):",
     "        if not sku:"),

    # O acento vira lixo na fonte da impressora termica e no Code 128.
    ("o acento saindo do SKU",
     "etiquetas/skus.py",
     "    sem_acento = \"\".join(\n        c for c in unicodedata.normalize(\"NFD\", str(texto))\n        if unicodedata.category(c) != \"Mn\")",
     "    sem_acento = str(texto)"),

    # Medido: "M / Preto" saia "MPRE", colado e ilegivel.
    ("a estrutura da variante sendo preservada",
     "etiquetas/skus.py",
     "        pecas[nome] = (normalizar_variante(bruto, letras) if nome == \"variante\"\n                       else normalizar(bruto, letras))",
     "        pecas[nome] = normalizar(bruto, letras)"),

    # ---------------------------------------- o filtro do que falta no cadastro
    # Uma pagina so nao serve: o Shopify devolve 50 produtos e talvez 2 estejam
    # sem codigo. O lojista veria 2 e concluiria que sao todos na loja inteira.
    ("a busca filtrada continuando pelas paginas seguintes",
     "web/rotas_api.py",
     "        if not filtro or not tem_mais or len(itens) >= alvo:\n            break",
     "        break"),

    # Dizer "3 sem codigo" sem dizer "entre os 400 que varri" e deixar o lojista
    # achar que sao 3 na loja toda.
    ("a resposta dizendo entre quantos procurou",
     "web/rotas_api.py",
     '        "varridos": vistos if filtro else None,',
     '        "varridos": None,'),

    # O teto existe pro caso oposto: loja onde quase tudo tem codigo faria isso
    # varrer 8 mil produtos e estourar o tempo da requisicao.
    ("o teto de paginas da busca filtrada",
     "web/rotas_api.py",
     "        if paginas >= PAGINAS_POR_FILTRO:\n            break",
     "        pass"),

    # Espaco em branco aparece preenchido na planilha e nao serve pra nada.
    ("o espaco em branco contando como cadastro vazio",
     "loja/catalogo.py",
     '    "sem_codigo": lambda it: not _texto(\n        (it.get("variante") or {}).get("codigo_barras")).strip(),',
     '    "sem_codigo": lambda it: not _texto(\n        (it.get("variante") or {}).get("codigo_barras")),'),

    # Filtro desconhecido vem da querystring. Tela antiga mandando nome que nao
    # existe mais deve ver o catalogo inteiro, nao uma tela de erro.
    ("o filtro desconhecido devolvendo tudo em vez de quebrar",
     "loja/catalogo.py",
     "    return [i for i in (itens or []) if regra(i)] if regra else list(itens or [])",
     "    return [i for i in (itens or []) if FILTROS[filtro](i)]"),

    # -------------------------------------------- o registro de desfazer
    # Mesma falha do IDOR de leitura, com consequencia pior: aqui o vizinho nao
    # leria o alheio, ele DESFARIA a escrita do alheio.
    ("o filtro de loja ao ler o lote de desfazer",
     "dados/gravacoes.py",
     "                WHERE loja_id = ? AND lote = ? AND desfeito_em IS NULL\n             ORDER BY id\"\"\", (dono, str(lote))).fetchall()",
     "                WHERE lote = ? AND desfeito_em IS NULL\n             ORDER BY id\"\"\", (str(lote),)).fetchall()"),

    ("o filtro de loja ao marcar o lote como desfeito",
     "dados/gravacoes.py",
     "                WHERE loja_id = ? AND lote = ? AND desfeito_em IS NULL\"\"\",\n            (agora(), dono, str(lote)))",
     "                WHERE lote = ? AND desfeito_em IS NULL\"\"\",\n            (agora(), str(lote)))"),

    # Sem o valor anterior nao existe desfazer — e sem desfazer o gerador nao
    # pode subir, porque um bug nosso mexe no catalogo de quem paga.
    ("o valor ANTERIOR sendo guardado",
     "dados/gravacoes.py",
     "    linhas = [(str(v), str(antigo or \"\"), str(novo or \"\"))",
     "    linhas = [(str(v), \"\", str(novo or \"\"))"),

    # Lista fechada: se alguem tentar gravar `price` por engano, o erro tem que
    # aparecer aqui e nao na loja do lojista.
    ("a lista fechada de campos gravaveis",
     "dados/gravacoes.py",
     "    if campo not in CAMPOS_GRAVAVEIS:",
     "    if False:"),

    # O prazo e o que impede isto de virar uma copia permanente do catalogo
    # alheio. Ver a politica de privacidade, que promete 30 dias.
    ("o prazo de guarda do registro de desfazer",
     "dados/gravacoes.py",
     "            (\"-%d days\" % max(1, int(dias)),))",
     "            (\"-99999 days\",))"),

    # Marcar em vez de apagar: desfazer duas vezes sobrescreveria um valor que o
    # lojista pode ter posto a mao depois.
    ("o lote desfeito saindo da fila",
     "dados/gravacoes.py",
     "                WHERE loja_id = ? AND desfeito_em IS NULL\n             GROUP BY lote, campo",
     "                WHERE loja_id = ?\n             GROUP BY lote, campo"),

    # -------------------------------------------- as rotas do gerador de SKU
    # A REGRA que decide o desenho das tres rotas: o servidor calcula o que
    # grava, o navegador so confirma QUAIS. Sem o filtro de confirmadas, o
    # aplicar gravaria tudo que a previa propos — inclusive o que o lojista
    # desmarcou olhando a tabela.
    ("o aplicar gravando SO o que o lojista confirmou",
     "web/rotas_api.py",
     "                and str(l[\"item\"][\"variante\"].get(\"id\")) in confirmadas]",
     "                ]"),

    # Regra que vem de fora e nao se discute: SKU em uso esta em planilha, em
    # etiqueta ja impressa e na cabeca de quem trabalha na loja.
    ("o aplicar nao tocando em quem ja tem SKU",
     "web/rotas_api.py",
     "                if l[\"sku\"] and not l[\"pulado\"]",
     "                if l[\"sku\"]"),

    # Mandar nao e gravar. Anotar "desfazer" para o que nao aconteceu faria o
    # desfazer sobrescrever um valor que o lojista pos a mao.
    ("o registro de desfazer saindo do que o Shopify CONFIRMOU",
     "web/rotas_api.py",
     "        for variante_id, sku in escrita.variantes_gravadas(resposta).items():\n            gravados.append((variante_id, anteriores.get(variante_id, \"\"), sku))",
     "        for pid, vid, sku in [(produto_id, v, s) for v, s in pares]:\n            gravados.append((vid, anteriores.get(vid, \"\"), sku))"),

    # O Shopify responde 200 com erro dentro. Ignorar os motivos faria o app
    # registrar como gravado o que foi recusado.
    ("as recusas do Shopify barrando o registro de desfazer",
     "web/rotas_api.py",
     "        motivos = escrita.erros_da_escrita(resposta)\n        if motivos:\n            falhas.extend(motivos)\n            continue\n        # Só o que o Shopify CONFIRMOU",
     "        motivos = []\n        # Só o que o Shopify CONFIRMOU"),

    # Com `or`, o lojista que escolhesse "todos os produtos" (string vazia)
    # teria a escolha trocada em silencio por "sem SKU".
    ("a escolha de filtro do lojista sendo respeitada",
     "web/rotas_api.py",
     "            \"sem_sku\" if filtro is None else str(filtro))",
     "            filtro or \"sem_sku\")"),

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
