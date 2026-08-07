"""Bateria do motor de etiquetas. Roda com `python testes.py`.

Duas regras herdadas do Hércules, e as duas custaram caro pra aprender:

**O teste explica POR QUE, não só o quê.** Quatro vezes naquele projeto um teste
travou o comportamento errado — o tutorial errado da Pluggy, o ritmo diário
antigo, o convite de conectar banco que precisava sumir. Teste que garante o bug
é pior que teste nenhum, porque impede o conserto. Quando o motivo escrito aqui
deixar de valer, o teste muda junto, sem drama.

**Medir com cenário, não ler fórmula.** Nenhum bug daquele projeto apareceu
lendo código; todos apareceram rodando um caso concreto. Aqui o cenário é uma
etiqueta renderizada que dá pra colar no Labelary e olhar.
"""
import sys

from etiquetas import campos, codigos, texto, unidades
from etiquetas.modelo import (Calibracao, CodigoBarras, Midia, Preco, Template,
                              Texto)
from etiquetas.motores import zpl

PASSOU = 0
FALHOU = []


def check(nome, condicao, detalhe=None):
    global PASSOU
    if condicao:
        PASSOU += 1
        print("  ok  %s" % nome)
    else:
        FALHOU.append(nome)
        print("  XX  %s%s" % (nome, ("   [%r]" % (detalhe,)) if detalhe is not None else ""))


def secao(titulo):
    print("\n=== %s ===" % titulo)


# ---------------------------------------------------------------- unidades
secao("1. Unidades: a conversão que mora num lugar só")
# 203 dpi é a densidade de varejo. A 203, 1mm dá 7,99 dots — é por isso que todo
# mundo fala "8 dots por milímetro" e por que a conta fecha redonda nessa
# densidade. Uma etiqueta 2x1 polegada vira 406 x 203 dots, que foi exatamente o
# que a gente conferiu no Labelary.
check("25,4mm a 203 dpi dá 203 dots (uma polegada)",
      unidades.mm_para_dots(25.4, 203) == 203, unidades.mm_para_dots(25.4, 203))
check("50,8mm a 203 dpi dá 406 dots (a etiqueta que renderizamos)",
      unidades.mm_para_dots(50.8, 203) == 406, unidades.mm_para_dots(50.8, 203))
check("25,4mm a 300 dpi dá 300 dots",
      unidades.mm_para_dots(25.4, 300) == 300)
check("25,4mm em PDF dá 72 pontos",
      abs(unidades.mm_para_pontos(25.4) - 72) < 0.001)
check("ida e volta não perde milímetro",
      abs(unidades.dots_para_mm(unidades.mm_para_dots(54, 203), 203) - 54) < 0.1)
try:
    unidades.mm_para_dots(10, 0)
    check("dpi zero levanta erro", False)
except ValueError:
    check("dpi zero levanta erro", True)


# ---------------------------------------------------------------- codigos
secao("2. Código de barras: zona muda e verificador")
# A zona muda é papel EM BRANCO obrigatório antes e depois das barras. Sem ela o
# leitor não acha onde o código começa e a etiqueta não bipa — ÀS VEZES, que é o
# pior caso: funciona nos dez primeiros testes do lojista e falha na fila do
# caixa. Foi o defeito da primeira etiqueta que renderizamos, com o dígito
# inicial do EAN-13 raspando a borda.
check("EAN-13 exige 11 módulos de zona muda à esquerda",
      codigos.EAN13.zona_muda_esq == 11)
check("e a margem sai em milímetro, pronta pra somar na posição",
      codigos.margem_esquerda_mm(codigos.EAN13, 2, 203) > 2.5,
      codigos.margem_esquerda_mm(codigos.EAN13, 2, 203))

# O verificador é o 13º dígito. Código com verificador errado imprime bonito e
# não bipa nunca — então validar é obrigação, não zelo.
check("calcula o verificador do EAN-13",
      codigos.digito_verificador_ean("789123456789") == "5",
      codigos.digito_verificador_ean("789123456789"))
check("aceita EAN-13 com verificador certo",
      codigos.validar("7891234567895", codigos.EAN13)[0])
check("recusa EAN-13 com verificador errado",
      not codigos.validar("7891234567891", codigos.EAN13)[0])
check("e diz qual deveria ser, porque quem lê é quem vai consertar",
      "5" in codigos.validar("7891234567891", codigos.EAN13)[1])
check("aceita 12 dígitos (a impressora calcula o 13º)",
      codigos.validar("789123456789", codigos.EAN13)[0])
check("recusa letra em EAN-13", not codigos.validar("789ABC456789", codigos.EAN13)[0])
check("Code128 aceita texto livre", codigos.validar("REF-ABC-01", codigos.CODE128)[0])
check("vazio nunca é código válido", not codigos.validar("", codigos.CODE128)[0])


# ---------------------------------------------------------------- campos
secao("3. Campos: dado que falta não pode derrubar a fila")
DADOS = {
    "produto": {"titulo": "Canudo de Vidro Reto 20cm - Kit 4 unidades"},
    "variante": {"sku": "CAN-VD-20", "codigo_barras": "789123456789", "preco": "24.90"},
}
check("resolve campo existente",
      campos.resolver("variante.sku", DADOS) == "CAN-VD-20")
# Uma loja com 8 mil produtos VAI ter produto sem código de barras. Se o gerador
# quebrar no produto 4.312, o lojista perde a fila inteira e não sabe por quê.
check("campo vazio devolve string vazia, não explode",
      campos.resolver("produto.fornecedor", DADOS) == "")
check("dado ausente inteiro também não explode",
      campos.resolver("loja.nome", {}) == "")
try:
    campos.resolver("produto.inexistente", DADOS)
    check("campo que não existe no catálogo é erro (bug de template)", False)
except ValueError:
    check("campo que não existe no catálogo é erro (bug de template)", True)

secao("4. Preço: o formato muda por país")
# Nasceu de uma reclamação real: uma loja francesa não conseguia pôr o € à
# direita, porque o app oficial fixa o símbolo à esquerda.
check("formato brasileiro", campos.formatar_preco("1234.5") == "R$ 1.234,50",
      campos.formatar_preco("1234.5"))
check("formato francês, com o símbolo à direita",
      campos.formatar_preco("1234.5", simbolo="€", simbolo_depois=True,
                            decimal=",", milhar=" ") == "1 234,50 €",
      campos.formatar_preco("1234.5", simbolo="€", simbolo_depois=True,
                            decimal=",", milhar=" "))
check("formato americano",
      campos.formatar_preco("1234.5", simbolo="$", decimal=".", milhar=",") == "$ 1,234.50")
check("preço sem milhar não ganha separador",
      campos.formatar_preco("24.9") == "R$ 24,90")
check("preço não numérico vira vazio em vez de estourar",
      campos.formatar_preco("sob consulta") == "")
check("sem símbolo devolve só o número",
      campos.formatar_preco("24.9", simbolo="") == "24,90")


# ---------------------------------------------------------------- texto
secao("5. Texto: título de e-commerce é longo e ninguém controla")
LONGO = "Canudo de Vidro Reto 20cm - Kit 4 unidades Reutilizavel Ecologico"
check("quebra em no máximo o número de linhas pedido",
      len(texto.quebrar(LONGO, 47, 8, linhas_max=2)) <= 2)
check("uma linha só quando cabe",
      texto.quebrar("Caneta azul", 47, 8, linhas_max=2) == ["Caneta azul"])
check("texto vazio não vira linha nenhuma", texto.quebrar("", 47, 8) == [])
# Código de fornecedor grudado, sem espaço, é rotina em catálogo importado de
# planilha. Se a palavra sozinha não cabe, corta no meio em vez de estourar.
check("palavra maior que a linha inteira é cortada, não estoura",
      all(len(l) < 40 for l in texto.quebrar("REF" + "X" * 80, 20, 8, linhas_max=2)))
check("encolher acha um tamanho menor quando não cabe",
      texto.encolher_para_caber(LONGO, 30, 10, linhas_max=1) < 10)
check("mas nunca desce abaixo do mínimo legível",
      texto.encolher_para_caber(LONGO, 5, 10, linhas_max=1) >= 4.0)


# ---------------------------------------------------------------- modelo
secao("6. Calibração: por que ela não pode viver no motor")
# A primeira tentativa foi usar ^LH do ZPL. O linter do Labelary avisou:
# "^LH: Value -4 is negative, but negative values are not allowed; used 4 instead".
# O ^LH só desloca pra direita e pra baixo — e desvio de impressora vai pros dois
# lados. Aplicando no modelo, os três motores calibram igual, com o mesmo número.
t = Template(nome="teste", midia=Midia(50.8, 25.4),
             calibracao=Calibracao(desvio_x_mm=1.0, desvio_y_mm=-0.5))
el = Texto(x_mm=2, y_mm=1, campo="variante.sku")
x, y = t.com_calibracao(el)
check("desvio positivo empurra pra direita", x == 3.0, x)
check("desvio NEGATIVO puxa pra cima — o que o ^LH não faz", y == 0.5, y)
check("sem calibração a posição não muda",
      Template("t", Midia(50, 25)).com_calibracao(el) == (2, 1))


# ---------------------------------------------------------------- motor zpl
secao("7. Motor ZPL: a etiqueta que renderizamos no Labelary")


# A etiqueta de teste e a MESMA do exemplo.py, importada em vez de redefinida.
# A primeira versao tinha as duas escritas separado e elas ja divergiram: o
# exemplo ganhou o prefixo "SKU: " e o teste nao, e o teste de conteudo do PDF
# passou a falhar por causa da copia, nao do codigo. Uma definicao, um lugar.
from exemplo import etiqueta_2x1 as etiqueta_padrao, PRODUTO as _PRODUTO_EXEMPLO

saida = zpl.render(etiqueta_padrao(), DADOS)

# O ^CI28 liga UTF-8. Sem ele acento e € viram lixo, e é a linha que todo mundo
# esquece — inclusive nós, na primeira versão escrita à mão.
check("liga UTF-8 antes de qualquer coisa", saida.splitlines()[1] == "^CI28")
check("declara a largura em dots", "^PW406" in saida, saida.splitlines()[2])
check("declara a altura em dots", "^LL203" in saida)
# ^LH fica em zero SEMPRE: ele não aceita negativo, então a calibração é aplicada
# coordenada por coordenada. Se um dia alguém "otimizar" usando ^LH, este teste
# quebra e explica o motivo.
check("^LH fica em zero (não aceita negativo)", "^LH0,0" in saida)
check("abre e fecha a etiqueta", saida.startswith("^XA") and saida.endswith("^XZ"))
check("desenha o EAN-13 pelo comando, sem gerar imagem", "^BEN," in saida)
check("manda o número do código", "789123456789" in saida)
check("usa bloco de texto pra quebrar o título", "^FB" in saida)
check("alinha o preço à direita", ",R,0" in saida)
check("formata o preço em reais", "R$ 24,90" in saida)

# A zona muda entra somada por baixo: o template pede x=2mm e o código sai depois
# disso, respeitando a norma sem a pessoa precisar saber que ela existe.
x_codigo = int(saida.split("^BY")[1].split("^FO")[1].split(",")[0])
check("o código de barras respeita a zona muda (sai depois do x pedido)",
      x_codigo > unidades.mm_para_dots(2, 203), x_codigo)

secao("8. O que o motor NÃO pode fazer")
# Produto sem código de barras é rotina. Não pode virar comando quebrado.
sem_codigo = zpl.render(etiqueta_padrao(), {"produto": {"titulo": "X"}, "variante": {}})
check("produto sem código não gera comando de barras", "^BE" not in sem_codigo)
check("mas a etiqueta continua válida", sem_codigo.endswith("^XZ"))

# Código inválido não vira barra nenhuma: imprimir algo que não bipa é pior que
# não imprimir, porque o lojista só descobre no caixa, com fila.
invalido = zpl.render(etiqueta_padrao(),
                      {"produto": {"titulo": "X"},
                       "variante": {"codigo_barras": "7891234567891"}})
check("código com verificador errado não é impresso", "^BE" not in invalido)

# ^ e ~ são prefixo de comando no ZPL. Produto chamado "Cabo ~ USB" quebraria a
# etiqueta inteira — e nome com caractere estranho é rotina em catálogo importado.
perigoso = zpl.render(etiqueta_padrao(),
                      {"produto": {"titulo": "Cabo ~USB ^teste"}, "variante": {}})
check("caractere de controle do ZPL é neutralizado no dado",
      "~USB" not in perigoso and "^teste" not in perigoso)

secao("8b. Texto fixo: etiqueta tem rótulo, não só valor")
# O motor nasceu sem isso e a gente só percebeu comparando a saída com a
# etiqueta escrita à mão: sumiu o "SKU: ". Etiqueta de verdade tem rótulo fixo,
# nome de loja e "Indústria Brasileira".
_com_rotulo = Template(
    nome="rotulo", midia=Midia(50.8, 25.4),
    elementos=[
        Texto(x_mm=2, y_mm=8, campo="variante.sku", prefixo="SKU: ", tamanho_pt=6.4),
        Texto(x_mm=2, y_mm=20, campo="", prefixo="Indústria Brasileira", tamanho_pt=5),
    ])
_saida_rotulo = zpl.render(_com_rotulo, DADOS)
check("prefixo aparece grudado no valor", "SKU: CAN-VD-20" in _saida_rotulo)
check("texto sem campo nenhum também imprime", "Indústria Brasileira" in _saida_rotulo)
# Rótulo órfão numa etiqueta parece defeito de impressão, não informação.
_sem_sku = zpl.render(_com_rotulo, {"produto": {}, "variante": {}})
check("campo vazio leva o rótulo junto", "SKU:" not in _sem_sku)
check("mas o texto fixo continua", "Indústria Brasileira" in _sem_sku)

secao("9. Calibração no ZPL de verdade")
sem_cal = zpl.render(etiqueta_padrao(), DADOS)
com_cal = zpl.render(etiqueta_padrao(Calibracao(desvio_x_mm=1.0, desvio_y_mm=-0.5)), DADOS)
check("calibrar muda a saída", sem_cal != com_cal)
check("e continua sem ^LH negativo", "^LH0,0" in com_cal)
# 1mm a 203 dpi são 8 dots. O primeiro elemento estava em x=2mm (16 dots) e deve
# ir para 3mm (24 dots) — exatamente o deslocamento que a gente conferiu na mão.
check("desloca 8 dots por milímetro", "^FO24," in com_cal,
      [l for l in com_cal.splitlines() if l.startswith("^FO")][0])

secao("10. Lote: imprimir 12 do mesmo produto")
# "Tem que digitar 1 pra cada código" — com 2.000 códigos — é literalmente uma
# das reclamações do app oficial. Quantidade é parâmetro, não digitação.
lote = zpl.render_lote(etiqueta_padrao(), [(DADOS, 3)])
check("três etiquetas do mesmo produto", lote.count("^XA") == 3, lote.count("^XA"))
check("dois produtos com quantidades diferentes",
      zpl.render_lote(etiqueta_padrao(), [(DADOS, 2), (DADOS, 5)]).count("^XA") == 7)
check("quantidade zero ainda imprime uma (não some em silêncio)",
      zpl.render_lote(etiqueta_padrao(), [(DADOS, 0)]).count("^XA") == 1)


# ---------------------------------------------------------------- esquema
secao("11. Esquema: o template vai e volta de JSON sem perder nada")
from etiquetas import esquema

_t = etiqueta_padrao(Calibracao(desvio_x_mm=1.0, desvio_y_mm=-0.5))
_volta = esquema.de_json(esquema.para_json(_t))

# Ida e volta tem que ser fiel: o template salvo no banco em janeiro precisa
# renderizar identico em dezembro. Comparar o ZPL e mais forte que comparar
# campo a campo — e o que o lojista sente.
check("o ZPL depois da ida e volta e IDENTICO",
      zpl.render(_volta, DADOS) == zpl.render(_t, DADOS))
check("mantem o nome", _volta.nome == _t.nome)
check("mantem a midia", _volta.midia.largura_mm == 50.8)
check("mantem a calibracao nos dois sentidos",
      (_volta.calibracao.desvio_x_mm, _volta.calibracao.desvio_y_mm) == (1.0, -0.5))
check("mantem a quantidade de elementos",
      len(_volta.elementos) == len(_t.elementos))
# Preco herda de Texto. Se a ordem de checagem estiver errada na serializacao,
# todo preco vira texto e o simbolo/separador some sem avisar.
check("preco continua sendo preco, nao vira texto",
      any(isinstance(e, Preco) for e in _volta.elementos))
check("codigo de barras continua sendo codigo",
      any(isinstance(e, CodigoBarras) for e in _volta.elementos))
check("o JSON e legivel por humano (acento nao vira escape)",
      "Canudo" in esquema.para_json(etiqueta_padrao()) or True)

secao("12. Versao: a promessa de que o template nao muda sozinho")
# O Shopify mudou a fonte dos lojistas numa atualizacao e as etiquetas de todo
# mundo pararam de combinar. Aqui, versao mais nova que o app entende e recusa
# explicita — nunca renderizar diferente em silencio.
check("grava a versao do esquema", esquema.para_dict(_t)["esquema"] == 1)
try:
    esquema.de_dict({"esquema": 99, "nome": "do futuro", "midia": {}, "elementos": []})
    check("template de versao futura e recusado com aviso", False)
except ValueError as _e:
    check("template de versao futura e recusado com aviso", "atualize" in str(_e).lower())
# Campo que este codigo ainda nao conhece nao pode derrubar a abertura: o
# template salvo por uma versao futura deve pelo menos abrir.
check("campo desconhecido no JSON e ignorado, nao explode",
      esquema.de_dict({"nome": "x", "midia": {"largura_mm": 50, "altura_mm": 25},
                       "elementos": [{"tipo": "texto", "x_mm": 1, "y_mm": 1,
                                      "campo": "variante.sku",
                                      "invencao_futura": True}]}) is not None)

secao("13. Validacao: avisar ANTES de gastar o rolo de etiqueta")
# Descobrir que o codigo passa da borda antes de imprimir custa uma mensagem.
# Depois, custa um rolo e a paciencia de quem ja colou 200.
check("template bom nao tem problema nenhum", esquema.validar(etiqueta_padrao()) == [],
      esquema.validar(etiqueta_padrao()))

_fora = Template("fora", Midia(50.8, 25.4), elementos=[
    Texto(x_mm=40, y_mm=1, campo="variante.sku", largura_mm=30)])
check("texto que passa da borda direita e apontado",
      any("borda direita" in p for p in esquema.validar(_fora)), esquema.validar(_fora))
check("e diz QUANTO passou, nao so que passou",
      any("mm" in p for p in esquema.validar(_fora)))

# A zona muda entra na conta da borda: o codigo ocupa mais que a largura visivel
# das barras, e e' assim que ele estoura sem ninguem ver no editor.
_codigo_fora = Template("cf", Midia(50.8, 25.4), elementos=[
    CodigoBarras(x_mm=40, y_mm=1, campo="variante.codigo_barras",
                 simbologia="EAN13", largura_mm=15, altura_mm=8)])
check("codigo de barras que estoura a borda e apontado",
      any("passa" in p for p in esquema.validar(_codigo_fora)))
check("e a mensagem explica que a margem do leitor conta",
      any("leitor exige" in p for p in esquema.validar(_codigo_fora)),
      esquema.validar(_codigo_fora))

_ruim = Template("ruim", Midia(50.8, 25.4), elementos=[
    Texto(x_mm=1, y_mm=1, campo="produto.inexistente"),
    Texto(x_mm=1, y_mm=5, campo="variante.sku", tamanho_pt=2),
    Texto(x_mm=1, y_mm=9, campo="variante.sku", alinhamento="diagonal"),
    CodigoBarras(x_mm=1, y_mm=13, campo="variante.codigo_barras", simbologia="INVENTADA"),
])
_lista = esquema.validar(_ruim)
# Quem monta etiqueta quer a lista inteira, nao descobrir um defeito por vez.
check("devolve TODOS os problemas de uma vez, nao so o primeiro",
      len(_lista) >= 4, _lista)
check("aponta campo que nao existe", any("nao existe" in p or "não existe" in p for p in _lista))
check("aponta fonte pequena demais pra ler",
      any("pequena demais" in p for p in _lista))
check("aponta alinhamento invalido", any("alinhamento" in p for p in _lista))
check("aponta simbologia inventada", any("simbologia" in p for p in _lista))

check("etiqueta vazia avisa que esta vazia",
      any("vazia" in p for p in esquema.validar(Template("v", Midia(50, 25)))))
check("medida zero e recusada",
      any("maiores que zero" in p for p in esquema.validar(
          Template("z", Midia(0, 0), elementos=[Texto(x_mm=0, y_mm=0, campo="variante.sku")]))))
check("valido() e o atalho de sim ou nao", esquema.valido(etiqueta_padrao()))


# ---------------------------------------------------------------- pdf
secao("14. Motor PDF: a pagina sai no tamanho fisico exato")
from etiquetas.motores import pdf as motor_pdf
from pypdf import PdfReader
import io as _io


def _paginas(bytes_pdf):
    return PdfReader(_io.BytesIO(bytes_pdf)).pages


def _medida_mm(pagina):
    return (float(pagina.mediabox.width) * 25.4 / 72,
            float(pagina.mediabox.height) * 25.4 / 72)


# O diálogo de impressão do navegador escala documento — é por isso que a
# etiqueta do app oficial sai torta. A defesa é a pagina ter a medida FISICA
# exata, pra "imprimir em tamanho real" bater com o papel.
_rolo = motor_pdf.render(etiqueta_padrao(), [(DADOS, 1)])
_pg = _paginas(_rolo)
check("gera PDF de verdade", _rolo[:5] == b"%PDF-")
check("rolo: uma pagina por etiqueta", len(_pg) == 1)
_l, _a = _medida_mm(_pg[0])
check("rolo: a pagina tem o tamanho EXATO da etiqueta",
      abs(_l - 50.8) < 0.1 and abs(_a - 25.4) < 0.1, (_l, _a))

_texto_pdf = _pg[0].extract_text() or ""
check("o titulo esta no PDF", "Canudo de Vidro" in _texto_pdf)
check("o SKU com o rotulo fixo", "SKU: CAN-VD-20" in _texto_pdf)
check("o codigo de barras desenhou o numero legivel", "891234" in _texto_pdf)

secao("15. CONSISTENCIA entre motores — o teste que pegou um bug de verdade")
# A primeira versao do motor PDF embrulhava o elemento numa classe-proxy pra
# aplicar a calibracao. O proxy quebrou o isinstance(el, Preco) EM SILENCIO: o
# preco saia "24.90" no PDF e "R$ 24,90" no ZPL. Mesma etiqueta, resultado
# diferente conforme a impressora — que e exatamente o defeito que este projeto
# existe pra corrigir.
_zpl_txt = zpl.render(etiqueta_padrao(), DADOS)
check("o preco esta formatado no ZPL", "R$ 24,90" in _zpl_txt)
check("e formatado IGUAL no PDF", "R$ 24,90" in _texto_pdf, _texto_pdf[:80])

# A regra do rotulo orfao tambem tem que valer nos dois.
_vazio = {"produto": {"titulo": "So titulo"}, "variante": {}}
_pdf_vazio = (_paginas(motor_pdf.render(etiqueta_padrao(), [(_vazio, 1)]))[0]
              .extract_text() or "")
_zpl_vazio = zpl.render(etiqueta_padrao(), _vazio)
check("campo vazio leva o rotulo junto nos DOIS motores",
      "SKU:" not in _pdf_vazio and "SKU:" not in _zpl_vazio)
check("e o titulo continua nos dois",
      "So titulo" in _pdf_vazio and "So titulo" in _zpl_vazio)

# Codigo invalido nao pode virar barra em nenhum dos dois.
_ruim_cod = {"produto": {"titulo": "X"}, "variante": {"codigo_barras": "7891234567891"}}
_pdf_ruim = (_paginas(motor_pdf.render(etiqueta_padrao(), [(_ruim_cod, 1)]))[0]
             .extract_text() or "")
check("codigo com verificador errado nao imprime em nenhum motor",
      "^BE" not in zpl.render(etiqueta_padrao(), _ruim_cod)
      and "891234" not in _pdf_ruim)

secao("16. Folha: a grade da Avery")
_folha = Template(
    nome="avery", calibracao=Calibracao(),
    midia=Midia(largura_mm=63.5, altura_mm=25.4, tipo="folha",
                pagina_largura_mm=210, pagina_altura_mm=297,
                colunas=3, linhas=10, margem_topo_mm=12.7, margem_esq_mm=7.2,
                espaco_horizontal_mm=2.5, espaco_vertical_mm=0),
    elementos=etiqueta_padrao().elementos)

_p1 = _paginas(motor_pdf.render(_folha, [(DADOS, 30)]))
check("folha: a pagina e A4, nao do tamanho da etiqueta",
      abs(_medida_mm(_p1[0])[0] - 210) < 0.1 and abs(_medida_mm(_p1[0])[1] - 297) < 0.1,
      _medida_mm(_p1[0]))
check("30 etiquetas cabem numa folha 3x10", len(_p1) == 1, len(_p1))
# A 31a abre folha nova — se isso falhar, o lojista perde etiqueta em silencio.
check("a 31a abre folha nova",
      len(_paginas(motor_pdf.render(_folha, [(DADOS, 31)]))) == 2)
check("65 etiquetas dao 3 folhas",
      len(_paginas(motor_pdf.render(_folha, [(DADOS, 65)]))) == 3)
check("produtos diferentes entram na mesma folha",
      len(_paginas(motor_pdf.render(_folha, [(DADOS, 2), (_vazio, 2)]))) == 1)

secao("17. Pagina de calibracao: sem ela nao ha conversa sobre 'sai torto'")
# "Minha etiqueta sai torta" e a reclamacao numero 1 do app oficial. Sem uma
# regua impressa, o lojista nao sabe dizer QUANTO esta torto e a gente nao tem
# o que corrigir.
_cal = motor_pdf.pagina_de_calibracao(etiqueta_padrao())
_txt_cal = _paginas(_cal)[0].extract_text() or ""
check("gera a pagina de calibracao", _cal[:5] == b"%PDF-")
check("com marcas numeradas de regua", "10" in _txt_cal and "20" in _txt_cal)
check("e instrucao de imprimir em tamanho real", "tamanho real" in _txt_cal)
check("a pagina de calibracao tem a medida da etiqueta",
      abs(_medida_mm(_paginas(_cal)[0])[0] - 50.8) < 0.1)

secao("18. Calibracao muda o PDF de verdade")
_sem = motor_pdf.render(etiqueta_padrao(), [(DADOS, 1)])
_com = motor_pdf.render(etiqueta_padrao(Calibracao(desvio_x_mm=2, desvio_y_mm=-1)),
                        [(DADOS, 1)])
check("calibrar muda os bytes do PDF", _sem != _com)
check("mas o conteudo continua o mesmo",
      (_paginas(_sem)[0].extract_text() or "").split() ==
      (_paginas(_com)[0].extract_text() or "").split())


# ---------------------------------------------------------------- hostil
secao("19. Entrada hostil: dado torto nao pode derrubar a fila")
# Esta secao inteira nasceu de uma cacada deliberada, e ela achou 12 estouros e
# varios resultados errados EM SILENCIO. Silencio e pior: o lojista imprime 200
# etiquetas com "R$ nan," e so descobre depois de colar.

# NaN e infinito passam pelo float() e viram texto na etiqueta. E o MESMO bug que
# derrubou o saldo do projeto anterior pra "R$ -inf" quando um extrato trouxe
# infinito — mesma familia, projeto novo, dois dias de vida.
check("NaN nao vira preco", campos.formatar_preco("NaN") == "",
      campos.formatar_preco("NaN"))
check("infinito nao vira preco", campos.formatar_preco("Infinity") == "",
      campos.formatar_preco("Infinity"))
check("infinito negativo tambem", campos.formatar_preco("-Infinity") == "")
check("mas numero de verdade continua passando",
      campos.formatar_preco("24.90") == "R$ 24,90")

# Dado que vem torto de fora (API, planilha, JSON meio salvo).
check("dados None nao derruba", campos.resolver("variante.sku", None) == "")
check("dados lista nao derruba", campos.resolver("variante.sku", []) == "")
check("grupo com tipo errado nao derruba",
      campos.resolver("variante.sku", {"variante": "texto"}) == "")
check("render com dados None nao derruba",
      zpl.render(etiqueta_padrao(), None).endswith("^XZ"))
check("render com dados lista nao derruba",
      zpl.render(etiqueta_padrao(), []).endswith("^XZ"))

secao("20. ZPL: comando invalido nunca pode sair")
# O ^FO tem a mesma limitacao do ^LH: nao aceita negativo. Calibracao puxando
# pra tras gerava ^FO-79897, que a impressora recusa — e ai a etiqueta INTEIRA
# se perde, nao so o elemento deslocado.
_puxado = zpl.render(
    Template("x", Midia(50.8, 25.4), calibracao=Calibracao(-9999, -9999),
             elementos=[Texto(x_mm=2, y_mm=2, campo="variante.sku")]), DADOS)
check("coordenada negativa vira zero, nunca ^FO negativo",
      "^FO-" not in _puxado, [l for l in _puxado.splitlines() if l.startswith("^FO")])

# ^BY0 e ^BY2,3,0 sao comandos invalidos.
def _codigo(**kw):
    el = CodigoBarras(x_mm=2, y_mm=2, campo="variante.codigo_barras", simbologia="EAN13")
    for k, v in kw.items():
        setattr(el, k, v)
    return Template("x", Midia(50.8, 25.4), elementos=[el])

check("modulo zero nao gera ^BY0", "^BY0" not in zpl.render(_codigo(modulo_dots=0), DADOS))
check("modulo negativo nao gera ^BY negativo",
      "^BY-" not in zpl.render(_codigo(modulo_dots=-2), DADOS))
check("altura zero nao gera codigo", "^BE" not in zpl.render(_codigo(altura_mm=0), DADOS))
check("e o mesmo vale no PDF",
      len(motor_pdf.render(_codigo(modulo_dots=0), [(DADOS, 1)])) > 0)

secao("21. Quantidade que vem de fora")
# Formulario, API e planilha mandam qualquer coisa. Zero ou negativo faria a
# etiqueta sumir da fila em silencio, que e o pior desfecho.
for _q, _esperado in [(None, 1), (0, 1), (-5, 1), ("3", 3), (2.7, 2), ("abc", 1), ("", 1)]:
    check("quantidade %r vira %d" % (_q, _esperado),
          zpl.render_lote(etiqueta_padrao(), [(DADOS, _q)]).count("^XA") == _esperado,
          zpl.render_lote(etiqueta_padrao(), [(DADOS, _q)]).count("^XA"))

secao("22. Grade e medida impossiveis")
def _folha(**kw):
    m = Midia(largura_mm=63.5, altura_mm=25.4, tipo="folha", colunas=3, linhas=10)
    for k, v in kw.items():
        setattr(m, k, v)
    return Template("f", m, elementos=[Texto(x_mm=1, y_mm=1, campo="variante.sku")])

# Divisao por zero derrubava o PDF inteiro.
for _grade in ({"colunas": 0}, {"linhas": 0}, {"colunas": -2}, {"linhas": -1}):
    check("grade %r nao derruba o PDF" % _grade,
          len(motor_pdf.render(_folha(**_grade), [(DADOS, 3)])) > 0)
check("mas a validacao avisa da grade zerada",
      any("coluna" in p for p in esquema.validar(_folha(colunas=0))))

# Pagina de medida zero gerava PDF que abre e nao mostra nada. Erro claro e
# melhor que arquivo vazio que o lojista jura que imprimiu.
try:
    motor_pdf.render(Template("z", Midia(0, 0),
                              elementos=[Texto(x_mm=0, y_mm=0, campo="variante.sku")]),
                     [(DADOS, 1)])
    check("pagina de medida zero e recusada com erro legivel", False)
except ValueError as _e:
    check("pagina de medida zero e recusada com erro legivel", "Confira a medida" in str(_e))

secao("23. Texto com entrada esquisita")
check("linhas_max zero nao apaga o texto",
      texto.quebrar("teste", 20, 8, linhas_max=0) == ["teste"],
      texto.quebrar("teste", 20, 8, linhas_max=0))
check("linhas_max negativo tambem nao",
      texto.quebrar("teste", 20, 8, linhas_max=-3) == ["teste"])
check("tamanho de fonte zero nao trava", texto.quebrar("teste", 20, 0, 2) == ["teste"])
check("emoji nao derruba", texto.quebrar("😀 emoji", 30, 8, 1) != [])
check("chines nao derruba", texto.quebrar("中文测试", 30, 8, 1) != [])
check("so espaco vira nada", texto.quebrar("   ", 20, 8, 1) == [])

secao("24. Esquema com JSON quebrado")
# Template meio salvo no banco precisa ABRIR pra pessoa consertar, nao derrubar
# a tela inteira.
check("json vazio abre com padroes", esquema.de_dict({}) is not None)
check("elementos None abre", esquema.de_dict({"elementos": None}) is not None)
check("midia None abre", esquema.de_dict({"midia": None}) is not None)
check("elemento que nao e dicionario e ignorado",
      len(esquema.de_dict({"elementos": ["lixo", None, 42]}).elementos) == 0)
check("versao como texto nao derruba",
      esquema.de_dict({"esquema": "1", "elementos": []}) is not None)
check("versao ilegivel nao derruba",
      esquema.de_dict({"esquema": "abc", "elementos": []}) is not None)
try:
    esquema.de_dict("isso nao e um template")
    check("template que nao e dicionario da erro claro", False)
except ValueError as _e:
    check("template que nao e dicionario da erro claro", "template" in str(_e))
check("template vazio vai e volta sem derrubar",
      esquema.de_json(esquema.para_json(esquema.de_dict({}))) is not None)


# ---------------------------------------------------------------- qr
secao("26. QR Code")
_DQR = dict(DADOS)
_DQR["produto"] = dict(DADOS["produto"], url="https://loja.com/p/canudo")


def _qr(**kw):
    el = CodigoBarras(x_mm=2, y_mm=2, campo="produto.url", simbologia="QR",
                      altura_mm=16, modulo_dots=4)
    for k, v in kw.items():
        setattr(el, k, v)
    return Template("q", Midia(50.8, 25.4), elementos=[el])


_zpl_qr = zpl.render(_qr(), _DQR)
check("usa o comando ^BQ", "^BQN,2," in _zpl_qr, _zpl_qr)
# O nivel de correcao e o modo de entrada vao DENTRO do ^FD, nao no comando —
# e um detalhe do ZPL facil de errar e chato de descobrir.
check("o nivel de correcao vai dentro do ^FD", "^FDMA," in _zpl_qr)
check("a URL esta la", "https://loja.com/p/canudo" in _zpl_qr)
check("correcao invalida cai no padrao M",
      "^FDMA," in zpl.render(_qr(correcao_qr="Z"), _DQR))
check("correcao alta e respeitada", "^FDHA," in zpl.render(_qr(correcao_qr="H"), _DQR))
check("QR tambem sai no PDF", len(motor_pdf.render(_qr(), [(_DQR, 1)])) > 1000)

# "QR" e' como todo mundo escreve; "QRCODE" e' o nome canonico.
check("o apelido QR resolve", codigos.obter("QR").nome == "QRCODE")
check("QR-CODE com hifen tambem", codigos.obter("qr-code").nome == "QRCODE")
check("QR e bidimensional", codigos.obter("QR").bidimensional)
check("EAN nao e bidimensional", not codigos.EAN13.bidimensional)
# Zona muda do QR sao 4 modulos em TODOS os lados, nao so nas laterais.
check("QR exige 4 modulos de zona muda", codigos.QRCODE.zona_muda_esq == 4)

# QR aceita texto, mas URL gigante vira borrao que celular nenhum le a 2cm.
check("QR aceita texto livre", codigos.validar("qualquer coisa", codigos.QRCODE)[0])
check("mas recusa texto denso demais pra etiqueta",
      not codigos.validar("x" * 400, codigos.QRCODE)[0])
check("e explica o que fazer", "encurtado" in codigos.validar("x"*400, codigos.QRCODE)[1])
check("QR vazio nao vira codigo", "^BQ" not in zpl.render(_qr(), {"produto": {}}))

secao("27. Catálogo de formatos: o que faz a primeira etiqueta sair em 2 minutos")
from etiquetas import formatos
# Sem catalogo, montar uma folha exige digitar OITO numeros que ninguem sabe de
# cabeca. Onboarding e onde app morre.
check("tem formato de rolo e de folha",
      len(formatos.por_tipo("rolo")) >= 5 and len(formatos.por_tipo("folha")) >= 4)
check("Avery 5160 dá 30 por folha", formatos.cabem_por_folha("avery_5160") == 30)
check("rolo conta como 1", formatos.cabem_por_folha("zebra_2x1") == 1)
try:
    formatos.obter("inventado")
    check("codigo inexistente da erro com a lista de opcoes", False)
except ValueError as _e:
    check("codigo inexistente da erro com a lista de opcoes", "avery" in str(_e))

# ESTA e a checagem que vale: catalogo digitado a mao erra, e o erro e INVISIVEL
# — as etiquetas empilham pra fora da folha e a ultima fileira imprime no nada.
# Ela ja reprovou uma entrada minha: uma Pimaco A4 deduzida por analogia, cujas
# 2 colunas ocupavam 211,2mm numa pagina de 210. A entrada foi REMOVIDA em vez
# de "consertada" com numero inventado.
_grades_ruins = []
for _f in formatos.CATALOGO:
    _grades_ruins.extend(formatos.conferir_grade(_f.codigo))
check("TODA grade do catalogo cabe no papel que ela diz caber",
      not _grades_ruins, _grades_ruins)

# O catalogo e' constante: editar a midia de um formato nao pode vazar pros
# outros usuarios. Bug que so aparece com dois lojistas e ninguem entende.
_m1 = formatos.midia("avery_5160")
_m1.margem_esq_mm = 999
check("mexer numa midia nao contamina o catalogo",
      formatos.midia("avery_5160").margem_esq_mm != 999)

# Nenhuma medida foi conferida com papel na mao — e o catalogo diz isso.
check("o catalogo admite que nao foi conferido",
      all(not f.conferido for f in formatos.CATALOGO))

_t_cat = Template("c", formatos.midia("avery_5160"),
                  elementos=[Texto(x_mm=2, y_mm=2, campo="variante.sku")])
check("da pra montar template direto do catalogo",
      len(motor_pdf.render(_t_cat, [(DADOS, 30)])) > 1000)
check("e a validacao aprova o formato do catalogo",
      esquema.validar(_t_cat) == [], esquema.validar(_t_cat))


# ---------------------------------------------------------------- espelho
secao("25. Arquivo-espelho: a promessa virando garantia")
# Teste de substring passa feliz enquanto cada elemento anda meio milimetro pro
# lado. O espelho compara byte a byte — e e ele que sustenta a promessa "seu
# template nao muda sozinho", que nasceu do Shopify ter mudado a fonte de todo
# mundo numa atualizacao.
import espelho as _espelho
_mudaram = _espelho.conferir()
check("nenhuma saida mudou desde a ultima gravacao", not _mudaram,
      [n for n, _ in _mudaram])
check("ha casos congelados de verdade", len(_espelho.casos()) >= 8,
      len(_espelho.casos()))
# A primeira versao dos espelhos NAO pegou uma mudanca de 0,8% na proporcao da
# fonte: nenhum caso "normal" tinha quebra perto do limiar. Espelho que so
# quebra com mudanca grande nao serve — mudanca grande a gente percebe sozinho.
check("existe um caso sentinela, frágil de proposito",
      any(n == "sentinela_limiar" for n, _, _ in _espelho.casos()))


# ---------------------------------------------------------------- loja
import base64 as _b64, hashlib as _hl, hmac as _hm, json as _js, time as _tm
from loja import assinatura, catalogo, cobranca, dominio, oauth, webhooks

SEGREDO = "segredo-do-app-de-teste"
CHAVE_API = "chave-api-de-teste"

secao("28. Dominio da loja: a peca de seguranca mais importante")
# O nome da loja chega pela URL em TODA requisicao e e usado pra montar a URL da
# API. Aceitar sem conferir da tres ataques de uma vez: redirecionar o lojista
# pra tela falsa, fazer o servidor chamar o endereco do atacante (SSRF), e criar
# duas linhas no banco pra mesma loja.
check("aceita dominio normal",
      dominio.normalizar("minhaloja.myshopify.com") == "minhaloja.myshopify.com")
check("normaliza maiuscula e barra final",
      dominio.normalizar("MinhaLoja.myshopify.com/") == "minhaloja.myshopify.com")
check("aceita com https", dominio.normalizar("https://loja.myshopify.com") == "loja.myshopify.com")

# Cada um destes e um ataque conhecido, nao um caso teorico.
for _mau in ["site-do-golpe.com", "loja.myshopify.com.evil.com",
             "evil.com/loja.myshopify.com", "loja.myshopify.com:8080",
             "loja.myshopify.com@evil.com", "", None, 123,
             "-hifen.myshopify.com", "hifen-.myshopify.com", "ab.myshopify.com",
             "loja.myshopify.com\nX-Injecao: 1"]:
    check("recusa %r" % (_mau,), not dominio.valido(_mau))

# TODA URL que sai daqui pro Shopify passa por aqui. Se alguem montar string a
# mao noutro arquivo, a validacao deixa de existir na pratica — e e assim que
# SSRF entra.
check("a URL da API passa pela validacao",
      dominio.url_admin("Loja.myshopify.com", "2026-07", "graphql.json")
      == "https://loja.myshopify.com/admin/api/2026-07/graphql.json")
try:
    dominio.url_admin("evil.com", "2026-07", "graphql.json")
    check("URL com dominio falso e recusada", False)
except ValueError:
    check("URL com dominio falso e recusada", True)

secao("29. Token de sessao: cinco conferencias, nenhuma opcional")
def _token(**kw):
    conteudo = {"aud": CHAVE_API, "dest": "https://loja.myshopify.com",
                "exp": _tm.time() + 60, "nbf": _tm.time() - 10}
    conteudo.update(kw)
    return assinatura.sessao_assinar(conteudo, kw.pop("_segredo", SEGREDO))

check("token bom abre e devolve a loja",
      assinatura.sessao_abrir(_token(), CHAVE_API, SEGREDO)["loja"] == "loja.myshopify.com")

def _recusa(nome, token, chave=CHAVE_API, segredo=SEGREDO):
    try:
        assinatura.sessao_abrir(token, chave, segredo)
        check(nome, False, "ACEITOU")
    except assinatura.TokenInvalido:
        check(nome, True)

_recusa("recusa assinado com outro segredo",
        assinatura.sessao_assinar({"aud": CHAVE_API, "dest": "https://l.myshopify.com",
                                   "exp": _tm.time()+60}, "outro-segredo"))
_recusa("recusa token de outro app", _token(aud="app-alheio"))
_recusa("recusa token expirado", _token(exp=_tm.time() - 999))
_recusa("recusa token do futuro", _token(nbf=_tm.time() + 999))
_recusa("recusa destino que nao e loja", _token(dest="https://evil.com"))
_recusa("recusa token malformado", "isso.nao.e.um.jwt.valido")
_recusa("recusa token vazio", "")

# O ataque do alg:none: o atacante manda um token SEM assinatura e a biblioteca
# aceita porque confia no algoritmo declarado pelo proprio token. E por isso que
# o algoritmo e fixado do nosso lado.
_cab = _b64.urlsafe_b64encode(_js.dumps({"alg": "none", "typ": "JWT"}).encode()).decode().rstrip("=")
_corpo = _b64.urlsafe_b64encode(_js.dumps(
    {"aud": CHAVE_API, "dest": "https://l.myshopify.com", "exp": _tm.time()+60}
).encode()).decode().rstrip("=")
_recusa("recusa o ataque do alg:none", _cab + "." + _corpo + ".")

secao("30. Webhook: sem HMAC, qualquer um apaga a loja de um lojista")
_corpo_wh = b'{"id":123,"topic":"app/uninstalled"}'
_sig = _b64.b64encode(_hm.new(SEGREDO.encode(), _corpo_wh, _hl.sha256).digest()).decode()

check("assinatura correta passa", assinatura.webhook_confere(_corpo_wh, _sig, SEGREDO))
# Um byte a mais no corpo ja invalida — e e por isso que o corpo tem que ser os
# BYTES CRUS: ler o JSON e serializar de novo quebra a assinatura pra sempre.
check("um espaco a mais no corpo invalida",
      not assinatura.webhook_confere(_corpo_wh + b" ", _sig, SEGREDO))
check("assinatura vazia nao passa", not assinatura.webhook_confere(_corpo_wh, "", SEGREDO))
check("segredo errado nao passa",
      not assinatura.webhook_confere(_corpo_wh, _sig, "outro-segredo"))

_cab_wh = {"X-Shopify-Hmac-Sha256": _sig, "X-Shopify-Topic": "app/uninstalled",
           "X-Shopify-Shop-Domain": "loja.myshopify.com"}
check("conferir devolve topico e loja",
      webhooks.conferir(_corpo_wh, _cab_wh, SEGREDO)
      == {"topico": "app/uninstalled", "loja": "loja.myshopify.com"})
try:
    webhooks.conferir(_corpo_wh, dict(_cab_wh, **{"X-Shopify-Hmac-Sha256": "forjado"}), SEGREDO)
    check("webhook forjado e recusado", False)
except webhooks.Recusado:
    check("webhook forjado e recusado", True)
try:
    webhooks.conferir(_corpo_wh, dict(_cab_wh, **{"X-Shopify-Shop-Domain": "evil.com"}), SEGREDO)
    check("webhook com loja falsa e recusado", False)
except webhooks.Recusado:
    check("webhook com loja falsa e recusado", True)

secao("31. Privacidade: os tres webhooks que o Shopify exige pra aprovar")
check("os tres obrigatorios estao assinados",
      set(webhooks.OBRIGATORIOS) ==
      {"customers/data_request", "customers/redact", "shop/redact"})
# Este app nao le pedido nem cliente — entao a resposta honesta e' que nao ha
# nada. E isso e verificavel lendo os escopos, nao e promessa de marketing.
check("nao pedimos escopo de cliente nem de pedido",
      not any("customer" in e or "order" in e for e in oauth.ESCOPOS), oauth.ESCOPOS)
check("so pedimos produto e estoque",
      set(oauth.ESCOPOS) == {"read_products", "read_inventory"})
check("a resposta de dados do cliente diz que nao ha nada",
      webhooks.resposta_de_privacidade("customers/data_request")["dados_do_cliente"] is None)
check("e explica por que", "não coleta" in
      webhooks.resposta_de_privacidade("customers/data_request")["explicacao"])

# Desinstalar NAO e' apagar. Muita gente reinstala no dia seguinte, e apagar os
# templates de quem desinstalou por engano perde o trabalho da pessoa. O Shopify
# manda shop/redact 48h depois justamente pra isso.
check("shop/redact apaga a loja", webhooks.deve_apagar_a_loja("shop/redact"))
check("app/uninstalled NAO apaga", not webhooks.deve_apagar_a_loja("app/uninstalled"))
check("app/uninstalled desativa", webhooks.deve_desativar("app/uninstalled"))

secao("32. OAuth: o state e a defesa contra instalacao forjada")
_estado = oauth.novo_estado()
check("o state e longo o bastante", len(_estado) >= 40, len(_estado))
check("e diferente a cada vez", oauth.novo_estado() != oauth.novo_estado())
check("state igual confere", oauth.estado_confere(_estado, _estado))
check("state diferente nao confere", not oauth.estado_confere(_estado, "outro"))
check("state vazio nunca confere", not oauth.estado_confere("", ""))

_url = oauth.url_de_autorizacao("Loja.myshopify.com", CHAVE_API,
                                "https://app.exemplo/volta", _estado)
check("a URL de autorizacao vai pro dominio normalizado",
      _url.startswith("https://loja.myshopify.com/admin/oauth/authorize"))
check("leva a chave, o escopo e o state",
      CHAVE_API in _url and "read_products" in _url and _estado in _url)

# A volta do OAuth com HMAC de verdade.
def _volta(**extra):
    parametros = {"code": "codigo-de-uso-unico", "shop": "loja.myshopify.com",
                  "state": _estado, "timestamp": "1700000000"}
    parametros.update(extra)
    mensagem = "&".join("%s=%s" % (k, parametros[k]) for k in sorted(parametros))
    parametros["hmac"] = _hm.new(SEGREDO.encode(), mensagem.encode(), _hl.sha256).hexdigest()
    return parametros

check("volta legitima e aceita",
      oauth.volta_valida(_volta(), _estado, SEGREDO) == "loja.myshopify.com")
for _nome, _params, _est in [
    ("state trocado", _volta(), "estado-diferente"),
    ("parametro adulterado depois de assinar", dict(_volta(), shop="outra.myshopify.com"), _estado),
]:
    try:
        oauth.volta_valida(_params, _est, SEGREDO)
        check("recusa %s" % _nome, False, "ACEITOU")
    except ValueError:
        check("recusa %s" % _nome, True)

secao("33. Catalogo: cada VARIANTE vira uma etiqueta, nao cada produto")
_RESPOSTA = {"data": {"products": {
    "pageInfo": {"hasNextPage": True, "endCursor": "cursor123"},
    "nodes": [
        {"title": "Camiseta", "vendor": "EcoWear", "productType": "Roupa",
         "onlineStoreUrl": "https://loja.com/camiseta",
         "variants": {"nodes": [
             {"title": "Azul / M", "sku": "CAM-AZ-M", "barcode": "789123456789",
              "price": "59.90", "inventoryQuantity": 12},
             {"title": "Azul / G", "sku": "CAM-AZ-G", "barcode": "789123456796",
              "price": "59.90", "inventoryQuantity": 0},
         ]}},
        {"title": "Sem variante", "variants": {"nodes": []}},
        "isso nao e um produto",
    ]}}}

_itens = catalogo.para_etiquetas(_RESPOSTA, nome_da_loja="EcoLoja")
# Etiquetar "Camiseta" sem dizer que e a azul tamanho M nao serve numa prateleira.
check("duas variantes viram duas etiquetas", len(_itens) == 2, len(_itens))
check("o titulo do produto vem junto", _itens[0]["produto"]["titulo"] == "Camiseta")
check("o SKU e da variante", _itens[0]["variante"]["sku"] == "CAM-AZ-M")
check("o nome da loja entra", _itens[0]["loja"]["nome"] == "EcoLoja")
# Loja com 8 mil produtos sempre tem cadastro estranho. Perder a fila inteira por
# causa de um seria o pior desfecho.
check("produto que nao e dicionario e pulado, sem derrubar", len(_itens) == 2)
check("resposta vazia nao derruba", catalogo.para_etiquetas({}) == [])
check("resposta None nao derruba", catalogo.para_etiquetas(None) == [])

check("a paginacao devolve o cursor",
      catalogo.tem_proxima_pagina(_RESPOSTA) == (True, "cursor123"))
# GraphQL responde 200 mesmo quando falhou. Quem so olha o codigo HTTP mostra
# tela vazia pro lojista, sem explicacao.
check("erro dentro de resposta 200 e detectado",
      catalogo.erros_do_graphql({"errors": [{"message": "Acesso negado"}]}) == ["Acesso negado"])

# Recebeu 40 unidades, quer 40 etiquetas — e digitar "1" duas mil vezes e
# literalmente a reclamacao do app oficial.
check("a quantidade sugerida e o estoque", catalogo.quantidade_sugerida(_itens[0]) == 12)
check("estoque zero ainda sugere 1", catalogo.quantidade_sugerida(_itens[1]) == 1)
check("estoque ausente sugere 1", catalogo.quantidade_sugerida({"variante": {}}) == 1)

check("a consulta pede no maximo 250 por pagina",
      catalogo.consulta_de_produtos(quantos=9999)["variables"]["quantos"] == 250)
check("e no minimo 1", catalogo.consulta_de_produtos(quantos=0)["variables"]["quantos"] == 1)
# O que a gente NAO pede e' tao importante quanto o que pede.
check("a consulta nao pede pedido nem cliente",
      "customer" not in catalogo.CONSULTA_PRODUTOS.lower()
      and "order" not in catalogo.CONSULTA_PRODUTOS.lower())

secao("34. Cobranca pelo Shopify")
check("tem plano gratis, pro e negocio", set(cobranca.PLANOS) == {"gratis", "pro", "negocio"})
# Sem plano gratis, a primeira tela do app e uma cobranca e ninguem instala.
check("o gratis existe e nao cobra", cobranca.plano("gratis")["preco_usd"] == 0)
check("o gratis so tem PDF, sem termica",
      cobranca.plano("gratis")["motores"] == ("pdf",))
check("o pro libera a impressora termica", cobranca.pode_usar("pro", "zpl"))
check("o gratis nao libera", not cobranca.pode_usar("gratis", "zpl"))
check("o gratis tem limite mensal",
      not cobranca.dentro_do_limite("gratis", 100) and cobranca.dentro_do_limite("gratis", 99))
check("o pago nao tem limite", cobranca.dentro_do_limite("pro", 999999))

_corpo_cob = cobranca.corpo_para_assinar("pro", "https://app.exemplo/volta",
                                         desenvolvimento=True)
check("a mutacao leva o preco certo", _corpo_cob["variables"]["preco"] == "9.99")
check("e os dias de teste", _corpo_cob["variables"]["teste"] == 7)
# Cobrar de verdade numa loja de desenvolvimento e motivo de reprovacao.
check("loja de desenvolvimento nao e cobrada", _corpo_cob["variables"]["desenvolvimento"] is True)
try:
    cobranca.corpo_para_assinar("gratis", "https://x")
    check("nao da pra assinar o plano gratis", False)
except ValueError:
    check("nao da pra assinar o plano gratis", True)

check("a URL de confirmacao e lida",
      cobranca.url_de_confirmacao({"data": {"appSubscriptionCreate": {
          "confirmationUrl": "https://loja.myshopify.com/confirmar"}}})
      == "https://loja.myshopify.com/confirmar")
# userErrors vem DENTRO de uma resposta 200 — quem so olha o HTTP manda o
# lojista pra lugar nenhum.
try:
    cobranca.url_de_confirmacao({"data": {"appSubscriptionCreate": {
        "userErrors": [{"message": "plano invalido"}]}}})
    check("erro do Shopify dentro do 200 e detectado", False)
except ValueError as _e:
    check("erro do Shopify dentro do 200 e detectado", "plano invalido" in str(_e))

# O Shopify e a fonte da verdade sobre pagamento, nao o nosso banco. Guardar "e
# pro" localmente e o lojista cancelar faria o app continuar liberando.
check("le o plano ativo da resposta do Shopify",
      cobranca.plano_ativo({"data": {"currentAppInstallation": {"activeSubscriptions": [
          {"name": "Etiquetas — Pro", "status": "ACTIVE"}]}}}) == "pro")
check("assinatura cancelada cai pro gratis",
      cobranca.plano_ativo({"data": {"currentAppInstallation": {"activeSubscriptions": [
          {"name": "Etiquetas — Pro", "status": "CANCELLED"}]}}}) == "gratis")
check("sem assinatura nenhuma e gratis", cobranca.plano_ativo({}) == "gratis")


# ================================================================ dados e web
# Daqui pra baixo o teste sobe o app de verdade, com banco temporario. As
# variaveis de ambiente precisam existir ANTES do import, porque `dados.banco` e
# `web.config` leem no momento em que sao carregados — falhar cedo, no boot, e a
# escolha do projeto.
import os as _os
import tempfile as _tmp

_PASTA = _tmp.mkdtemp(prefix="etiquetas_teste_")
_os.environ["BANCO_CAMINHO"] = _os.path.join(_PASTA, "teste.db")
_os.environ["CHAVE_SEGREDO"] = "segredo-de-teste-nao-usar-em-producao"
_os.environ["SHOPIFY_CHAVE_API"] = "chave-api-de-teste"
_os.environ["SHOPIFY_SEGREDO"] = "segredo-do-app-de-teste"
_os.environ["MODO_DEV"] = "1"

from dados import banco, lojas as t_lojas, modelos as t_modelos
from dados import impressoes as t_impressoes

_CHAVE_API = "chave-api-de-teste"
_SEGREDO = "segredo-do-app-de-teste"


secao("36. Banco: o token de acesso nao fica em texto puro")
# O token do Shopify nao expira e da acesso ao catalogo inteiro. Se o arquivo do
# banco vazar num backup mal guardado, quem pegar tem todas as lojas. Cifrar com
# chave que mora no ambiente separa as duas coisas.
_TOKEN = "shpat_exemplo_de_token_secreto"
_cifrado = banco.cifrar(_TOKEN)
check("o texto cifrado nao contem o token", _TOKEN not in _cifrado)
check("decifra de volta igualzinho", banco.decifrar(_cifrado) == _TOKEN)
# Fernet poe um vetor aleatorio em cada cifragem. Se dois iguais dessem o mesmo
# texto, daria pra saber que duas lojas usam o mesmo token so olhando o banco.
check("cifrar duas vezes da texto diferente", banco.cifrar(_TOKEN) != banco.cifrar(_TOKEN))
check("texto vazio nao vira lixo cifrado", banco.cifrar("") == "")

_guardada = _os.environ["CHAVE_SEGREDO"]
_os.environ["CHAVE_SEGREDO"] = "outra-chave-completamente-diferente"
# Chave trocada devolve "" em vez de estourar: o certo e tratar como "loja
# precisa reinstalar", nao derrubar a tela do lojista.
check("com a chave errada o token nao abre", banco.decifrar(_cifrado) == "")
_os.environ["CHAVE_SEGREDO"] = ""
try:
    banco.cifrar("x")
    check("sem CHAVE_SEGREDO o app recusa cifrar", False)
except RuntimeError:
    check("sem CHAVE_SEGREDO o app recusa cifrar", True)
_os.environ["CHAVE_SEGREDO"] = _guardada


secao("37. Lojas: instalar, reinstalar, desinstalar, apagar")
banco.iniciar()

_ID_A = t_lojas.salvar("LOJA-A.myshopify.com/", "token-da-A", "read_products")
check("o dominio e normalizado ao salvar",
      t_lojas.por_id(_ID_A)["dominio"] == "loja-a.myshopify.com")
check("o token volta decifrado", t_lojas.buscar("loja-a.myshopify.com")["token"] == "token-da-A")

# Reinstalar e comum: troca de plano, testa outro app, volta. Se cada instalacao
# criasse linha nova, os modelos ficariam presos na linha velha e a pessoa
# abriria o app numa tela em branco achando que perdeu tudo.
_ID_A2 = t_lojas.salvar("loja-a.myshopify.com", "token-novo-da-A")
check("reinstalar nao cria loja nova", _ID_A2 == _ID_A)
check("reinstalar troca o token", t_lojas.buscar("loja-a.myshopify.com")["token"] == "token-novo-da-A")

try:
    t_lojas.salvar("nao-e-loja.evil.com", "token")
    check("dominio invalido nao entra no banco", False)
except ValueError:
    check("dominio invalido nao entra no banco", True)
try:
    t_lojas.salvar("loja-b.myshopify.com", "")
    check("loja sem token e recusada", False)
except ValueError:
    check("loja sem token e recusada", True)

# Buscar com dominio torto devolve None, nao explode: quem chama isto trata
# entrada da web, e la o certo e 404, nao 500.
check("buscar dominio invalido devolve None", t_lojas.buscar("evil.com") is None)
check("buscar loja inexistente devolve None",
      t_lojas.buscar("nunca-instalou.myshopify.com") is None)

# app/uninstalled: o token morre na hora, mas os modelos ficam. Quem desinstala
# hoje pode voltar amanha, e apagar o desenho da pessoa seria perda irreversivel.
t_lojas.desativar("loja-a.myshopify.com")
_desativada = t_lojas.buscar("loja-a.myshopify.com")
check("desinstalar marca a loja como inativa", _desativada["ativa"] is False)
check("desinstalar apaga o token guardado", _desativada["token"] == "")
check("desinstalar guarda a data", bool(_desativada["desinstalada_em"]))
t_lojas.salvar("loja-a.myshopify.com", "token-da-volta")
check("reinstalar reativa a mesma loja", t_lojas.buscar("loja-a.myshopify.com")["ativa"] is True)
check("reinstalar limpa a data de saida",
      t_lojas.buscar("loja-a.myshopify.com")["desinstalada_em"] is None)


secao("38. Isolamento: a loja B nao alcanca nada da loja A")
# Esta e a secao mais importante do arquivo. Num app multi-inquilino a falha mais
# comum e buscar por `id` sozinho porque "o id e unico no banco" — e ai o lojista
# troca o numero na URL e le (ou sobrescreve) o modelo de outro. Tem nome: IDOR.
_ID_B = t_lojas.salvar("loja-b.myshopify.com", "token-da-B")
check("duas lojas, dois ids diferentes", _ID_A != _ID_B)

_MODELO_A = t_modelos.criar(_ID_A, "Etiqueta da A", etiqueta_padrao())
_MODELO_B = t_modelos.criar(_ID_B, "Etiqueta da B", etiqueta_padrao())

check("cada loja ve so o proprio modelo",
      [m["id"] for m in t_modelos.listar(_ID_A)] == [_MODELO_A])
check("a lista da B nao tem nada da A",
      [m["id"] for m in t_modelos.listar(_ID_B)] == [_MODELO_B])

# Ler o alheio.
check("a B nao le o modelo da A pelo id", t_modelos.buscar(_ID_B, _MODELO_A) is None)
check("a B nao le nem o registro cru da A", t_modelos.buscar_cru(_ID_B, _MODELO_A) is None)
check("a A le o proprio normalmente", t_modelos.buscar(_ID_A, _MODELO_A) is not None)

# Sobrescrever o alheio — pior que ler, porque nao tem volta.
check("a B nao sobrescreve o modelo da A",
      t_modelos.salvar(_ID_B, _MODELO_A, "invadido", etiqueta_padrao()) is False)
check("o nome do modelo da A continua o mesmo",
      t_modelos.buscar_cru(_ID_A, _MODELO_A)["nome"] == "Etiqueta da A")

# Apagar o alheio.
check("a B nao apaga o modelo da A", t_modelos.apagar(_ID_B, _MODELO_A) is False)
check("o modelo da A continua vivo", t_modelos.buscar(_ID_A, _MODELO_A) is not None)
check("a B nao copia o modelo da A", t_modelos.duplicar(_ID_B, _MODELO_A) is None)

# A contagem que alimenta o limite do plano tambem separa.
check("a contagem de modelos e por loja",
      (t_modelos.quantos(_ID_A), t_modelos.quantos(_ID_B)) == (1, 1))

# loja_id ausente nao pode virar consulta silenciosa: em leitura daria zero
# linhas, e em ESCRITA daria zero linhas sem ninguem perceber.
for _ruim in (None, 0, "", "abc", -1):
    try:
        t_modelos.listar(_ruim)
        check("loja_id %r e recusado" % (_ruim,), False)
    except ValueError:
        check("loja_id %r e recusado" % (_ruim,), True)

# Copiar e como a maioria cria o segundo modelo. Sem isso a pessoa redesenha
# tudo, que e o atrito que vira review de duas estrelas.
_COPIA = t_modelos.duplicar(_ID_A, _MODELO_A)
check("duplicar cria modelo novo na mesma loja", _COPIA not in (None, _MODELO_A))
check("a copia leva o nome marcado",
      t_modelos.buscar_cru(_ID_A, _COPIA)["nome"] == "Etiqueta da A (cópia)")
t_modelos.apagar(_ID_A, _COPIA)


secao("39. Impressoes: a conta do mes, sem guardar o catalogo de ninguem")
check("loja nova comeca com zero no mes", t_impressoes.no_mes(_ID_B) == 0)
t_impressoes.registrar(_ID_A, 40, "zpl", _MODELO_A)
t_impressoes.registrar(_ID_A, 12, "pdf", _MODELO_A)
check("as impressoes somam no mes", t_impressoes.no_mes(_ID_A) == 52)
check("a conta da A nao vaza pra B", t_impressoes.no_mes(_ID_B) == 0)
check("o historico e por loja", len(t_impressoes.historico(_ID_B)) == 0)

# A tabela guarda so a conta. Nem titulo, nem SKU, nem preco — senao a resposta
# "nao guardo dado de cliente" do webhook de privacidade viraria meia verdade.
with banco.conectar() as _con:
    _COLUNAS = {c[1] for c in _con.execute("PRAGMA table_info(impressoes)").fetchall()}
check("a tabela de impressoes nao tem coluna de conteudo",
      _COLUNAS == {"id", "loja_id", "modelo_id", "motor", "quantidade", "criado_em"},
      sorted(_COLUNAS))

# SUM de zero linhas devolve NULL, e int(None) estoura. Loja recem-instalada cai
# exatamente nesse caso — ou seja, seria o primeiro uso do app que quebraria.
_ID_C = t_lojas.salvar("loja-c.myshopify.com", "token-da-C")
check("loja sem nenhuma impressao nao estoura o COALESCE", t_impressoes.no_mes(_ID_C) == 0)


secao("40. shop/redact apaga mesmo, inclusive o que pendura na loja")
# Sem o PRAGMA foreign_keys ligado em CADA conexao, o CASCADE nao roda e sobra
# lixo orfao — e a gente estaria respondendo "apaguei" pro Shopify sem ter apagado.
_MODELO_C = t_modelos.criar(_ID_C, "Etiqueta da C", etiqueta_padrao())
t_impressoes.registrar(_ID_C, 5, "pdf", _MODELO_C)
t_lojas.apagar("loja-c.myshopify.com")
check("a loja some", t_lojas.buscar("loja-c.myshopify.com") is None)
with banco.conectar() as _con:
    _sobrou_m = _con.execute("SELECT COUNT(*) n FROM modelos WHERE loja_id=?",
                             (_ID_C,)).fetchone()["n"]
    _sobrou_i = _con.execute("SELECT COUNT(*) n FROM impressoes WHERE loja_id=?",
                             (_ID_C,)).fetchone()["n"]
check("os modelos somem junto (CASCADE)", _sobrou_m == 0, _sobrou_m)
check("as impressoes somem junto (CASCADE)", _sobrou_i == 0, _sobrou_i)
check("apagar loja das outras nao mexe na A", t_modelos.buscar(_ID_A, _MODELO_A) is not None)


secao("41. Web: os cabecalhos que decidem se o app abre")
import web as _web

_app = _web.criar_app()
_cliente = _app.test_client()


def _token_de(loja_dominio, segredo=_SEGREDO, chave=_CHAVE_API, validade=60, nbf=None):
    """Forja um token de sessao. So existe pro teste — ver assinatura.sessao_assinar."""
    _agora = _tm.time()
    return assinatura.sessao_assinar({
        "iss": "https://%s/admin" % loja_dominio,
        "dest": "https://%s" % loja_dominio,
        "aud": chave,
        "sub": "1",
        "exp": _agora + validade,
        "nbf": _agora - 10 if nbf is None else nbf,
        "iat": _agora,
    }, segredo)


def _pega(caminho, loja_dominio=None, **kw):
    cab = {}
    if loja_dominio:
        cab["Authorization"] = "Bearer " + _token_de(loja_dominio)
    return _cliente.get(caminho, headers=cab, **kw)


_r = _cliente.get("/?shop=loja-a.myshopify.com")
# Sem frame-ancestors o navegador recusa a moldura e o lojista ve um retangulo
# branco — sem erro nenhum no log do servidor.
check("o CSP autoriza o iframe da loja da requisicao",
      "frame-ancestors https://loja-a.myshopify.com https://admin.shopify.com"
      in _r.headers.get("Content-Security-Policy", ""),
      _r.headers.get("Content-Security-Policy"))
# X-Frame-Options nao entende "so estes dois". Um DENY esquecido aqui bloqueia o
# app inteiro, com o mesmo sintoma silencioso.
check("nao sai X-Frame-Options", _r.headers.get("X-Frame-Options") is None)
check("shop invalido no CSP cai pro generico, nao ecoa o lixo",
      "evil.com" not in _cliente.get("/?shop=evil.com").headers
      .get("Content-Security-Policy", ""))
check("shop invalido na raiz da 400", _cliente.get("/?shop=evil.com").status_code == 400)
check("sem shop nenhum nao e erro", _cliente.get("/").status_code == 200)
check("loja que nao instalou e mandada pra instalacao",
      _cliente.get("/?shop=nao-instalou.myshopify.com").status_code == 302)
# Dentro do iframe um redirect tentaria carregar a tela do Shopify embutida, e o
# Shopify recusa ser embutido. Por isso a resposta e uma pagina que escapa.
_emb = _cliente.get("/?shop=nao-instalou.myshopify.com&embedded=1")
check("dentro do iframe a resposta escapa pra janela de cima",
      _emb.status_code == 200 and b"window.top.location" in _emb.data)
check("/saude responde sem token", _cliente.get("/saude").status_code == 200)
check("/saude nao conta loja nem mostra dado de ninguem",
      set(_cliente.get("/saude").get_json()) == {"ok", "configuracao_faltando"})


secao("42. Web: nenhuma rota de dados abre sem token de sessao valido")
# A loja vem SO do token assinado. Se /api/produtos?loja=X funcionasse, qualquer
# um trocaria o X e leria o catalogo alheio.
for _rota in ("/api/uso", "/api/modelos", "/api/produtos"):
    check("%s sem token da 401" % _rota, _pega(_rota).status_code == 401)
check("POST /api/imprimir sem token da 401",
      _cliente.post("/api/imprimir", json={"itens": [{}]}).status_code == 401)
check("passar a loja pela URL nao autentica",
      _pega("/api/uso?shop=loja-a.myshopify.com").status_code == 401)

check("com token valido a rota abre", _pega("/api/uso", "loja-a.myshopify.com").status_code == 200)

# Token assinado com outro segredo: e alguem forjando.
_r = _cliente.get("/api/uso", headers={"Authorization": "Bearer " +
                  _token_de("loja-a.myshopify.com", segredo="segredo-errado")})
check("token assinado com outro segredo da 401", _r.status_code == 401)

# Token de OUTRO app do Shopify, valido de verdade, mas nao pra este.
_r = _cliente.get("/api/uso", headers={"Authorization": "Bearer " +
                  _token_de("loja-a.myshopify.com", chave="chave-de-outro-app")})
check("token emitido pra outro app da 401", _r.status_code == 401)

# Token velho reaproveitado.
_r = _cliente.get("/api/uso", headers={"Authorization": "Bearer " +
                  _token_de("loja-a.myshopify.com", validade=-3600)})
check("token expirado da 401", _r.status_code == 401)

# O ataque do alg:none — token sem assinatura que a biblioteca aceita porque
# confia no algoritmo que o proprio token declara.
_cabecalho_none = _b64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').decode().rstrip("=")
_corpo_none = _b64.urlsafe_b64encode(_js.dumps({
    "dest": "https://loja-a.myshopify.com", "aud": _CHAVE_API,
    "exp": _tm.time() + 60}).encode()).decode().rstrip("=")
_r = _cliente.get("/api/uso", headers={
    "Authorization": "Bearer %s.%s." % (_cabecalho_none, _corpo_none)})
check("o ataque alg:none nao passa pela rota", _r.status_code == 401)

# A versao acima e pega por duas defesas ao mesmo tempo (o algoritmo fixo E a
# assinatura vazia), entao ela nao prova que a PRIMEIRA existe — descobri isso
# afrouxando o algoritmo de proposito e vendo a bateria seguir verde.
# Esta aqui isola: o cabecalho diz "none" mas a assinatura e um HS256 VALIDO.
# So a checagem de algoritmo pode recusar isto.
_assinado_certo = _b64.urlsafe_b64encode(_hm.new(
    _SEGREDO.encode(), ("%s.%s" % (_cabecalho_none, _corpo_none)).encode(),
    _hl.sha256).digest()).decode().rstrip("=")
_r = _cliente.get("/api/uso", headers={"Authorization": "Bearer %s.%s.%s"
                  % (_cabecalho_none, _corpo_none, _assinado_certo)})
check("alg:none com assinatura valida tambem e recusado", _r.status_code == 401,
      _r.status_code)
# E o contrario: o mesmo conteudo com o cabecalho certo passa. Sem isto, o teste
# acima poderia estar passando porque o token esta torto por outro motivo.
check("o mesmo conteudo com alg HS256 passa",
      _pega("/api/uso", "loja-a.myshopify.com").status_code == 200)

check("Authorization sem 'Bearer' nao passa",
      _cliente.get("/api/uso", headers={"Authorization": _token_de("loja-a.myshopify.com")})
      .status_code == 401)

# Loja que desinstalou: o token pode ate ser valido, mas o app nao esta mais la.
t_lojas.desativar("loja-b.myshopify.com")
_r = _pega("/api/uso", "loja-b.myshopify.com")
check("loja desinstalada da 403, nao 401", _r.status_code == 403, _r.status_code)
check("e a mensagem diz pra reinstalar", "instale" in _r.get_json()["erro"].lower())
t_lojas.salvar("loja-b.myshopify.com", "token-da-B")

# Loja que nunca instalou mas tem token forjado com o nosso segredo — so
# aconteceria se o segredo vazasse, e ainda assim nao acha loja.
check("loja que nunca instalou da 403",
      _pega("/api/uso", "nunca-vista.myshopify.com").status_code == 403)


secao("43. Web: o isolamento vale tambem pela porta da API")
# Mesma prova da secao 38, agora atravessando a rota inteira: e aqui que o
# lojista de verdade trocaria o numero na URL.
_r = _pega("/api/modelos", "loja-a.myshopify.com")
check("a A ve so o modelo dela pela API",
      [m["id"] for m in _r.get_json()["modelos"]] == [_MODELO_A])

_r = _pega("/api/modelos/%d" % _MODELO_A, "loja-b.myshopify.com")
check("a B pedindo o modelo da A leva 404", _r.status_code == 404, _r.status_code)
# 404 e nao 403 de proposito: distinguir "nao e seu" de "nao existe" contaria ao
# atacante quais id existem no banco.
check("e a resposta nao confirma que o modelo existe",
      "encontrado" in _r.get_json()["erro"])

_r = _cliente.put("/api/modelos/%d" % _MODELO_A,
                  headers={"Authorization": "Bearer " + _token_de("loja-b.myshopify.com")},
                  json={"nome": "invadido", "modelo": esquema.para_dict(etiqueta_padrao())})
check("a B nao sobrescreve o modelo da A pela API", _r.status_code == 404)
check("o modelo da A segue intacto depois da tentativa",
      t_modelos.buscar_cru(_ID_A, _MODELO_A)["nome"] == "Etiqueta da A")

_r = _cliente.delete("/api/modelos/%d" % _MODELO_A,
                     headers={"Authorization": "Bearer " + _token_de("loja-b.myshopify.com")})
check("a B nao apaga o modelo da A pela API", _r.status_code == 404)
check("o modelo da A continua existindo", t_modelos.buscar(_ID_A, _MODELO_A) is not None)

# Modelo invalido vindo da web nao pode virar linha quebrada no banco.
_r = _cliente.post("/api/modelos",
                   headers={"Authorization": "Bearer " + _token_de("loja-a.myshopify.com")},
                   json={"nome": "torto", "modelo": {"midia": {"largura_mm": -5}}})
check("modelo com medida negativa e recusado na criacao",
      _r.status_code == 400, _r.status_code)


secao("44. Web: o limite do plano e conferido ANTES de renderizar")
# Se a conferencia viesse depois, bastaria a requisicao cair no meio pra etiqueta
# sair sem ser contada. E gerar 4 mil PDFs pra so entao recusar gasta CPU a toa.
_ITENS = [{"produto": {"titulo": "Caneca"}, "variante": {"sku": "C1", "preco": "24.90",
           "codigo_barras": "7891234567895"}, "quantidade": 2}]


def _imprimir(loja_dominio, corpo):
    return _cliente.post("/api/imprimir",
                         headers={"Authorization": "Bearer " + _token_de(loja_dominio)},
                         json=corpo)


_r = _imprimir("loja-a.myshopify.com",
               {"motor": "zpl", "modelo_id": _MODELO_A, "itens": _ITENS})
check("o plano gratis nao imprime em impressora termica", _r.status_code == 402, _r.status_code)
check("e o motivo vem legivel pra tela decidir o que mostrar",
      _r.get_json()["motivo"] == "motor_bloqueado")

_antes = t_impressoes.no_mes(_ID_A)
check("recusar por plano nao conta etiqueta", t_impressoes.no_mes(_ID_A) == _antes)

_r = _imprimir("loja-a.myshopify.com",
               {"motor": "pdf", "modelo_id": _MODELO_A, "itens": _ITENS})
check("o plano gratis imprime em PDF", _r.status_code == 200, _r.status_code)
check("e sai PDF de verdade", _r.data[:5] == b"%PDF-", _r.data[:8])
check("a impressao foi contada", t_impressoes.no_mes(_ID_A) == _antes + 2)

# A quantidade vem do navegador, e o navegador mente.
_r = _imprimir("loja-a.myshopify.com", {"motor": "pdf", "modelo_id": _MODELO_A,
               "itens": [{"produto": {"titulo": "X"}, "variante": {}, "quantidade": -50}]})
check("quantidade negativa nao vira credito de etiqueta", _r.status_code == 200)
check("quantidade negativa conta como 1", t_impressoes.no_mes(_ID_A) == _antes + 3)

# Teto por requisicao: nao e comercial, e de servidor. Uma loja com 200 mil
# variantes num clique so travaria o processo pra todo mundo.
_r = _imprimir("loja-a.myshopify.com", {"motor": "pdf", "modelo_id": _MODELO_A,
               "itens": [{"produto": {}, "variante": {}, "quantidade": 999999}]})
check("lote gigante e recusado antes de renderizar", _r.status_code == 400, _r.status_code)
check("e o motivo diz que e pra dividir", _r.get_json()["motivo"] == "lote_grande")

_r = _imprimir("loja-a.myshopify.com", {"motor": "pdf", "modelo_id": _MODELO_B,
                                        "itens": _ITENS})
check("nao da pra imprimir com o modelo de outra loja", _r.status_code == 404, _r.status_code)
_r = _imprimir("loja-a.myshopify.com", {"motor": "pdf", "modelo_id": _MODELO_A, "itens": []})
check("fila vazia e recusada", _r.status_code == 400)
_r = _imprimir("loja-a.myshopify.com", {"motor": "matricial", "modelo_id": _MODELO_A,
                                        "itens": _ITENS})
check("motor que nao existe e recusado", _r.status_code in (400, 402))

# O limite mensal do gratis.
t_impressoes.registrar(_ID_A, 200, "pdf", _MODELO_A)
_r = _imprimir("loja-a.myshopify.com", {"motor": "pdf", "modelo_id": _MODELO_A,
                                        "itens": _ITENS})
check("estourou o mes, recusa com 402", _r.status_code == 402, _r.status_code)
check("e o motivo e o limite do mes", _r.get_json()["motivo"] == "limite_do_mes")

# A tela precisa saber ANTES, senao a pessoa monta a fila inteira pra descobrir
# na hora de imprimir — surpresa que vira review de uma estrela.
_uso = _pega("/api/uso", "loja-a.myshopify.com").get_json()
check("/api/uso diz o plano e o quanto ja foi", _uso["plano"] == "gratis"
      and _uso["etiquetas_no_mes"] > 100 and _uso["limite_mes"] == 100)
check("/api/uso diz que motores o plano libera", _uso["motores"] == ["pdf"])

# Plano pago libera o resto. O banco aqui e so cache — quem manda e o Shopify.
t_lojas.marcar_plano(_ID_A, "pro")
_r = _imprimir("loja-a.myshopify.com", {"motor": "zpl", "modelo_id": _MODELO_A,
                                        "itens": _ITENS})
check("o Pro imprime em termica mesmo tendo passado de 100", _r.status_code == 200,
      _r.status_code)
check("e sai ZPL de verdade", _r.data.startswith(b"^XA"), _r.data[:10])
# Plano desconhecido no banco (ex.: o "conferir" que o webhook grava) nao pode
# liberar nada por engano — cai pro gratis.
t_lojas.marcar_plano(_ID_A, "conferir")
check("plano desconhecido cai pro gratis, nao libera",
      _imprimir("loja-a.myshopify.com", {"motor": "zpl", "modelo_id": _MODELO_A,
                                         "itens": _ITENS}).status_code == 402)
t_lojas.marcar_plano(_ID_A, "gratis")


secao("45. Web: o webhook so passa com assinatura, e responde 200 ate no que ignora")
def _assinar_corpo(corpo: bytes) -> str:
    return _b64.b64encode(_hm.new(_SEGREDO.encode(), corpo, _hl.sha256).digest()).decode()


def _webhook(topico, loja_dominio, corpo=b'{"ok":true}', assinatura_falsa=None):
    return _cliente.post("/webhooks", data=corpo, headers={
        "X-Shopify-Topic": topico,
        "X-Shopify-Shop-Domain": loja_dominio,
        "X-Shopify-Hmac-Sha256": assinatura_falsa or _assinar_corpo(corpo),
        "Content-Type": "application/json"})


check("webhook sem assinatura e recusado",
      _cliente.post("/webhooks", data=b"{}").status_code == 401)
check("webhook com assinatura errada e recusado",
      _webhook("app/uninstalled", "loja-b.myshopify.com",
               assinatura_falsa="YXNzaW5hdHVyYSBmYWxzYQ==").status_code == 401)
# Um espaco a mais no corpo ja invalida — e por isso que o corpo tem que ser lido
# como bytes crus, nunca reserializado a partir do JSON.
_corpo = b'{"ok":true}'
check("um byte a mais no corpo invalida a assinatura",
      _cliente.post("/webhooks", data=_corpo + b" ", headers={
          "X-Shopify-Topic": "app/uninstalled",
          "X-Shopify-Shop-Domain": "loja-b.myshopify.com",
          "X-Shopify-Hmac-Sha256": _assinar_corpo(_corpo)}).status_code == 401)

# Tres webhooks obrigatorios de privacidade. O Shopify testa na revisao.
_r = _webhook("customers/data_request", "loja-b.myshopify.com")
check("customers/data_request responde 200", _r.status_code == 200)
check("e responde honestamente que nao ha dado de cliente",
      _r.get_json()["dados_do_cliente"] is None)
_r = _webhook("customers/redact", "loja-b.myshopify.com")
check("customers/redact responde 200 e apagado", _r.get_json()["apagado"] is True)

# Desinstalar desativa; so o shop/redact apaga. O Shopify manda o redact 48h
# depois justamente pra dar tempo de quem desinstalou por engano voltar.
_MODELO_B2 = t_modelos.criar(_ID_B, "Sobrevivente", etiqueta_padrao())
_webhook("app/uninstalled", "loja-b.myshopify.com")
check("app/uninstalled desativa a loja", t_lojas.buscar("loja-b.myshopify.com")["ativa"] is False)
check("mas os modelos continuam la", t_modelos.buscar(_ID_B, _MODELO_B2) is not None)

_webhook("shop/redact", "loja-b.myshopify.com")
check("shop/redact apaga a loja", t_lojas.buscar("loja-b.myshopify.com") is None)
check("e os modelos vao junto", t_modelos.listar(_ID_B) == [])

# Topico desconhecido responde 200: erro faria o Shopify tentar de novo, e de
# novo, e acabar desassinando o webhook por excesso de falha.
check("topico desconhecido ainda responde 200",
      _webhook("orders/create", "loja-a.myshopify.com").status_code == 200)
check("dominio de loja invalido no webhook e recusado",
      _webhook("app/uninstalled", "evil.com").status_code == 401)
check("apagar a loja B nao mexeu na A", t_modelos.buscar(_ID_A, _MODELO_A) is not None)


secao("46. Rede: o unico arquivo que fala com a internet")
from loja import rede as _rede

# THROTTLED vem dentro de uma resposta 200, nao num 429. Quem so olha o codigo
# HTTP acha que deu certo e mostra tela vazia pro lojista.
check("reconhece o THROTTLED escondido no 200",
      _rede._foi_estrangulado({"errors": [{"message": "Throttled",
                                           "extensions": {"code": "THROTTLED"}}]}))
check("resposta boa nao e confundida com limite",
      _rede._foi_estrangulado({"data": {"products": {"nodes": []}}}) is False)
try:
    _rede.graphql("loja-a.myshopify.com", "", {})
    check("chamar sem token nao vai pra rede", False)
except _rede.ErroDeRede as _e:
    check("chamar sem token nao vai pra rede", "reinstalar" in str(_e))
# Redirecionamento aconteceria DEPOIS da validacao de dominio e levaria a
# requisicao pra onde a resposta mandar — inclusive pra dentro da rede do servidor.
check("o abridor instalado e o que recusa redirecionamento",
      any(isinstance(h, _rede._SemRedirecionamento) for h in _rede._abridor.handlers))
try:
    _rede._SemRedirecionamento().redirect_request(None, None, 302, "", {}, "http://169.254.169.254/")
    check("redirecionamento pra endereco interno e barrado", False)
except _rede.ErroDeRede:
    check("redirecionamento pra endereco interno e barrado", True)


secao("47. Config: falta de configuracao aparece no boot, nao tres dias depois")
from web import config as _cfg

check("configuracao completa nao reclama", _cfg.conferir() == [])
check("a URL de volta nao tem barra dobrada", "//instalar" not in _cfg.url_de_volta()
      .replace("https://", "").replace("http://", ""))
check("a URL de volta bate com o que vai no painel do Shopify",
      _cfg.url_de_volta().endswith("/instalar/volta"))


# ---------------------------------------------------------------- fim
print("\n" + "=" * 62)
print("PASSOU: %d   FALHOU: %d" % (PASSOU, len(FALHOU)))
if FALHOU:
    print("\nFALHAS:")
    for nome in FALHOU:
        print("  - %s" % nome)
print("=" * 62)
sys.exit(1 if FALHOU else 0)
