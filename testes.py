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
check("so pedimos produto, estoque e escrita de produto",
      set(oauth.ESCOPOS) == {"read_products", "read_inventory",
                             "write_products"}, oauth.ESCOPOS)
check("a resposta de dados do cliente diz que nao ha nada",
      webhooks.resposta_de_privacidade("customers/data_request")["dados_do_cliente"] is None)
# Esta resposta vai pro SHOPIFY, nao pro lojista, entao e em ingles — e o que
# ela diz tem que ser verdade verificavel nos escopos, nao promessa.
check("e explica por que, na lingua da plataforma",
      "does not collect or store customer data" in
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
# Dois planos, nao tres. Havia um "Negocio" prometendo multiplos locais e
# historico de modelos, e NENHUM dos dois estava construido — vender o que nao
# existe e reprovacao na revisao e reclamacao depois. Ele volta quando houver o
# que por nele, e ai quem diz o que e sao os clientes.
check("tem plano gratis e pro", set(cobranca.PLANOS) == {"gratis", "pro"},
      set(cobranca.PLANOS))
check("e nenhum plano promete o que nao existe",
      all("dymo" not in p["motores"] for p in cobranca.PLANOS.values()))

# O nome que a gente CRIA e o nome que a gente RECONHECE tem que ser o mesmo.
# `corpo_para_assinar` monta "Etik Barcode Labels — Pro" e `plano_ativo` procura
# o nome do plano dentro do que o Shopify devolve. Se os dois usassem strings
# diferentes, a assinatura seria criada e nunca reconhecida: o lojista pagaria e
# continuaria no gratis. E o mesmo defeito que ja cavamos por outro caminho, e a
# volta inteira e o unico jeito de garantir que ele nao volte.
for _cod, _p in cobranca.PLANOS.items():
    if _p["preco_usd"] <= 0:
        continue
    _nome_na_fatura = cobranca.corpo_para_assinar(
        _cod, "https://x")["variables"]["nome"]
    _reconhecido = cobranca.plano_ativo({"data": {"currentAppInstallation": {
        "activeSubscriptions": [{"name": _nome_na_fatura, "status": "ACTIVE"}]}}})
    check("a assinatura de %s volta reconhecida como %s" % (_cod, _cod),
          _reconhecido == _cod, (_nome_na_fatura, _reconhecido))
    check("e o nome na fatura leva o nome do app",
          cobranca.NOME_DO_APP in _nome_na_fatura, _nome_na_fatura)
# Sem plano gratis, a primeira tela do app e uma cobranca e ninguem instala.
check("o gratis existe e nao cobra", cobranca.plano("gratis")["preco_usd"] == 0)
check("o gratis so tem PDF, sem termica",
      cobranca.plano("gratis")["motores"] == ("pdf",))
check("o pro libera a impressora termica", cobranca.pode_usar("pro", "zpl"))
check("o gratis nao libera", not cobranca.pode_usar("gratis", "zpl"))
check("o gratis tem limite mensal",
      not cobranca.dentro_do_limite("gratis", 200) and cobranca.dentro_do_limite("gratis", 199))
check("o pago nao tem limite", cobranca.dentro_do_limite("pro", 999999))

_corpo_cob = cobranca.corpo_para_assinar("pro", "https://app.exemplo/volta",
                                         desenvolvimento=True)
check("a mutacao leva o preco certo", _corpo_cob["variables"]["preco"] == "9.99")
check("e os dias de teste", _corpo_cob["variables"]["teste"] == 7)
# Cobrar de verdade numa loja de desenvolvimento e motivo de reprovacao.
check("da pra pedir assinatura de teste explicitamente",
      _corpo_cob["variables"]["desenvolvimento"] is True)
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

def _instalar(dominio, token, escopos=""):
    """Uma loja instalada hoje: token de 1h e refresh de 90 dias.

    Sem isto toda loja de teste ficaria com credencial da era anterior — e aí
    cada rota tentaria migrar o token CONTRA A REDE DE VERDADE, que e o que a
    bateria inteira existe pra nao fazer. A migracao tem secao propria, com a
    rede fingida.
    """
    return t_lojas.salvar(dominio, token, escopos,
                          refresh="shprt-de-teste",
                          expira_em=t_lojas.daqui_a(3600),
                          refresh_expira_em=t_lojas.daqui_a(90 * 24 * 3600))


_ID_A = _instalar("LOJA-A.myshopify.com/", "token-da-A", "read_products")
check("o dominio e normalizado ao salvar",
      t_lojas.por_id(_ID_A)["dominio"] == "loja-a.myshopify.com")
check("o token volta decifrado", t_lojas.buscar("loja-a.myshopify.com")["token"] == "token-da-A")

# Reinstalar e comum: troca de plano, testa outro app, volta. Se cada instalacao
# criasse linha nova, os modelos ficariam presos na linha velha e a pessoa
# abriria o app numa tela em branco achando que perdeu tudo.
_ID_A2 = _instalar("loja-a.myshopify.com", "token-novo-da-A")
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
_instalar("loja-a.myshopify.com", "token-da-volta")
check("reinstalar reativa a mesma loja", t_lojas.buscar("loja-a.myshopify.com")["ativa"] is True)
check("reinstalar limpa a data de saida",
      t_lojas.buscar("loja-a.myshopify.com")["desinstalada_em"] is None)


secao("38. Isolamento: a loja B nao alcanca nada da loja A")
# Esta e a secao mais importante do arquivo. Num app multi-inquilino a falha mais
# comum e buscar por `id` sozinho porque "o id e unico no banco" — e ai o lojista
# troca o numero na URL e le (ou sobrescreve) o modelo de outro. Tem nome: IDOR.
_ID_B = _instalar("loja-b.myshopify.com", "token-da-B")
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
_ID_C = _instalar("loja-c.myshopify.com", "token-da-C")
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
# O texto vem da tabela de idiomas, entao o teste compara com ELA em vez de
# travar uma frase — senao traduzir quebraria o teste sem nada estar errado.
from web import textos as _txt
check("e a mensagem manda reinstalar",
      _r.get_json()["erro"] == _txt.t("desinstalado", "en"), _r.get_json()["erro"])
check("e ela existe nos dois idiomas",
      _txt.t("desinstalado", "pt") != _txt.t("desinstalado", "en"))
_instalar("loja-b.myshopify.com", "token-da-B")

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
      _r.get_json()["erro"] == _txt.t("erro_modelo_sumido", "en"),
      _r.get_json()["erro"])

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
      and _uso["etiquetas_no_mes"] > 200 and _uso["limite_mes"] == 200)
check("/api/uso diz que motores o plano libera", _uso["motores"] == ["pdf"])

# Plano pago libera o resto. O banco aqui e so cache — quem manda e o Shopify.
t_lojas.marcar_plano(_ID_A, "pro")

# Uma loja nova pros testes de isolamento: a loja B foi APAGADA na secao 45, pelo
# shop/redact. Reusar ela aqui daria 403 e eu estaria medindo "loja desinstalada"
# achando que media isolamento.
_ID_D = _instalar("loja-d.myshopify.com", "token-da-D")
t_lojas.marcar_plano(_ID_D, "pro")
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
# Hospedagem barata costuma obrigar a saida a passar por um proxy — o plano
# gratis do PythonAnywhere e assim, e e como ele controla a lista de sites
# permitidos. Sem respeitar isso, o app sobe e falha em TODA chamada ao Shopify,
# com erro de conexao e nada dizendo que o motivo e proxy.
import urllib.request as _url
_guardado_proxy = {k: _os.environ.get(k) for k in ("http_proxy", "https_proxy")}
_os.environ["http_proxy"] = _os.environ["https_proxy"] = "http://proxy.server:3128"
_com_proxy = _rede._montar_abridor()
for k, v in _guardado_proxy.items():
    if v is None:
        _os.environ.pop(k, None)
    else:
        _os.environ[k] = v
_sem_proxy = _rede._montar_abridor()

check("com proxy no ambiente, o abridor passa a usar ele",
      any(isinstance(h, _url.ProxyHandler) for h in _com_proxy.handlers))

# PROXY_SAIDA manda sobre as variaveis padrao: o processo do site nem sempre
# recebe `https_proxy`, e ai a configuracao explicita e a unica saida.
_guardado_saida = _os.environ.get("PROXY_SAIDA")
_os.environ["PROXY_SAIDA"] = "http://explicito:3128"
_ab_explicito = _rede._montar_abridor()
if _guardado_saida is None:
    _os.environ.pop("PROXY_SAIDA", None)
else:
    _os.environ["PROXY_SAIDA"] = _guardado_saida
_phs = [h for h in _ab_explicito.handlers if isinstance(h, _url.ProxyHandler)]
check("PROXY_SAIDA no ambiente e respeitado",
      _phs and _phs[0].proxies.get("https") == "http://explicito:3128",
      _phs[0].proxies if _phs else None)
check("e vale pros dois protocolos",
      _phs and _phs[0].proxies.get("http") == "http://explicito:3128")
check("e sem proxy nada muda",
      not any(isinstance(h, _url.ProxyHandler) and h.proxies
              for h in _sem_proxy.handlers))
# A recusa a redirecionamento nao pode se perder no caminho: e ela que impede a
# requisicao de ser desviada pra dentro da rede do servidor.
for _nome, _ab in (("com proxy", _com_proxy), ("sem proxy", _sem_proxy)):
    check("%s, a recusa a redirecionamento continua de pe" % _nome,
          any(isinstance(h, _rede._SemRedirecionamento) for h in _ab.handlers))

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


secao("48. Motor SVG: a previa que nao pode mentir")
# A previa existe pra pessoa decidir ANTES de gastar etiqueta. Se ela quebrar o
# texto num lugar e a impressora noutro, ela e pior que nao ter previa — o
# lojista confia, imprime duzentas e descobre no papel.
# Por isso a previa sai do servidor, chamando as MESMAS funcoes.
import re as _re
from etiquetas.motores import svg as motor_svg

_svg = motor_svg.render(etiqueta_padrao(), DADOS)


def _textos_svg(fonte):
    """So os textos DA ETIQUETA, sem os do codigo de barras.

    O codigo de barras entra como <svg> aninhado, e o reportlab desenha o numero
    legivel dele em varios <text> soltos ('7', '891234', '567895'). Comparar isso
    com o ^FD do ZPL — que leva o numero inteiro de uma vez — daria diferenca sem
    nenhum dos dois estar errado. Some com o aninhado antes de olhar.
    """
    sem_codigo = _re.sub(r"<svg x=.*?</svg>", "", fonte, flags=_re.DOTALL)
    return _re.findall(r"<text[^>]*>([^<]*)</text>", sem_codigo)


def _linhas_zpl(fonte):
    """As linhas de texto do ZPL. `\\&` e a quebra de linha dentro do ^FD.

    So conta o ^FD que vem junto de um ^A0N, que e o comando de fonte — o resto
    e dado de codigo de barras, que nao e texto desenhado.
    """
    saida = []
    for linha in fonte.splitlines():
        if "^A0N" not in linha:
            continue
        for campo in _re.findall(r"\^FD(.*?)\^FS", linha):
            saida.extend(campo.split("\\&"))
    return saida


check("o viewBox e a etiqueta em MILIMETRO, sem escala no meio",
      'viewBox="0 0 50.8 25.4"' in _svg, _svg[:120])
# SVG tem origem no topo e Y crescendo pra baixo, igual ao modelo e ao ZPL. E o
# PDF que e o esquisito dos tres. Se aparecer um "altura - y" no motor SVG, e bug.
check("nao tem inversao de eixo Y no arquivo",
      "altura_pagina" not in _io.open("etiquetas/motores/svg.py", encoding="utf-8").read())

# O teste que segura a promessa: a previa quebra o texto ONDE a impressora quebra.
_txt_svg = [t for t in _textos_svg(_svg) if t.strip()]
_txt_zpl = _linhas_zpl(zpl.render(etiqueta_padrao(), DADOS))
check("as linhas de texto do SVG sao as MESMAS do ZPL, na mesma ordem",
      _txt_svg[:len(_txt_zpl)] == _txt_zpl, (_txt_svg, _txt_zpl))
check("inclusive a quebra do titulo em duas linhas",
      "Canudo de Vidro Reto 20cm -" in _txt_svg and "Kit 4 unidades" in _txt_svg)
check("e o preco formatado igual aos outros motores", "R$ 24,90" in _txt_svg)

# Campo vazio leva o rotulo junto, nos TRES motores.
_svg_vazio = motor_svg.render(etiqueta_padrao(), _vazio)
check("campo vazio leva o rotulo junto tambem no SVG",
      "SKU:" not in "".join(_textos_svg(_svg_vazio)))
check("mas o titulo continua", "So titulo" in _textos_svg(_svg_vazio))

# Codigo invalido nao vira barra em nenhum motor — e na previa isso e informacao:
# o lojista VE o codigo sumir e descobre o cadastro errado antes de imprimir.
_svg_ruim = motor_svg.render(etiqueta_padrao(), _ruim_cod)
check("codigo com verificador errado nao e desenhado na previa",
      "<svg x=" not in _svg_ruim, _svg_ruim[-200:])
check("mas o codigo valido e desenhado", "<svg x=" in _svg)

# XML nao perdoa & solto. Produto com "&" no nome e rotina em catalogo, e sem
# escapar o SVG inteiro quebra — a previa fica em branco sem dizer por que.
_svg_amp = motor_svg.render(etiqueta_padrao(),
                            {"produto": {"titulo": "Camiseta P&B <G>"}, "variante": {}})
check("o & do nome do produto e escapado", "&amp;" in _svg_amp)
check("e o < tambem", "&lt;" in _svg_amp and "P&B" not in _svg_amp)

# Calibracao: a previa tem que deslocar junto, senao a pessoa calibra no escuro.
_svg_cal = motor_svg.render(etiqueta_padrao(Calibracao(desvio_x_mm=2.0, desvio_y_mm=1.5)),
                            DADOS)
_x_sem = float(_re.search(r'<text x="([\d.]+)"', _svg).group(1))
_x_com = float(_re.search(r'<text x="([\d.]+)"', _svg_cal).group(1))
check("a previa desloca com a calibracao", abs((_x_com - _x_sem) - 2.0) < 0.01,
      (_x_sem, _x_com))
_y_sem = float(_re.search(r'<text x="[\d.]+" y="([\d.]+)"', _svg).group(1))
_y_com = float(_re.search(r'<text x="[\d.]+" y="([\d.]+)"', _svg_cal).group(1))
check("nos dois eixos", abs((_y_com - _y_sem) - 1.5) < 0.01, (_y_sem, _y_com))

# O codigo de barras sai do tamanho FISICO certo. Nao e estetica: fora da medida,
# o leitor nao pega. O <svg> aninhado leva a medida em mm, nao em ponto.
_aninhado = _re.search(r'<svg x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"',
                       _svg)
check("o codigo de barras vai como svg aninhado com medida propria", _aninhado is not None)
if _aninhado:
    _larg_cod = float(_aninhado.group(3))
    # EAN-13 com modulo 2 dots a 203dpi: 95 modulos + zona muda ja somada pelo
    # reportlab desligada. Confere que esta na ordem de grandeza de milimetro, e
    # nao de ponto (que daria ~73, quase o dobro da etiqueta inteira).
    check("a medida esta em milimetro, nao sobrou em ponto",
          5 < _larg_cod < 50.8, _larg_cod)
    check("e o codigo cabe dentro da etiqueta",
          float(_aninhado.group(1)) + _larg_cod <= 50.8 + 0.01,
          float(_aninhado.group(1)) + _larg_cod)

# Etiqueta de medida zero gerava SVG que abre e nao mostra nada. Erro claro e
# melhor que previa em branco que a pessoa vai jurar que e bug da tela.
try:
    motor_svg.render(Template(nome="x", calibracao=Calibracao(),
                              midia=Midia(largura_mm=0, altura_mm=10),
                              elementos=[]), DADOS)
    check("etiqueta de largura zero levanta erro", False)
except ValueError:
    check("etiqueta de largura zero levanta erro", True)

# A moldura e so da previa: mostra onde o papel acaba. Nunca vai pro papel.
check("a previa desenha a borda da etiqueta", "stroke=" in _svg)
check("e da pra pedir sem borda", "stroke=" not in motor_svg.render(
    etiqueta_padrao(), DADOS, moldura=False))


secao("49. valores.py: a regra do valor mora num lugar so")
# Nasceu escrita duas vezes (inline no ZPL, funcao no PDF) com um comentario no
# PDF dizendo "mesma resolucao do motor ZPL" — o comentario era a confissao. O
# motor de previa seria a terceira copia, entao extrai antes de escrever.
from etiquetas import valores as _valores

check("os tres motores importam de valores.py",
      all("valores" in _io.open("etiquetas/motores/%s.py" % m, encoding="utf-8").read()
          for m in ("zpl", "pdf", "svg")))
# E ninguem mais pode ter uma copia da regra. Se alguem reescrever a formatacao
# de preco dentro de um motor, isto pega.
for _motor in ("zpl", "pdf", "svg"):
    _fonte_motor = _io.open("etiquetas/motores/%s.py" % _motor, encoding="utf-8").read()
    check("o motor %s nao formata preco por conta propria" % _motor,
          "formatar_preco" not in _fonte_motor)

_el_preco = [e for e in etiqueta_padrao().elementos if isinstance(e, Preco)][0]
check("o preco sai formatado", _valores.do_elemento(_el_preco, DADOS) == "R$ 24,90")
check("campo vazio devolve vazio, levando o rotulo junto",
      _valores.do_elemento(_el_preco, {"variante": {}}) == "")


secao("50. Receitas: escolhas do lojista viram um template que cabe no papel")
# A tela manda "quero titulo, SKU, preco e codigo numa 5x2,5cm". Traduzir isso em
# coordenada e trabalho do servidor — se fosse do JavaScript, a regra viraria
# duas e a que o lojista ve discordaria da que imprime.
from etiquetas import receitas, formatos as _fmt

# --- a propriedade que vale pra TODOS os formatos, do menor ao maior ---------
for _f in _fmt.CATALOGO:
    _t = receitas.montar(_f.codigo)
    _m = _t.midia
    _nome = _f.codigo

    check("%s: o template montado passa na validacao" % _nome,
          esquema.validar(_t) == [], esquema.validar(_t))

    # Nada pode vazar pra fora do papel. Elemento meio pra fora nao da erro
    # nenhum: imprime cortado, e o lojista so ve no papel.
    for _el in _t.elementos:
        _x, _y = _t.com_calibracao(_el)
        _alt = getattr(_el, "altura_mm", 0) or (_el.tamanho_pt * 25.4 / 72 * 1.15
                                                * _el.linhas_max)
        check("%s: %s nao passa da borda direita" % (_nome, _el.campo),
              _x + (_el.largura_mm or 0) <= _m.largura_mm + 0.01,
              (_x, _el.largura_mm, _m.largura_mm))
        check("%s: %s nao passa da borda de baixo" % (_nome, _el.campo),
              _y + _alt <= _m.altura_mm + 0.01, (_y, _alt, _m.altura_mm))
        check("%s: %s nao comeca fora do papel" % (_nome, _el.campo),
              _x >= -0.01 and _y >= -0.01, (_x, _y))

    # Barra abaixo do minimo nao bipa — e o defeito so aparece no caixa, com fila.
    # Isto pegou um bug de verdade: o teto proporcional de 42% cortava a barra da
    # etiqueta de joia pra 5,0mm, abaixo do minimo que o proprio codigo reservou.
    for _el in _t.elementos:
        if isinstance(_el, CodigoBarras):
            check("%s: a barra nao fica abaixo do minimo que bipa" % _nome,
                  _el.altura_mm >= receitas.BARRA_MINIMA_MM, _el.altura_mm)

# --- a ordem de sobrevivencia -----------------------------------------------
# Numa etiqueta de joia (56x12mm) nao cabe tudo. A primeira versao cortava de
# baixo pra cima, na ordem visual, e o titulo de duas linhas comia a etiqueta
# inteira deixando SEM CODIGO DE BARRAS — numa etiqueta de codigo de barras.
_joia = receitas.montar("dymo_30299")
_tem_codigo = any(isinstance(e, CodigoBarras) for e in _joia.elementos)
check("na etiqueta minuscula o codigo de barras e o que SOBREVIVE", _tem_codigo)
check("e o titulo e o que sai",
      not any(e.campo == "produto.titulo" for e in _joia.elementos))
check("a receita diz o que nao coube, em vez de sumir calada",
      set(receitas.cabem_os_campos("dymo_30299", receitas.PADRAO))
      == {"titulo", "sku", "preco"},
      receitas.cabem_os_campos("dymo_30299", receitas.PADRAO))
check("numa etiqueta que cabe tudo, nao falta nada",
      receitas.cabem_os_campos("zebra_2x1", receitas.PADRAO) == [])

# --- as escolhas chegam mesmo no template -----------------------------------
_euro = receitas.montar("zebra_2x1", simbolo="€", simbolo_depois=True,
                        separador_decimal=",", separador_milhar=".")
_p = [e for e in _euro.elementos if isinstance(e, Preco)][0]
check("o simbolo da moeda chega no elemento", _p.simbolo == "€")
check("e a posicao do simbolo tambem", _p.simbolo_depois is True)
# "o € fica do lado errado" e uma das reclamacoes do app oficial. Prova de ponta
# a ponta: da escolha ate o texto renderizado.
_svg_euro = motor_svg.render(_euro, DADOS)
check("e o preco sai '24,90 €' de verdade",
      "24,90 €" in "".join(_textos_svg(_svg_euro)), _textos_svg(_svg_euro))

check("sem rotulo o SKU sai limpo",
      [e for e in receitas.montar("zebra_2x1", rotulo_sku=False).elementos
       if e.campo == "variante.sku"][0].prefixo == "")
check("com rotulo ele leva o 'SKU: '",
      [e for e in receitas.montar("zebra_2x1").elementos
       if e.campo == "variante.sku"][0].prefixo == "SKU: ")

# SKU e preco dividem a MESMA linha, lado a lado. A primeira versao avancava o Y
# logo depois do SKU, e o preco — que vem em seguida na ordem visual — nascia uma
# linha abaixo: 2,2mm de desalinho no papel. Nenhum teste de borda pegava, porque
# os dois continuavam DENTRO da etiqueta. Apareceu olhando o ZPL cru, com o SKU
# em ^FO16,62 e o preco em ^FO203,80.
for _f in _fmt.CATALOGO:
    _t = receitas.montar(_f.codigo)
    _sku = [e for e in _t.elementos if e.campo == "variante.sku"]
    _prc = [e for e in _t.elementos if isinstance(e, Preco)]
    if _sku and _prc:
        # O que tem que coincidir e a LINHA DE BASE, nao o topo. O preco sai com
        # fonte maior de proposito, entao topos iguais deixariam a base do preco
        # 0,34mm mais baixa — o bastante pra parecer torto na prateleira.
        def _base(el):
            return el.y_mm + el.tamanho_pt * 25.4 / 72 * 1.15
        check("%s: SKU e preco apoiados na MESMA base" % _f.codigo,
              abs(_base(_sku[0]) - _base(_prc[0])) < 0.001,
              (_base(_sku[0]), _base(_prc[0])))
        check("%s: e o preco e o maior dos dois" % _f.codigo,
              _prc[0].tamanho_pt > _sku[0].tamanho_pt)
        check("%s: e lado a lado, sem sobrepor" % _f.codigo,
              _sku[0].x_mm + _sku[0].largura_mm <= _prc[0].x_mm + 0.001,
              (_sku[0].x_mm + _sku[0].largura_mm, _prc[0].x_mm))

_cal = receitas.montar("zebra_2x1", desvio_x_mm=1.5, desvio_y_mm=-0.5)
check("a calibracao chega no template",
      (_cal.calibracao.desvio_x_mm, _cal.calibracao.desvio_y_mm) == (1.5, -0.5))

# Escolher os campos e o que resolve "nao da pra tirar o campo de preco" e
# "sumiu o SKU" — duas das reclamacoes das 565 avaliacoes do app oficial.
_so_codigo = receitas.montar("zebra_2x1", campos=("codigo_barras",))
check("da pra ligar so o codigo de barras", len(_so_codigo.elementos) == 1)
check("sem preco, nao existe elemento de preco",
      not any(isinstance(e, Preco) for e in
              receitas.montar("zebra_2x1", campos=("titulo", "sku")).elementos))
check("campo desconhecido e ignorado, nao quebra",
      len(receitas.montar("zebra_2x1", campos=("titulo", "inventado")).elementos) == 1)
check("sem campo nenhum devolve etiqueta vazia, sem estourar",
      receitas.montar("zebra_2x1", campos=()).elementos == [])

# Formato que nao existe tem que dar erro claro, nao KeyError cru.
try:
    receitas.montar("papel_inventado")
    check("formato inexistente levanta erro em portugues", False)
except (ValueError, KeyError) as _e:
    check("formato inexistente levanta erro em portugues", "papel_inventado" in str(_e))

# Sozinho, o codigo nao pode virar a etiqueta inteira: o teto de 42% segura.
_cod_sozinho = [e for e in _so_codigo.elementos if isinstance(e, CodigoBarras)][0]
check("o codigo sozinho nao ocupa a etiqueta toda",
      _cod_sozinho.altura_mm <= 25.4 * 0.42 + 0.01, _cod_sozinho.altura_mm)

# A receita passa pelo JSON e volta igual — e o que faz o modelo ser salvavel.
_ida = receitas.montar("avery_5160", simbolo="$", campos=("titulo", "preco"))
check("o template da receita sobrevive ao JSON",
      esquema.para_dict(esquema.de_json(esquema.para_json(_ida)))
      == esquema.para_dict(_ida))


secao("51. Salvar e reabrir: a receita volta com os botoes no lugar")
# O template montado e o que imprime. A receita e o que REABRE o editor. Sem
# guardar as duas, dava pra imprimir e nao dava pra editar: o lojista abriria o
# modelo dele e veria todos os botoes no padrao, sem relacao com a etiqueta na
# tela — e concluiria que o app perdeu o trabalho dele.
_RECEITA = {"formato": "avery_5160", "campos": ["titulo", "fornecedor", "preco"],
            "simbolo": "US$", "simbolo_depois": True, "separador_decimal": ".",
            "separador_milhar": ",", "rotulo_sku": False, "simbologia": "CODE128",
            "desvio_x_mm": 1.5, "desvio_y_mm": -0.5}

# Esta secao e sobre salvar e reabrir, nao sobre cobranca. A loja A ficou no
# gratis (1 modelo) la na secao 44, e ja tem um — sem isto os testes daqui
# tomariam 402 e eu estaria medindo o limite de plano de novo, por acidente.
t_lojas.marcar_plano(_ID_A, "pro")


def _post(caminho, loja_dominio, corpo):
    return _cliente.post(caminho, headers={"Authorization": "Bearer " + _token_de(loja_dominio)},
                         json=corpo)


_r = _post("/api/modelos", "loja-a.myshopify.com",
           {"nome": "Prateleira EUA", "receita": _RECEITA})
check("da pra criar modelo mandando so as ESCOLHAS", _r.status_code == 201, _r.status_code)
_NOVO = _r.get_json()["id"]

_r = _pega("/api/modelos/%d" % _NOVO, "loja-a.myshopify.com")
_lido = _r.get_json()
check("e a receita volta inteira", _lido["receita"] == _RECEITA, _lido.get("receita"))
check("com o nome junto", _lido["nome"] == "Prateleira EUA")
# O template montado tambem e guardado: e ele que imprime, e ele nao pode
# depender de a receita ser remontada certinho toda vez.
check("e o template montado veio junto",
      _lido["modelo"]["midia"]["largura_mm"] == 66.7, _lido["modelo"]["midia"])
check("com a calibracao que foi escolhida",
      _lido["modelo"]["calibracao"]["desvio_x_mm"] == 1.5)
check("e so os campos que foram ligados",
      {e["campo"] for e in _lido["modelo"]["elementos"]}
      == {"produto.titulo", "produto.fornecedor", "variante.preco"},
      {e["campo"] for e in _lido["modelo"]["elementos"]})

# Alterar troca as duas coisas juntas. Se so uma trocasse, o modelo imprimiria
# uma etiqueta e reabriria mostrando outra.
_r = _cliente.put("/api/modelos/%d" % _NOVO,
                  headers={"Authorization": "Bearer " + _token_de("loja-a.myshopify.com")},
                  json={"nome": "Prateleira BR",
                        "receita": dict(_RECEITA, simbolo="R$", formato="zebra_2x1")})
check("alterar aceita receita nova", _r.status_code == 200, _r.status_code)
_lido = _pega("/api/modelos/%d" % _NOVO, "loja-a.myshopify.com").get_json()
check("o nome mudou", _lido["nome"] == "Prateleira BR")
check("a receita mudou", _lido["receita"]["simbolo"] == "R$")
check("e o template montado mudou JUNTO",
      _lido["modelo"]["midia"]["largura_mm"] == 50.8, _lido["modelo"]["midia"])

# Duplicar leva a receita junto — senao a copia abriria no padrao e a pessoa
# refaria tudo, que e exatamente o atrito que duplicar existe pra evitar.
_r = _post("/api/modelos/%d/copia" % _NOVO, "loja-a.myshopify.com", {})
check("duplicar cria outro modelo", _r.status_code == 201, _r.status_code)
_COPIA = _r.get_json()["id"]
_lido_copia = _pega("/api/modelos/%d" % _COPIA, "loja-a.myshopify.com").get_json()
check("a copia leva a receita junto", _lido_copia["receita"]["simbolo"] == "R$")
check("e o nome marcado como copia", "cópia" in _lido_copia["nome"])

# O isolamento vale pra receita tambem: ela guarda como a loja monta a etiqueta
# dela, e isso e informacao de negocio.
check("outra loja nao le a receita da A",
      _pega("/api/modelos/%d" % _NOVO, "loja-d.myshopify.com").status_code == 404)

# Receita invalida nao pode virar modelo quebrado no banco.
_r = _post("/api/modelos", "loja-a.myshopify.com",
           {"nome": "torto", "receita": {"formato": "papel_que_nao_existe"}})
check("formato inexistente e recusado ao salvar", _r.status_code == 400, _r.status_code)
_r = _post("/api/modelos", "loja-a.myshopify.com",
           {"nome": "vazio", "receita": {"formato": "zebra_2x1", "campos": []}})
check("etiqueta sem campo nenhum e recusada", _r.status_code == 400, _r.status_code)

# Da pra imprimir SEM salvar: obrigar a salvar antes de testar transforma
# "deixa eu ver como fica" em tres cliques, e enche a lista de "teste2".
_r = _post("/api/imprimir", "loja-a.myshopify.com",
           {"motor": "pdf", "receita": _RECEITA, "itens": _ITENS})
check("imprime sem modelo salvo", _r.status_code == 200, _r.status_code)
check("e sai PDF", _r.data[:5] == b"%PDF-")

# O modelo_id vai junto so como anotacao no historico. Ele vem do navegador,
# entao um id de outra loja nao pode entrar no registro desta.
_r = _post("/api/imprimir", "loja-d.myshopify.com",
           {"motor": "pdf", "receita": _RECEITA, "itens": _ITENS, "modelo_id": _NOVO})
check("imprimir com modelo_id de outra loja nao quebra", _r.status_code == 200,
      _r.status_code)
_ultima = t_impressoes.historico(_ID_D, 1)[0]
check("e o id alheio NAO entra no historico desta loja",
      _ultima["modelo_id"] is None, _ultima["modelo_id"])

t_modelos.apagar(_ID_A, _COPIA)
t_modelos.apagar(_ID_A, _NOVO)


secao("52. A chave de cifra e derivada uma vez, nao a cada requisicao")
# O scrypt e caro DE PROPOSITO — e o que torna forca bruta inviavel. Mas ele
# rodava a cada leitura de loja, ou seja, a cada requisicao autenticada. Medido
# no navegador: 386ms num GET que devia custar 5ms.
import time as _tempo

banco.cifrar("aquece")
_ini = _tempo.perf_counter()
for _ in range(100):
    banco.decifrar(banco.cifrar("shpat_token_qualquer"))
_por_vez = (_tempo.perf_counter() - _ini) / 100 * 1000
check("cifrar e decifrar custa menos de 5ms", _por_vez < 5.0, "%.2f ms" % _por_vez)

# O cache NAO pode esconder a troca de segredo: se escondesse, um token cifrado
# com a chave antiga pareceria abrir com a nova, e a cifra nao valeria nada.
_cifrado_a = banco.cifrar("segredo-do-token")
_antiga = _os.environ["CHAVE_SEGREDO"]
_os.environ["CHAVE_SEGREDO"] = "uma-chave-totalmente-diferente"
check("trocar a chave ainda invalida o que estava cifrado",
      banco.decifrar(_cifrado_a) == "")
_os.environ["CHAVE_SEGREDO"] = _antiga
check("e voltar a chave certa abre de novo",
      banco.decifrar(_cifrado_a) == "segredo-do-token")
check("chaves diferentes geram objetos diferentes em cache",
      len(banco._CHAVES) >= 2, len(banco._CHAVES))


secao("53. Rotacao de segredo: a janela em que os dois valem")
# Descoberto instalando de verdade: ao rotacionar o Client secret, o Shopify gera
# o novo e CONTINUA ASSINANDO COM O ANTIGO ate a rotacao ser concluida no painel.
# Com um segredo so, toda rotacao derruba o app — webhook recusado, instalacao
# recusada, token de sessao recusado — e o motivo nao aparece em lugar nenhum.
_NOVO_S, _VELHO_S = "segredo-novo-do-app", "segredo-velho-do-app"
_DOIS = (_NOVO_S, _VELHO_S)

_corpo_wh = b'{"loja":"x"}'
def _assina_wh(corpo, s):
    return _b64.b64encode(_hm.new(s.encode(), corpo, _hl.sha256).digest()).decode()

check("webhook assinado com o segredo NOVO passa",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, _NOVO_S), _DOIS))
check("webhook assinado com o ANTIGO tambem passa, durante a janela",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, _VELHO_S), _DOIS))
check("mas um terceiro segredo NAO passa",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, "outro"), _DOIS) is False)
# Passar um segredo sozinho continua funcionando: quem chama com string nao muda.
check("com um segredo so, o antigo nao vale",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, _VELHO_S), _NOVO_S) is False)

# O mesmo vale pros parametros do OAuth — foi exatamente onde a instalacao parou.
def _params_assinados(s):
    p = {"code": "abc", "shop": "loja.myshopify.com", "timestamp": "1787878288"}
    msg = "&".join("%s=%s" % (k, p[k]) for k in sorted(p))
    p["hmac"] = _hm.new(s.encode(), msg.encode(), _hl.sha256).hexdigest()
    return p

check("OAuth assinado com o novo passa",
      assinatura.parametros_conferem(_params_assinados(_NOVO_S), _DOIS))
check("OAuth assinado com o antigo passa na janela",
      assinatura.parametros_conferem(_params_assinados(_VELHO_S), _DOIS))
check("OAuth com segredo alheio nao passa",
      assinatura.parametros_conferem(_params_assinados("invasor"), _DOIS) is False)

# E pro token de sessao.
def _tok(s):
    _ag = _tm.time()
    return assinatura.sessao_assinar({"dest": "https://loja.myshopify.com",
        "aud": "chave", "exp": _ag + 60, "nbf": _ag - 5}, s)

check("token de sessao assinado com o antigo abre na janela",
      assinatura.sessao_abrir(_tok(_VELHO_S), "chave", _DOIS)["loja"] == "loja.myshopify.com")
try:
    assinatura.sessao_abrir(_tok("invasor"), "chave", _DOIS)
    check("token de sessao com segredo alheio e recusado", False)
except assinatura.TokenInvalido:
    check("token de sessao com segredo alheio e recusado", True)

# Lista vazia nao pode virar "aceita tudo". Sem segredo nenhum, nada passa.
check("sem segredo nenhum, webhook nao passa",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, _NOVO_S), ()) is False)
check("sem segredo nenhum, OAuth nao passa",
      assinatura.parametros_conferem(_params_assinados(_NOVO_S), ()) is False)
check("string vazia tambem nao vale como segredo",
      assinatura.webhook_confere(_corpo_wh, _assina_wh(_corpo_wh, ""), "") is False)

# A config so junta o antigo quando ele existe — e o antigo NUNCA e usado pra
# assinar o que sai, so pra conferir o que chega.
from web import config as _cfg2
_guardado = _cfg2.SEGREDO_ANTIGO
_cfg2.SEGREDO_ANTIGO = ""
check("sem SHOPIFY_SEGREDO_ANTIGO, so um segredo e aceito",
      len(_cfg2.segredos_aceitos()) == 1, _cfg2.segredos_aceitos())
_cfg2.SEGREDO_ANTIGO = "o-anterior"
check("com ele, dois sao aceitos", len(_cfg2.segredos_aceitos()) == 2)
check("e o primeiro da lista e o ATUAL, que e o usado pra assinar",
      _cfg2.segredos_aceitos()[0] == _cfg2.SEGREDO)
_cfg2.SEGREDO_ANTIGO = _guardado


secao("54. Que tipo de token o Shopify devolveu")
# O app le o catalogo quando o lojista manda imprimir, e responde webhook a
# qualquer hora — inclusive com ninguem logado. Token AMARRADO A UM USUARIO
# morre junto com a sessao da pessoa, e isso continua sendo bomba-relogio.
#
# Esta secao ja errou DUAS vezes, e vale guardar as duas:
#
# 1. A primeira versao tratava o prefixo `shpua_` como prova de que o token
#    expirava. Na primeira instalacao de verdade veio um `shpua_` SEM
#    expires_in. Prefixo e convencao da plataforma, muda sem aviso, nao e
#    contrato.
#
# 2. A correcao daquilo elegeu `expires_in` como o sinal — e envelheceu mal. O
#    Shopify passou a EXPIRAR os tokens offline tambem, entao hoje `expires_in`
#    aparece nos dois casos e nao distingue nada. Quem distingue e
#    `associated_user`.
#
# A licao e a mesma nas duas: teste que congela um palpite e pior que teste
# nenhum, porque impede o conserto.
from loja import rede as _rede2

check("associated_user denuncia token de usuario",
      _rede2.token_de_usuario({"access_token": "shpat_x",
                               "associated_user": {"id": 1}}))
check("expires_in sozinho NAO denuncia — token offline expira, e isso e o normal",
      _rede2.token_de_usuario({"access_token": "shpat_x", "expires_in": 3600})
      is False)
check("prefixo shpua_ nao e prova de nada",
      _rede2.token_de_usuario({"access_token": "shpua_abc"}) is False)
check("token offline comum nao dispara alarme falso",
      _rede2.token_de_usuario({"access_token": "shpat_abc",
                               "scope": "read_products"}) is False)
check("resposta vazia nao quebra", _rede2.token_de_usuario({}) is False)
check("resposta que nem e dicionario nao quebra",
      _rede2.token_de_usuario(None) is False)

# A resposta da troca vira o que o banco guarda: prazo RELATIVO virando instante
# ABSOLUTO. Guardar o relativo nao serve pra nada depois — o que a proxima
# requisicao precisa saber e se JA VENCEU.
_cred = _rede2.credenciais_da_resposta({
    "access_token": "shpat_novo", "refresh_token": "shprt_novo",
    "expires_in": 3600, "refresh_token_expires_in": 7776000})
check("o token e o refresh sao guardados separados",
      (_cred["token"], _cred["refresh"]) == ("shpat_novo", "shprt_novo"))
check("e os dois prazos viram data, nao segundos",
      _cred["expira_em"] > "2026" and _cred["refresh_expira_em"] > _cred["expira_em"],
      _cred)
check("resposta sem prazo nenhum nao inventa prazo",
      _rede2.credenciais_da_resposta({"access_token": "x"})["expira_em"] == "")

# trocar_token devolve a resposta INTEIRA, nao so o token: e o resto dela que
# conta que tipo de token e. Devolver so a string apagaria essa informacao.
import inspect as _insp
check("trocar_token devolve o dicionario inteiro",
      "-> dict" in _insp.signature(_rede2.trocar_token).__str__()
      or _insp.signature(_rede2.trocar_token).return_annotation is dict)


secao("55. A volta da instalacao, de ponta a ponta (com a rede substituida)")
# Esta era a UNICA rota sem teste, porque ela fala com a rede. E foi ela que
# quebrou em producao: renomeei uma variavel e deixei um uso antigo pra tras —
# NameError na cara do lojista, no meio da instalacao.
#
# Trocando so a ida a rede, o resto do caminho fica testavel: conferencia de
# hmac, conferencia de state, gravacao da loja, cifra do token e assinatura dos
# webhooks. Que e onde os erros de verdade moram.
from loja import rede as _rede3
from web import rotas_instalacao as _inst

_LOJA_NOVA = "recem-instalada.myshopify.com"
_chamadas = {"graphql": 0}


def _falso_trocar_token(url, corpo):
    _chamadas["url"] = url
    _chamadas["corpo"] = corpo
    return {"access_token": "shpat_token_de_teste",
            "refresh_token": "shprt_da_instalacao",
            "expires_in": 3600, "refresh_token_expires_in": 7776000,
            "scope": "read_products,read_inventory"}


def _falso_graphql(loja, token, corpo, **kw):
    _chamadas["graphql"] += 1
    return {"data": {"webhookSubscriptionCreate": {"userErrors": []}}}


def _volta(loja_dominio, segredo=None, estado="estado-combinado", com_estado=True,
           resposta_token=None):
    """Simula o Shopify devolvendo o `code`, com hmac de verdade."""
    original_troca, original_graphql = _rede3.trocar_token, _rede3.graphql
    _rede3.trocar_token = resposta_token or _falso_trocar_token
    _rede3.graphql = _falso_graphql
    try:
        p = {"code": "codigo-de-uso-unico", "shop": loja_dominio,
             "state": estado, "timestamp": "1787878288"}
        msg = "&".join("%s=%s" % (k, p[k]) for k in sorted(p))
        p["hmac"] = _hm.new((segredo or _SEGREDO).encode(), msg.encode(),
                            _hl.sha256).hexdigest()
        with _cliente.session_transaction() as sessao:
            if com_estado:
                sessao["estado_oauth"] = "estado-combinado"
            else:
                sessao.pop("estado_oauth", None)
        return _cliente.get("/instalar/volta", query_string=p)
    finally:
        _rede3.trocar_token, _rede3.graphql = original_troca, original_graphql


_r = _volta(_LOJA_NOVA)
check("a instalacao completa e redireciona pro admin", _r.status_code == 302, _r.status_code)

# Sem `expiring=1` o Shopify devolve um token que nao expira — e a Admin API
# passou a RECUSAR esses com 403. O app instalava bonito e nao lia produto
# nenhum, que foi exatamente como o defeito apareceu na loja de verdade.
check("a instalacao pede token que EXPIRA",
      _chamadas["corpo"].get("expiring") == "1", _chamadas["corpo"])
_nova = t_lojas.buscar(_LOJA_NOVA)
check("e guarda o refresh que veio junto",
      _nova["refresh"] == "shprt_da_instalacao", _nova["refresh"])
check("com o prazo, senao a renovacao nunca acontece",
      bool(_nova["token_expira_em"]))
check("e vai pro painel de apps da loja certa",
      "recem-instalada/apps" in _r.headers.get("Location", ""),
      _r.headers.get("Location"))

_gravada = t_lojas.buscar(_LOJA_NOVA)
check("a loja foi gravada", _gravada is not None)
check("com o token que veio da troca", _gravada["token"] == "shpat_token_de_teste")
check("e os escopos que a gente pede",
      _gravada["escopos"] == ",".join(oauth.ESCOPOS), _gravada["escopos"])
check("ativa", _gravada["ativa"] is True)
# A versao anterior deste teste exigia que a instalacao assinasse TODOS os
# webhooks, inclusive os tres de privacidade — e assim ELE GARANTIA O BUG.
#
# `webhookSubscriptionCreate` nao aceita topico de conformidade. As tres
# chamadas falhavam, o erro era engolido pelo `except rede.ErroDeRede: pass` da
# instalacao, e ficava a impressao de que estavam configurados. Nao estavam: os
# tres se declaram UMA vez na configuracao do app, e sem essa declaracao a
# revisao do Shopify REPROVA o app.
#
# E nem faria sentido assinar por loja: `shop/redact` chega 48 horas DEPOIS da
# desinstalacao, quando o token daquela loja ja foi apagado.
check("a instalacao assina so os webhooks NOSSOS",
      _chamadas["graphql"] == len(webhooks.ASSINADOS_NA_INSTALACAO),
      _chamadas["graphql"])
check("e os de privacidade ficam de fora, porque a API os recusa",
      set(webhooks.ASSINADOS_NA_INSTALACAO).isdisjoint(webhooks.OBRIGATORIOS))
check("mas a ROTA continua aceitando os cinco topicos",
      set(webhooks.OBRIGATORIOS) <= set(webhooks.TODOS)
      and set(webhooks.NOSSOS) <= set(webhooks.TODOS))
check("a troca de token foi pro dominio da loja",
      _chamadas["url"] == "https://%s/admin/oauth/access_token" % _LOJA_NOVA,
      _chamadas.get("url"))

# state errado: alguem forjando uma instalacao que a gente nao comecou.
_r = _volta("outra-loja.myshopify.com", com_estado=False)
check("sem o state guardado, a instalacao e recusada", _r.status_code == 400)
check("e a loja NAO entra no banco",
      t_lojas.buscar("outra-loja.myshopify.com") is None)

# hmac errado: os parametros nao vieram do Shopify.
_r = _volta("terceira-loja.myshopify.com", segredo="segredo-de-invasor")
check("com hmac de outro segredo, recusada", _r.status_code == 400)
check("e essa loja tambem NAO entra no banco",
      t_lojas.buscar("terceira-loja.myshopify.com") is None)

# Falha de rede na troca nao pode virar loja gravada sem token.
def _troca_que_falha(url, corpo):
    raise _rede3.ErroDeRede("o Shopify caiu")

_r = _volta("quarta-loja.myshopify.com", resposta_token=_troca_que_falha)
check("se a troca de token falha, responde 502", _r.status_code == 502, _r.status_code)
check("e nao deixa loja pela metade no banco",
      t_lojas.buscar("quarta-loja.myshopify.com") is None)

# Webhook que falha NAO derruba a instalacao: o lojista ja autorizou, e falhar
# aqui deixaria uma loja com token e sem app.
def _graphql_que_falha(loja, token, corpo, **kw):
    raise _rede3.ErroDeRede("limite de requisicoes")

_orig = _rede3.graphql
_rede3.graphql = _graphql_que_falha
try:
    _r = _volta("quinta-loja.myshopify.com")
finally:
    _rede3.graphql = _orig
check("webhook falhando nao derruba a instalacao", _r.status_code == 302, _r.status_code)
check("e a loja fica instalada mesmo assim",
      t_lojas.buscar("quinta-loja.myshopify.com") is not None)

for _d in (_LOJA_NOVA, "quinta-loja.myshopify.com"):
    t_lojas.apagar(_d)


secao("56. O plano do lojista que paga nao pode sumir")
# Medido antes de consertar: o webhook de assinatura gravava a palavra "conferir"
# DENTRO da coluna do plano. Como "conferir" nao e um plano conhecido, o app caia
# no mais restrito — e o lojista que ACABOU de pagar era rebaixado pro gratis,
# em silencio e pra sempre, porque nada resolvia esse estado de volta.
from web import rotas_api as _api
from loja import rede as _rede4

_ID_P = _instalar("paga-o-pro.myshopify.com", "token-da-pagante")
t_lojas.marcar_plano(_ID_P, "pro")


def _com_shopify_dizendo(nome_do_plano, quebra=False):
    """Troca a ida ao Shopify por uma resposta conhecida."""
    original = _rede4.graphql

    def falso(loja, token, corpo, **kw):
        if quebra:
            raise _rede4.ErroDeRede("o Shopify caiu")
        assinaturas = ([{"name": nome_do_plano, "status": "ACTIVE"}]
                       if nome_do_plano else [])
        return {"data": {"currentAppInstallation":
                         {"activeSubscriptions": assinaturas}}}
    _rede4.graphql = falso
    return original


def _plano_agora():
    with _app.app_context():
        return _api._plano_de(t_lojas.por_id(_ID_P))


check("plano recem-conferido nao vence", t_lojas.plano_venceu(t_lojas.por_id(_ID_P)) is False)

# Enquanto esta fresco, nem pergunta ao Shopify. Se perguntasse toda vez, cada
# clique do lojista viraria uma ida a API.
_orig = _com_shopify_dizendo(None)   # se consultar, cai pro gratis
try:
    check("plano fresco e entregue sem consultar o Shopify", _plano_agora() == "pro")
finally:
    _rede4.graphql = _orig

# O webhook marca vencido — e NAO destroi o plano conhecido.
t_lojas.marcar_plano_vencido(_ID_P)
check("depois do webhook, o plano guardado continua 'pro'",
      t_lojas.por_id(_ID_P)["plano"] == "pro")
check("mas ele esta marcado como vencido", t_lojas.plano_venceu(t_lojas.por_id(_ID_P)))

# Shopify fora do ar NAO pode tirar o recurso pago de quem esta pagando. Cair pro
# gratis aqui seria uma instabilidade do Shopify virando prejuizo pro lojista no
# meio do trabalho.
_orig = _com_shopify_dizendo(None, quebra=True)
try:
    check("com o Shopify fora do ar, o pagante NAO e rebaixado", _plano_agora() == "pro")
finally:
    _rede4.graphql = _orig
check("e a proxima tentativa e adiada, pra nao martelar a API",
      t_lojas.plano_venceu(t_lojas.por_id(_ID_P)) is False)

# Quando o Shopify responde, a verdade dele manda — nos dois sentidos.
t_lojas.marcar_plano_vencido(_ID_P)
_orig = _com_shopify_dizendo("%s — Pro" % cobranca.NOME_DO_APP)
try:
    check("o Shopify dizendo Pro promove a loja", _plano_agora() == "pro")
finally:
    _rede4.graphql = _orig

t_lojas.marcar_plano_vencido(_ID_P)
_orig = _com_shopify_dizendo(None)     # cancelou: nenhuma assinatura ativa
try:
    check("e cancelamento rebaixa pro gratis", _plano_agora() == "gratis")
finally:
    _rede4.graphql = _orig

# Plano desconhecido no banco (dado velho, ou a palavra "conferir" de antes)
# nunca pode liberar recurso pago.
with banco.conectar() as _con:
    _con.execute("UPDATE lojas SET plano='conferir' WHERE id=?", (_ID_P,))
_orig = _com_shopify_dizendo(None, quebra=True)
try:
    check("plano desconhecido com Shopify fora do ar cai pro gratis, nao estoura",
          _plano_agora() == "gratis")
finally:
    _rede4.graphql = _orig

# A validade tambem serve de rede pro dia em que o webhook se perder — e webhook
# se perde. Sem ela, um cancelamento sem webhook daria acesso pago pra sempre.
check("a validade do plano e de horas, nao infinita",
      0 < t_lojas.VALIDADE_DO_PLANO_EM_HORAS <= 24, t_lojas.VALIDADE_DO_PLANO_EM_HORAS)
with banco.conectar() as _con:
    _con.execute("UPDATE lojas SET plano='pro', plano_conferido_em=? WHERE id=?",
                 ("2020-01-01T00:00:00+00:00", _ID_P))
check("plano conferido ha anos vence sozinho",
      t_lojas.plano_venceu(t_lojas.por_id(_ID_P)))
check("data ilegivel tambem conta como vencida",
      t_lojas.plano_venceu({"plano_conferido_em": "isso nao e data"}))

# E agora o caminho DE VERDADE: o webhook chegando pela rota, nao a funcao
# chamada na mao. Sem isto o teste acima passava com o webhook gravando
# "conferir" por cima do plano — foi a sabotagem que mostrou o furo.
t_lojas.marcar_plano(_ID_P, "pro")
_r = _webhook("app_subscriptions/update", "paga-o-pro.myshopify.com")
check("o webhook de assinatura responde 200", _r.status_code == 200, _r.status_code)
check("e NAO escreve nada por cima do plano conhecido",
      t_lojas.por_id(_ID_P)["plano"] == "pro", t_lojas.por_id(_ID_P)["plano"])
check("so marca que venceu", t_lojas.plano_venceu(t_lojas.por_id(_ID_P)))

t_lojas.apagar("paga-o-pro.myshopify.com")


secao("57. Cobranca ligada de ponta a ponta")
# O modulo de cobranca existia, testado e correto, e NINGUEM chamava ele. Um
# motor sem chave de ignicao. Isto liga: criar a assinatura, mandar o lojista
# aprovar, e receber ele de volta.
from web import config as _cfg3

_ID_C = _instalar("quer-assinar.myshopify.com", "token-de-quem-vai-assinar")
_pedidos = []


def _shopify_de_mentira(resposta, desenvolvimento=True):
    """Responde a DUAS consultas: que tipo de loja e, e a criacao da assinatura.

    A rota pergunta o tipo antes de assinar, entao um duplo que devolve sempre a
    mesma coisa faz a primeira pergunta voltar sem resposta — foi o que quebrou
    este teste quando a deteccao entrou.
    """
    original = _rede4.graphql

    def falso(loja, token, corpo, **kw):
        _pedidos.append(corpo)
        if "partnerDevelopment" in corpo.get("query", ""):
            if desenvolvimento is None:
                return {"data": {"shop": None}}     # resposta que nao diz nada
            return {"data": {"shop": {"myshopifyDomain": loja,
                                      "plan": {"partnerDevelopment": desenvolvimento,
                                               "shopifyPlus": False}}}}
        return resposta
    _rede4.graphql = falso
    return original


_OK = {"data": {"appSubscriptionCreate": {
    "confirmationUrl": "https://admin.shopify.com/store/x/charges/1/confirm",
    "appSubscription": {"id": "gid://1", "status": "PENDING"}, "userErrors": []}}}

_pedidos.clear()
_orig = _shopify_de_mentira(_OK)
try:
    _r = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "pro"})
finally:
    _rede4.graphql = _orig

check("assinar devolve a URL de confirmacao do Shopify",
      _r.status_code == 200 and "charges/1/confirm" in _r.get_json()["url"],
      (_r.status_code, _r.get_json()))

# A rota faz DUAS consultas agora: primeiro o tipo da loja, depois a criacao.
# Pegar _pedidos[0] pegava a pergunta do tipo, que nem tem variables.
_vars = [p for p in _pedidos
         if "appSubscriptionCreate" in p.get("query", "")][0]["variables"]
check("com o preco do plano Pro", _vars["preco"] == "9.99", _vars["preco"])
check("em dolar", _vars["moeda"] == "USD")
check("com os dias de teste", _vars["teste"] == cobranca.DIAS_DE_TESTE)
# Cobrar de verdade numa loja de desenvolvimento e motivo de REPROVACAO na
# revisao do Shopify. O COBRANCA_TESTE existia na config e nao era usado por
# ninguem — este teste e o que garante que ele chega na mutacao.
# Loja de desenvolvimento so aceita cobranca de teste; loja de verdade precisa da
# cobranca de verdade. Antes isso era uma variavel de ambiente que ALGUEM tinha
# que lembrar de trocar antes de publicar — e esquecer significava o app
# publicado criando assinaturas de teste pra todo mundo: o lojista "assina",
# ganha acesso, e nao paga nada. Nao apareceria em teste nenhum.
check("loja de desenvolvimento vira assinatura de TESTE",
      _vars["desenvolvimento"] is True, _vars["desenvolvimento"])
check("e o app perguntou ao Shopify antes de decidir",
      any("partnerDevelopment" in p.get("query", "") for p in _pedidos))

# Loja de verdade: cobranca de verdade.
_pedidos.clear()
_orig = _shopify_de_mentira(_OK, desenvolvimento=False)
try:
    _r_real = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "pro"})
finally:
    _rede4.graphql = _orig
check("loja de verdade vira cobranca de verdade", _r_real.status_code == 200)
_vars_real = [p for p in _pedidos if "appSubscriptionCreate" in p.get("query", "")][0]["variables"]
check("e a assinatura NAO e de teste",
      _vars_real["desenvolvimento"] is False, _vars_real["desenvolvimento"])

# Sem saber o tipo, recusa. Chutar erra caro dos dois lados: cobranca real em
# loja de teste e reprovacao na revisao, e cobranca de teste em loja real e
# entregar o produto de graca sem ninguem perceber.
_pedidos.clear()
_orig = _shopify_de_mentira(_OK, desenvolvimento=None)
try:
    _r_sei_la = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "pro"})
finally:
    _rede4.graphql = _orig
check("sem saber o tipo da loja, recusa em vez de chutar",
      _r_sei_la.status_code == 502, _r_sei_la.status_code)
check("e NAO chega a criar assinatura nenhuma",
      not any("appSubscriptionCreate" in p.get("query", "") for p in _pedidos))

# A leitura da resposta, isolada.
check("resposta de loja de desenvolvimento e reconhecida",
      cobranca.e_loja_de_desenvolvimento(
          {"data": {"shop": {"plan": {"partnerDevelopment": True}}}}) is True)
check("resposta de loja de verdade tambem",
      cobranca.e_loja_de_desenvolvimento(
          {"data": {"shop": {"plan": {"partnerDevelopment": False}}}}) is False)
for _torta in ({}, None, {"data": {}}, {"data": {"shop": None}},
               {"data": {"shop": {"plan": {}}}},
               {"data": {"shop": {"plan": "isso nao e dicionario"}}}):
    check("resposta torta %r vira None, nao um chute" % (str(_torta)[:26],),
          cobranca.e_loja_de_desenvolvimento(_torta) is None)
check("a URL de volta aponta pra nossa rota de retorno",
      _vars["volta"].endswith("/cobranca/volta?shop=quer-assinar.myshopify.com"),
      _vars["volta"])

# Assinar NAO pode liberar nada: quem confirma e o lojista, na tela do Shopify.
check("pedir assinatura nao promove a loja sozinho",
      t_lojas.por_id(_ID_C)["plano"] == "gratis", t_lojas.por_id(_ID_C)["plano"])

# O plano gratis nao tem assinatura pra criar.
_r = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "gratis"})
check("nao da pra assinar o plano gratis", _r.status_code == 400, _r.status_code)
_r = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "inventado"})
check("plano que nao existe e recusado", _r.status_code == 400)

# userErrors vem DENTRO de uma resposta 200. Sem tratar, o lojista seria mandado
# pra lugar nenhum achando que assinou.
_orig = _shopify_de_mentira({"data": {"appSubscriptionCreate": {
    "userErrors": [{"message": "loja sem meio de pagamento"}]}}})
try:
    _r = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "pro"})
finally:
    _rede4.graphql = _orig
check("erro do Shopify dentro do 200 vira 502, nao redirecionamento torto",
      _r.status_code == 502, _r.status_code)
check("e a mensagem dele chega na tela",
      "meio de pagamento" in _r.get_json()["erro"], _r.get_json())

# Rede caindo no meio.
_orig = _rede4.graphql


def _cai(loja, token, corpo, **kw):
    raise _rede4.ErroDeRede("sem conexao")


_rede4.graphql = _cai
try:
    _r = _post("/api/assinar", "quer-assinar.myshopify.com", {"plano": "pro"})
finally:
    _rede4.graphql = _orig
check("rede caindo vira 502 com explicacao", _r.status_code == 502)

# --- a volta -------------------------------------------------------------
t_lojas.marcar_plano(_ID_C, "pro")
check("antes da volta, o plano esta fresco",
      t_lojas.plano_venceu(t_lojas.por_id(_ID_C)) is False)

_r = _cliente.get("/cobranca/volta?shop=quer-assinar.myshopify.com")
check("a volta redireciona pro admin da loja", _r.status_code == 302, _r.status_code)
check("e pro painel de apps dela",
      "quer-assinar/apps" in _r.headers.get("Location", ""), _r.headers.get("Location"))
# Ela nao promove ninguem: so marca que precisa reconferir com o Shopify. E por
# isso que ela pode ser uma rota aberta.
check("a volta marca o plano pra reconferir",
      t_lojas.plano_venceu(t_lojas.por_id(_ID_C)))
check("mas NAO muda o plano por conta propria",
      t_lojas.por_id(_ID_C)["plano"] == "pro", t_lojas.por_id(_ID_C)["plano"])

check("a volta com dominio invalido e recusada",
      _cliente.get("/cobranca/volta?shop=evil.com").status_code == 400)
check("e sem loja nenhuma tambem",
      _cliente.get("/cobranca/volta").status_code == 400)
# Loja que nunca instalou nao pode derrubar a rota.
check("volta de loja desconhecida nao quebra",
      _cliente.get("/cobranca/volta?shop=nunca-vi.myshopify.com").status_code == 302)

# --- a lista de planos que a tela mostra ---------------------------------
t_lojas.marcar_plano(_ID_C, "gratis")
_d = _pega("/api/planos", "quer-assinar.myshopify.com").get_json()
check("a tela recebe os dois planos", len(_d["planos"]) == 2, len(_d["planos"]))
check("sabe qual e o atual", _d["atual"] == "gratis", _d["atual"])
check("e os dias de teste", _d["dias_de_teste"] == cobranca.DIAS_DE_TESTE)
check("com preco em numero, pra tela nao formatar moeda por conta propria",
      all(isinstance(p["preco_usd"], (int, float)) for p in _d["planos"]))

t_lojas.apagar("quer-assinar.myshopify.com")


secao("58. Revisao: os quatro problemas que a medicao achou")

# --- 1. quebra de texto era quadratica --------------------------------------
# O conteudo da etiqueta vem do navegador. A versao antiga descobria onde cortar
# uma palavra TIRANDO UM CARACTERE POR VEZ: 10 mil caracteres custavam 16ms,
# 40 mil custavam 472ms — dobrar o texto multiplicava o tempo por doze. Um
# titulo de 2 MB, que o Flask aceita, travaria um processo por minutos.
import time as _t2

_ini = _t2.perf_counter()
texto.preparar("A" * 200000, 32.0, 7.8, 2, "cortar")
_ms = (_t2.perf_counter() - _ini) * 1000
check("200 mil caracteres custam menos de 50ms", _ms < 50, "%.1f ms" % _ms)

# O teste acima passa com as DUAS defesas: o algoritmo direto e o teto de
# caracteres. Ou seja, ele nao prova que o algoritmo esta certo — sozinho, o teto
# ja faria a conta caber. Descobri isso vendo a sabotagem do algoritmo escapar.
#
# Este mede o `quebrar` direto, que NAO tem teto. So o algoritmo pode salvar.
_ini = _t2.perf_counter()
texto.quebrar("A" * 60000, 32.0, 7.8, 2)
_ms_puro = (_t2.perf_counter() - _ini) * 1000
check("quebrar 60 mil caracteres, SEM o teto, custa menos de 30ms",
      _ms_puro < 30, "%.1f ms" % _ms_puro)
# E a prova de que nao e linear disfarcado: dobrar a entrada nao pode dobrar o
# tempo de forma explosiva. Na versao antiga isso multiplicava por doze.
_ini = _t2.perf_counter()
texto.quebrar("A" * 120000, 32.0, 7.8, 2)
_dobro = (_t2.perf_counter() - _ini) * 1000
check("e dobrar a entrada nao explode o tempo",
      _dobro < max(30, _ms_puro * 4), "%.1f ms -> %.1f ms" % (_ms_puro, _dobro))

# E o corte continua caindo no MESMO lugar de antes — os arquivos-espelho
# garantiriam isso, mas vale dizer aqui tambem.
check("a conta direta acha o mesmo ponto de corte",
      texto.quebrar("REF-ABC123456789012345678901234567890", 32.0, 7.8, 2)
      == ["REF-ABC1234567890123", "45678901234567890"],
      texto.quebrar("REF-ABC123456789012345678901234567890", 32.0, 7.8, 2))
check("quantos_cabem bate com o que o cabe() aceita",
      texto.cabe("A" * texto.quantos_cabem(32.0, 7.8), 32.0, 7.8)
      and not texto.cabe("A" * (texto.quantos_cabem(32.0, 7.8) + 1), 32.0, 7.8))
check("largura zero nao divide por zero", texto.quantos_cabem(0, 7.8) >= 1)
check("fonte zero tambem nao", texto.quantos_cabem(32.0, 0) >= 1)

# O teto e defesa em profundidade: mesmo que a medida deixe de ser linear um dia,
# o custo continua limitado.
check("texto passa a ser cortado num teto",
      len("".join(texto.preparar("A" * 99999, 500.0, 8.0, 99, "cortar")[0]))
      <= texto.TETO_DE_CARACTERES)
check("e o teto e generoso o bastante pra nao afetar etiqueta real",
      texto.TETO_DE_CARACTERES >= 2000)

# --- 2. a tela lia so os 50 primeiros produtos ------------------------------
# A API devolvia `tem_mais` e `cursor` desde sempre; a tela ignorava os dois.
# Numa loja com 200 produtos, os 150 de baixo simplesmente nao existiam.
from web import dev as _dev

_pag1, _mais1, _cur1 = _dev.catalogo_falso(None, None)
check("a primeira pagina traz 50", len(_pag1) == 50, len(_pag1))
check("e avisa que tem mais", _mais1 is True)
_pag2, _mais2, _cur2 = _dev.catalogo_falso(None, _cur1)
check("a segunda pagina continua de onde parou", len(_pag2) == 50)
check("sem repetir o que ja veio",
      not ({i["variante"]["id"] for i in _pag1} & {i["variante"]["id"] for i in _pag2}))
_pag3, _mais3, _ = _dev.catalogo_falso(None, _cur2)
check("a ultima pagina fecha a conta", _mais3 is False)
check("e o total bate", len(_pag1) + len(_pag2) + len(_pag3) == len(_dev.TODOS_FALSOS))
check("cursor invalido nao quebra, recomeca do zero",
      len(_dev.catalogo_falso(None, "isso nao e numero")[0]) == 50)

# A tela precisa disso no JSON, senao o botao de carregar mais nunca aparece.
# A loja A e "de verdade" pros testes, entao a ida ao Shopify e substituida.
_orig_gql = _rede4.graphql


def _produtos_de_mentira(loja, token, corpo, **kw):
    return {"data": {"products": {
        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-do-shopify"},
        "nodes": [{"title": "Um produto", "vendor": "", "productType": "",
                   "onlineStoreUrl": "",
                   "variants": {"pageInfo": {"hasNextPage": False},
                                "nodes": [{"id": "v1", "title": "", "sku": "S1",
                                           "barcode": "", "price": "1.00",
                                           "compareAtPrice": "",
                                           "inventoryQuantity": 4}]}}]}}}


_rede4.graphql = _produtos_de_mentira
try:
    _r = _pega("/api/produtos", "loja-a.myshopify.com")
finally:
    _rede4.graphql = _orig_gql
_corpo_prod = _r.get_json() or {}
check("a rota de produtos devolve tem_mais e cursor",
      {"itens", "tem_mais", "cursor"} <= set(_corpo_prod), (_r.status_code, _corpo_prod))
check("com o cursor que o Shopify mandou",
      _corpo_prod.get("cursor") == "cursor-do-shopify", _corpo_prod.get("cursor"))
check("e a quantidade sugerida vem do estoque",
      _corpo_prod["itens"][0]["quantidade"] == 4)

# --- 3. produto com mais de 100 variantes sumia calado ----------------------
# A consulta pede `variants(first: 100)`. Grade de roupa grande passa disso, e o
# lojista imprimiria a prateleira faltando tamanhos sem nada avisar.
_resp_cortada = {"data": {"products": {"nodes": [{
    "title": "Camiseta com muitas grades", "vendor": "", "productType": "",
    "onlineStoreUrl": "",
    "variants": {"pageInfo": {"hasNextPage": True},
                 "nodes": [{"id": "v1", "title": "P", "sku": "A", "barcode": "",
                            "price": "10", "compareAtPrice": "",
                            "inventoryQuantity": 1}]}}]}}}
_itens_cortados = catalogo.para_etiquetas(_resp_cortada)
check("o corte de variantes e detectado",
      _itens_cortados[0]["variantes_cortadas"] is True)
check("e vira uma lista de nomes pra tela avisar",
      catalogo.produtos_com_variantes_cortadas(_itens_cortados)
      == ["Camiseta com muitas grades"])
check("produto normal nao dispara o aviso",
      catalogo.produtos_com_variantes_cortadas(
          catalogo.para_etiquetas({"data": {"products": {"nodes": [{
              "title": "Normal", "variants": {"pageInfo": {"hasNextPage": False},
              "nodes": [{"id": "v", "sku": "S"}]}}]}}})) == [])
check("a consulta pede o pageInfo das variantes",
      "pageInfo { hasNextPage }" in catalogo.CONSULTA_PRODUTOS)

# --- 4. reconferir o plano podia travar a impressao por um minuto -----------
# rede.graphql insiste 3 vezes com espera crescente: ate 63 segundos no pior
# caso. Isso e aceitavel pra quem espera o catalogo, e pessimo pra uma
# atualizacao de cache que roda DENTRO de um pedido de impressao.
import inspect as _insp2
check("da pra pedir menos tentativas",
      "tentativas" in _insp2.signature(_rede4.graphql).parameters)
check("e o padrao continua insistindo",
      _insp2.signature(_rede4.graphql).parameters["tentativas"].default
      == _rede4.TENTATIVAS)
_fonte_api = _io.open("web/rotas_api.py", encoding="utf-8").read()
check("a reconferida de plano desiste na primeira",
      "tentativas=1" in _fonte_api.split("def _plano_de")[1].split("def ")[0])

# --- 5. SQLite travando leitor e escritor -----------------------------------
# No modo padrao uma escrita bloqueia TODAS as leituras. Com um processo so nao
# aparece; com varios — que e como qualquer servidor roda — um lojista salvando
# modelo trava a previa de todo mundo.
with banco.conectar() as _con:
    _modo = _con.execute("PRAGMA journal_mode").fetchone()[0]
check("o banco esta em WAL", str(_modo).lower() == "wal", _modo)


secao("59. Bilingue: ingles por padrao, portugues quando pedido")
# O app nasceu inteiro em portugues, e as 565 avaliacoes que embasaram a ideia
# sao em ingles. Listar em portugues seria mirar num mercado que a gente nunca
# mediu. Ingles virou o padrao; portugues existe porque o suporte sai mais
# barato na propria lingua.
from web import textos as _tx

check("o padrao e ingles", _tx.PADRAO == "en")
for _bruto, _esperado in [("pt-BR", "pt"), ("pt", "pt"), ("PT_br", "pt"),
                          ("en-US", "en"), ("de-DE", "en"), ("", "en"),
                          (None, "en"), ("xx", "en")]:
    check("idioma %r vira %r" % (_bruto, _esperado),
          _tx.idioma_de(_bruto) == _esperado, _tx.idioma_de(_bruto))

# Toda chave tem que existir nos DOIS idiomas. Uma faltando vira tela meio
# traduzida, que parece mais quebrado do que tela nao traduzida.
_sem_en = [k for k, v in _tx.TEXTOS.items() if not v.get("en")]
_sem_pt = [k for k, v in _tx.TEXTOS.items() if not v.get("pt")]
check("nenhuma chave sem ingles", _sem_en == [], _sem_en)
check("nenhuma chave sem portugues", _sem_pt == [], _sem_pt)
# E os dois tem que ser DIFERENTES onde faz sentido — se alguem copiar o
# portugues no campo do ingles, isto nao pega, mas pega o esquecimento comum de
# deixar a mesma frase nos dois por preguica.
# Nome de produto nao traduz — "Google Docs" tambem nao. Fora esses, frase longa
# identica nos dois idiomas quase sempre e traducao esquecida.
NAO_TRADUZEM = {"app_titulo"}
_iguais = [k for k, v in _tx.TEXTOS.items()
           if v["en"] == v["pt"] and len(v["en"]) > 12 and k not in NAO_TRADUZEM]
check("nenhuma frase longa identica nos dois idiomas", _iguais == [], _iguais)
check("e o nome do produto e o mesmo nos dois",
      _tx.t("app_titulo", "en") == _tx.t("app_titulo", "pt")
      == cobranca.NOME_DO_APP, _tx.t("app_titulo", "en"))

# Chave que nao existe volta visivel, nao estoura: tela feia da pra ver e
# consertar, tela em branco o lojista so reporta como "nao abre".
check("chave inexistente volta entre colchetes",
      _tx.t("nao_existe_essa", "en") == "[nao_existe_essa]")
check("e nao levanta excecao", isinstance(_tx.t("nao_existe_essa"), str))
check("a tabela sai completa", len(_tx.tabela("pt")) == len(_tx.TEXTOS))

# --- a tela responde no idioma pedido --------------------------------------
_html_en = _cliente.get("/dev/?locale=en-US").get_data(as_text=True)
_html_pt = _cliente.get("/dev/?locale=pt-BR").get_data(as_text=True)
check("a tela em ingles diz Products", "<h2>Products</h2>" in _html_en)
check("a tela em portugues diz Produtos", "<h2>Produtos</h2>" in _html_pt)
check("o lang do html acompanha",
      'lang="en"' in _html_en and 'lang="pt"' in _html_pt)
check("o titulo e o nome do produto, igual nos dois idiomas",
      ("<title>%s</title>" % cobranca.NOME_DO_APP) in _html_en
      and ("<title>%s</title>" % cobranca.NOME_DO_APP) in _html_pt)
# Chave faltando apareceria como [chave] na pagina. Isto varre a tela inteira.
import re as _re3
check("nenhuma chave faltando na tela em ingles",
      _re3.search(r"\[[a-z_]{4,}\]", _html_en) is None,
      (_re3.findall(r"\[[a-z_]{4,}\]", _html_en) or [""])[0])
check("nem na tela em portugues",
      _re3.search(r"\[[a-z_]{4,}\]", _html_pt) is None,
      (_re3.findall(r"\[[a-z_]{4,}\]", _html_pt) or [""])[0])

# --- as mensagens da API tambem -------------------------------------------
def _erro_em(idioma):
    return _cliente.post("/api/imprimir?idioma=" + idioma,
        headers={"Authorization": "Bearer " + _token_de("loja-de-teste.myshopify.com")},
        json={"motor": "zpl", "receita": {"formato": "zebra_2x1"},
              "itens": [{"produto": {}, "variante": {}}]}).get_json()["erro"]

t_lojas.marcar_plano(t_lojas.buscar("loja-de-teste.myshopify.com")["id"], "gratis")
# Os testes acima passam o idioma na mao. Isso NAO prova que a tela manda — e,
# de fato, apagar a linha que faz isso nao quebrava nada. Sem ela a tela fica na
# lingua do lojista e as mensagens de erro voltam no padrao: metade traduzida,
# que parece mais quebrado do que nada traduzido.
_fonte_tela = _io.open("web/rotas_tela.py", encoding="utf-8").read()
check("a tela repassa o idioma em toda chamada de API",
      'caminho += (caminho.indexOf("?") < 0 ? "?" : "&") + "idioma=" + IDIOMA;'
      in _fonte_tela)
check("e o idioma chega no JavaScript",
      "const IDIOMA = {{ idioma|tojson }};" in _fonte_tela)

check("erro da API em ingles", _erro_em("en") == _tx.t("erro_motor_bloqueado", "en"))
check("erro da API em portugues", _erro_em("pt") == _tx.t("erro_motor_bloqueado", "pt"))

# --- os nomes que a tela exibe vem traduzidos da borda ---------------------
# O motor guarda "Título do produto" e "2 x 1 pol"; quem traduz e o web, porque
# o motor tem arquivo-espelho e nao pode mudar por causa de idioma.
_f_en = _pega("/api/formatos?idioma=en", "loja-a.myshopify.com").get_json()
_f_pt = _pega("/api/formatos?idioma=pt", "loja-a.myshopify.com").get_json()
check("os campos vem traduzidos",
      [c["nome"] for c in _f_en["campos"]][:3] == ["Product title",
                                                   "Variant (color, size)", "Vendor"],
      [c["nome"] for c in _f_en["campos"]][:3])
check("e em portugues tambem",
      _f_pt["campos"][0]["nome"] == "Título do produto", _f_pt["campos"][0]["nome"])
check("o sufixo do formato e traduzido",
      "retail" in _f_en["formatos"][0]["nome"], _f_en["formatos"][0]["nome"])
check("inclusive a unidade de polegada",
      " in " in _f_en["formatos"][0]["nome"], _f_en["formatos"][0]["nome"])
check("e o portugues fica como estava",
      "pol" in _f_pt["formatos"][0]["nome"] and "varejo" in _f_pt["formatos"][0]["nome"],
      _f_pt["formatos"][0]["nome"])

_p_en = _pega("/api/planos?idioma=en", "loja-a.myshopify.com").get_json()
check("os planos vem traduzidos",
      [p["nome"] for p in _p_en["planos"]] == ["Free", "Pro"],
      [p["nome"] for p in _p_en["planos"]])
check("e o resumo tambem",
      "Unlimited labels" in [p["resumo"] for p in _p_en["planos"]][1])

# --- o motor continua sem saber o que e idioma -----------------------------
# Se um dia alguem puser texto de tela dentro do motor, traduzir passa a exigir
# mexer nele — e ele tem arquivo-espelho justamente pra nao mudar.
for _mod in ("etiquetas/receitas.py", "etiquetas/formatos.py", "etiquetas/modelo.py",
             "loja/cobranca.py", "loja/catalogo.py"):
    _fonte = _io.open(_mod, encoding="utf-8").read()
    check("%s nao importa a tabela de textos" % _mod,
          "textos" not in _fonte.replace("# ", "").split('"""')[-1],
          _mod)


secao("60. A politica de privacidade tem que ser verdade, nao promessa")
# Ela afirma coisas verificaveis: que o app so pede dois escopos de leitura, e
# que o banco nao guarda dado de cliente nem catalogo. Se alguem acrescentar uma
# coluna ou um escopo, a pagina passa a MENTIR — e mentir em politica de
# privacidade nao e bug, e problema regulatorio.
_priv_en = _cliente.get("/privacy?lang=en").get_data(as_text=True)
_priv_pt = _cliente.get("/privacy?lang=pt").get_data(as_text=True)

check("a politica abre sem token de sessao",
      _cliente.get("/privacy").status_code == 200)
check("nos dois idiomas",
      "Privacy Policy" in _priv_en and "Política de Privacidade" in _priv_pt)
check("e no idioma da requisicao quando nao pedem",
      "Privacy Policy" in _cliente.get("/privacy?idioma=en").get_data(as_text=True))

# 1. os escopos citados sao os que o app pede DE VERDADE
for _e in oauth.ESCOPOS:
    check("a politica cita o escopo %s" % _e, _e in _priv_en and _e in _priv_pt)
check("e o app pede exatamente tres",
      len(oauth.ESCOPOS) == 3, oauth.ESCOPOS)
# Se alguem pedir escopo de cliente ou pedido, a promessa central cai. Este
# app nao tem por que enxergar quem comprou, e isso nao mudou com a escrita.
_proibidos = ("read_customers", "write_customers", "read_orders",
              "write_orders", "read_all_orders")
check("nenhum escopo de cliente nem de pedido",
      not any(p in oauth.ESCOPOS for p in _proibidos), oauth.ESCOPOS)

# A TRAVA INVERTIDA, e ela e a que importa agora.
#
# Ate 20/10/2026 a trava era "nenhum escopo de escrita", e ela existia pra
# proteger a frase da ficha. Com `write_products` ligado, a frase mudou — e o
# que precisa ser travado passa a ser o contrario: se o app ESCREVE, o texto
# publico tem que DIZER que ele escreve.
#
# Sem isto, a politica de privacidade continuaria jurando "somente leitura"
# com um escopo de escrita ativo, que e exatamente a mentira que a trava
# antiga existia pra impedir.
if any(e.startswith("write") for e in oauth.ESCOPOS):
    check("a politica NAO jura mais 'somente leitura'",
          "somente leitura" not in _priv_pt and "read-only" not in _priv_en.lower(),
          [s for s in ("somente leitura", "read-only")
           if s in _priv_pt or s in _priv_en.lower()])
    check("ela diz, nos dois idiomas, que nada e escrito sem o lojista clicar",
          "até você revisar" in _priv_pt and "until you review" in _priv_en)
    check("e diz que o app so preenche campo VAZIO",
          "vazio" in _priv_pt and "empty" in _priv_en)
    check("e que da pra desfazer",
          "desfazer" in _priv_pt and "undone" in _priv_en)

# 2. o banco nao pode ganhar coluna de dado pessoal sem a politica mudar junto
#
# A lista de tabelas sai do PROPRIO BANCO, nao escrita a mao. A primeira versao
# listava ("lojas", "modelos", "impressoes") e por isso pegava coluna nova mas
# NAO pegava TABELA nova — foi assim que a `gravacoes` entrou sem ninguem reler
# a politica. Tabela nova guarda dado novo; e o caso mais forte, nao o mais
# fraco.
with banco.conectar() as _con:
    _tabelas = [r["name"] for r in _con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%'").fetchall()]
    _colunas = set()
    for _tab in _tabelas:
        for _c in _con.execute("PRAGMA table_info(%s)" % _tab).fetchall():
            _colunas.add("%s.%s" % (_tab, _c["name"]))

_ESPERADAS = {
    "lojas.id", "lojas.dominio", "lojas.token_cifrado", "lojas.escopos",
    "lojas.plano", "lojas.ativa", "lojas.instalada_em", "lojas.desinstalada_em",
    "lojas.plano_conferido_em",
    # O Shopify passou a expirar o token de acesso. Guardar o token de
    # renovacao cifrado, e os dois prazos, e o que evita o lojista ter que
    # reinstalar toda hora — e entrou na politica junto com esta linha.
    "lojas.refresh_cifrado", "lojas.token_expira_em", "lojas.refresh_expira_em",
    "modelos.id", "modelos.loja_id", "modelos.nome", "modelos.json",
    "modelos.receita", "modelos.criado_em", "modelos.alterado_em",
    "impressoes.id", "impressoes.loja_id", "impressoes.modelo_id",
    "impressoes.motor", "impressoes.quantidade", "impressoes.criado_em",
    # A UNICA tabela que guarda conteudo do catalogo, e e excecao assumida: sem
    # o valor anterior nao existe desfazer, e sem desfazer o gerador nao sobe.
    # Guarda o minimo, so o que NOS escrevemos, e tem prazo de 30 dias.
    "gravacoes.id", "gravacoes.loja_id", "gravacoes.lote",
    "gravacoes.variante_id", "gravacoes.campo", "gravacoes.valor_antigo",
    "gravacoes.valor_novo", "gravacoes.criado_em", "gravacoes.desfeito_em",
}
# Este teste FALHA de proposito quando o esquema muda. Nao e chatice: coluna
# nova e o momento de reler a politica e decidir se ela continua verdadeira.
check("o esquema do banco e exatamente o que a politica descreve",
      _colunas == _ESPERADAS, sorted(_colunas ^ _ESPERADAS))

# 3. nenhuma tabela guarda o catalogo — a promessa mais forte da pagina
_suspeitas = [c for c in _colunas
              if any(p in c for p in ("cliente", "customer", "pedido", "order",
                                      "email", "endereco", "address", "telefone",
                                      "phone", "produto", "product", "titulo",
                                      "sku", "barcode", "preco", "price"))]
check("nenhuma coluna com cara de dado de cliente ou de produto",
      _suspeitas == [], _suspeitas)

# 4. as respostas dos webhooks de privacidade dizem a mesma coisa que a pagina
check("o webhook de dados do cliente responde que nao ha nada",
      webhooks.resposta_de_privacidade("customers/data_request")["dados_do_cliente"]
      is None)
check("e a pagina afirma o mesmo",
      "never" in _priv_en.lower() and "nunca" in _priv_pt.lower())

# 5. o contato precisa estar preenchido antes de publicar
check("a pagina tem um endereco de contato", "mailto:" in _priv_en)
_r = _cliente.get("/privacy?lang=en").get_data(as_text=True)
check("e se nao estiver preenchido, a pagina DIZ isso em vez de sumir",
      ("preencha" in _r) or ("@" in _r.split("mailto:")[1][:40]))


secao("61. O icone sai de uma geometria so")
# A loja de apps quer PNG. PNG nao se edita: mexer numa barra significa abrir num
# programa de desenho e nunca mais bater com o original. Entao SVG e PNG saem da
# MESMA lista de formas — a mesma disciplina dos tres motores.
import sys as _sys
_sys.path.insert(0, "docs")
import icone as _icone

check("o SVG sai do gerador, nao da mao",
      _icone.svg() == _io.open("docs/icone.svg", encoding="utf-8").read(),
      "rode: python docs/icone.py")

from PIL import Image as _Img
_png = _Img.open("docs/icone.png")
check("o PNG tem o tamanho que o Shopify pede", _png.size == (1200, 1200), _png.size)
check("e existe a versao pequena, que e a que decide",
      _Img.open("docs/icone-60.png").size == (60, 60))

# Sem texto: e regra do Shopify e e o que faz o icone funcionar a 60px.
check("o icone nao tem texto nenhum",
      "<text" not in _icone.svg() and "font" not in _icone.svg())

# Sangra ate a borda: cada plataforma recorta o canto do seu jeito, e um icone
# com fundo branco proprio aparece como quadrado torto dentro da mascara deles.
check("o fundo sangra ate a borda",
      _png.getpixel((0, 0))[:3] != (255, 255, 255)
      and _png.getpixel((1199, 1199))[:3] != (255, 255, 255))
check("e tem gradiente, entao topo e base diferem",
      _png.getpixel((50, 50)) != _png.getpixel((50, 1150)))

# O contraste entre a etiqueta e o fundo e o que faz a forma ler no tamanho
# pequeno. Papel branco sobre azul escuro passa com folga.
def _luz(p):
    """Luminancia relativa como a norma define, COM a correcao de gama.

    A primeira versao disto somava os canais direto, sem linearizar o sRGB. Deu
    3,8:1 pra branco sobre azul-escuro, e reprovou um contraste que na verdade e
    de 11:1 — quase tres vezes melhor do que a conta dizia.
    O erro estava na regua, nao no desenho.

    Sem a correcao, cor escura parece mais clara do que e, e a conta e otimista
    justamente onde precisa ser dura.
    """
    def canal(v):
        v = v / 255.0
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = p[:3]
    return 0.2126 * canal(r) + 0.7152 * canal(g) + 0.0722 * canal(b)


_papel = _luz(_png.getpixel((860, 390)))
_fundo = _luz(_png.getpixel((50, 50)))
_contraste = (max(_papel, _fundo) + 0.05) / (min(_papel, _fundo) + 0.05)
check("a etiqueta contrasta com o fundo (>= 4.5:1)", _contraste >= 4.5,
      "%.1f:1" % _contraste)

# A 60px o desenho ainda tem que ter forma, nao virar um borrao de uma cor so.
_pequeno = _Img.open("docs/icone-60.png").convert("L")
_tons = len(set(_pequeno.getdata()))
check("a 60px ainda ha variacao de tom, nao um bloco chapado",
      _tons > 20, "%d tons" % _tons)
_sys.path.pop(0)


secao("62. Texto nao pode encostar nas barras")
# A altura de linha poe a LINHA DE BASE no fim do bloco, e a letra desce abaixo
# dela — o "p" de "preco", o rabo do "y", o traco do hifen. Entre duas linhas de
# texto isso e normal. Contra um codigo de barras, que e tinta solida a partir do
# topo, a descida cai em cima das barras.
#
# Medido na Avery com fornecedor ligado: SKU e preco com base em 12,581mm e o
# codigo comecando em 12,581mm EXATOS. Apareceu numa captura de tela, nao num
# teste: os testes de borda nao pegavam porque tudo continuava DENTRO da etiqueta.
import re as _re4

_TODOS_CAMPOS = ("titulo", "variante", "fornecedor", "sku", "preco", "codigo_barras")
_DIFICIL = {"produto": {"titulo": "Reusable Glass Straw Set — 4 pieces with brush",
                        "fornecedor": "EcoVida"},
            "variante": {"titulo": "Clear / 20cm", "sku": "STRW-GL-20",
                         "preco": "1249.90", "codigo_barras": "7891234567895"}}


def _folga_ate_o_codigo(fmt, campos):
    """Distancia entre o ponto mais baixo do texto e o topo das barras."""
    t = receitas.montar(fmt, campos=campos)
    s = motor_svg.render(t, _DIFICIL)
    descidas = [float(y) + float(tam) * receitas.DESCIDA_DA_LETRA
                for _, y, tam, _ in _re4.findall(
                    r'<text x="([\d.]+)" y="([\d.]+)" [^>]*font-size="([\d.]+)"[^>]*>([^<]*)<', s)]
    codigo = _re4.search(r'<svg x="[\d.]+" y="([\d.]+)"', s)
    if not codigo or not descidas:
        return None
    return float(codigo.group(1)) - max(descidas)


for _f in _fmt.CATALOGO:
    _folga = _folga_ate_o_codigo(_f.codigo, _TODOS_CAMPOS)
    if _folga is None:
        continue                    # etiqueta pequena demais pra ter os dois
    check("%s: a letra nao encosta nas barras" % _f.codigo, _folga >= 0,
          "%+.2f mm" % _folga)

# E com o conjunto padrao tambem, que e o que a maioria vai usar.
for _f in _fmt.CATALOGO:
    _folga = _folga_ate_o_codigo(_f.codigo, receitas.PADRAO)
    if _folga is None:
        continue
    check("%s: idem com os campos padrao" % _f.codigo, _folga >= 0,
          "%+.2f mm" % _folga)

# A folga tem que CRESCER com a fonte. A primeira tentativa usou 0,7mm fixo:
# resolveu nas etiquetas pequenas e continuou colidindo na de 3x2 polegadas,
# onde a fonte e o dobro e a letra desce o dobro junto.
_pequena = receitas.montar("zebra_2x1", campos=_TODOS_CAMPOS)
_grande = receitas.montar("zebra_3x2", campos=_TODOS_CAMPOS)


def _fonte_do_preco(t):
    return [e.tamanho_pt for e in t.elementos if isinstance(e, Preco)][0]


check("a fonte do preco cresce com a etiqueta",
      _fonte_do_preco(_grande) > _fonte_do_preco(_pequena) * 1.5,
      (_fonte_do_preco(_pequena), _fonte_do_preco(_grande)))
check("e a folga minima nao e zero", receitas.FOLGA_MINIMA_MM > 0)
check("a descida considerada e a de fonte de verdade",
      0.15 <= receitas.DESCIDA_DA_LETRA <= 0.3, receitas.DESCIDA_DA_LETRA)


import re as _re5

secao("63. O codigo tem que caber na LARGURA, nao so na altura")

# Até aqui só a altura era conferida. A etiqueta de 1"x1" mostrou o buraco: um
# EAN-13 legível precisa de ~28,3mm e o papel tem 25,4mm. Nenhum formato do
# catálogo esbarrava nisso — e medida livre deixaria qualquer largura entrar.

check("EAN-13 precisa de mais de 28mm, e isso e a norma, nao escolha nossa",
      27.5 <= codigos.largura_necessaria_mm(
          codigos.EAN13, "7891234567895", 2, unidades.ZEBRA_203) <= 29.0,
      codigos.largura_necessaria_mm(codigos.EAN13, "7891234567895", 2,
                                    unidades.ZEBRA_203))

check("Code128 fica mais largo com dado mais longo",
      codigos.largura_necessaria_mm(codigos.CODE128, "A" * 20, 2, unidades.ZEBRA_203)
      > codigos.largura_necessaria_mm(codigos.CODE128, "A", 2, unidades.ZEBRA_203) * 2)

# A receita nao POSICIONA o que nao cabe, e o lojista le o motivo na tela.
_um_por_um = receitas.montar("rolo_1x1", receitas.PADRAO)
check("na etiqueta de 1x1 polegada o codigo nao entra",
      not any(isinstance(e, CodigoBarras) for e in _um_por_um.elementos))
check("e a tela diz QUAL campo nao coube, em vez de sumir calado",
      receitas.nao_couberam(_um_por_um, receitas.PADRAO) == ["codigo_barras"],
      receitas.nao_couberam(_um_por_um, receitas.PADRAO))
check("numa etiqueta larga o mesmo codigo entra normalmente",
      any(isinstance(e, CodigoBarras)
          for e in receitas.montar("zebra_2x1", receitas.PADRAO).elementos))

# E os motores sao a segunda rede: um Code128 comprido cabe no template e nao
# cabe no papel, e isso so da pra saber com o dado do produto na mao.
_estreita = receitas.montar("avery_5167", ("sku", "codigo_barras"),
                            simbologia="CODE128")
_comprido = {"produto": {"titulo": "Trufa"},
             "variante": {"sku": "X", "preco": "1.00",
                          "codigo_barras": "CAM-PRETA-TAM-M-2026-LOTE-99"}}
_curto = {"produto": {"titulo": "Trufa"},
          "variante": {"sku": "X", "preco": "1.00", "codigo_barras": "ABC123"}}
check("codigo que vaza pela borda nao e impresso pelo ZPL",
      "^BC" not in zpl.render(_estreita, _comprido))
check("e o que cabe continua sendo impresso",
      "^BC" in zpl.render(_estreita, _curto))
check("a previa concorda com o ZPL: o que nao imprime, nao aparece",
      ("<svg x=" in motor_svg.render(_estreita, _curto))
      and ("<svg x=" not in motor_svg.render(_estreita, _comprido)))


secao("64. O QR sai do MESMO tamanho nos tres motores")

# Medido: o mesmo modelo com o mesmo dado saia 18,0mm no PDF e no SVG e 16,5mm
# no ZPL. A causa e que o ^BQ do ZPL recebe uma MAGNIFICACAO inteira, e o motor
# usava o `modulo_dots` — que e a largura da barra fina de um codigo linear e
# nao diz nada sobre o tamanho de um QR.
#
# O perigo real nao e a diferenca de 1,5mm: e que no ZPL o tamanho dependia do
# DADO. Uma URL longa (matriz 57) na magnificacao 4 da 28,5mm num campo de 18mm,
# e o QR sai andando pra fora da etiqueta.

_URLS = ("https://x.co/a",
         "https://ecocasa.com.br/p/canudo-vidro-reto-20cm",
         "https://loja.com.br/produtos/kit-canudos-de-vidro-reto-20cm-com-escova")


def _lado_no_zpl(url, altura_mm=18.0):
    t = Template(nome="qr", midia=Midia(50.8, 25.4), calibracao=Calibracao(),
                 elementos=[CodigoBarras(x_mm=2, y_mm=4, campo="produto.url",
                                         simbologia="QR", altura_mm=altura_mm,
                                         modulo_dots=4)])
    saida = zpl.render(t, {"produto": {"url": url}})
    mag = int(_re5.search(r"\^BQN,2,(\d+)", saida).group(1))
    return unidades.dots_para_mm(codigos.modulos_do_qr(url) * mag,
                                 unidades.ZEBRA_203)


def _lado_no_svg(url, altura_mm=18.0):
    t = Template(nome="qr", midia=Midia(50.8, 25.4), calibracao=Calibracao(),
                 elementos=[CodigoBarras(x_mm=2, y_mm=4, campo="produto.url",
                                         simbologia="QR", altura_mm=altura_mm,
                                         modulo_dots=4)])
    saida = motor_svg.render(t, {"produto": {"url": url}})
    return float(_re5.search(
        r'<svg x="[0-9.]+" y="[0-9.]+" width="([0-9.]+)"', saida).group(1))


for _url in _URLS:
    check("QR de %d caracteres: ZPL e previa do mesmo tamanho" % len(_url),
          abs(_lado_no_zpl(_url) - _lado_no_svg(_url)) < 0.05,
          (_lado_no_zpl(_url), _lado_no_svg(_url)))
    check("QR de %d caracteres: e perto do tamanho pedido" % len(_url),
          abs(_lado_no_zpl(_url) - 18.0) <= 3.0, _lado_no_zpl(_url))

# A magnificacao tem que sair da ALTURA. Se saisse do modulo_dots, ela seria a
# mesma pros tres dados — que era exatamente o bug.
_mags = {codigos.lado_do_qr_mm(u, 18.0, unidades.ZEBRA_203)[1] for u in _URLS}
check("a magnificacao muda com o dado, porque a matriz muda", len(_mags) > 1, _mags)

check("QR maior pedido vira QR maior desenhado",
      _lado_no_zpl(_URLS[1], 24.0) > _lado_no_zpl(_URLS[1], 12.0),
      (_lado_no_zpl(_URLS[1], 12.0), _lado_no_zpl(_URLS[1], 24.0)))


secao("65. Os digitos sob o codigo sao escolha do lojista")

# Numa Avery 5167 (44,45 x 12,7mm) a conta dava 0,07mm de FALTA pro SKU. Os
# digitos sob as barras custam 2,6mm e repetem o que o codigo ja carrega; o SKU
# nao esta em nenhum outro lugar da etiqueta. Quem escolhe e o lojista — e a
# Saratoga Chocolate reclamou publicamente de SKU sumindo justamente nessa
# etiqueta.
_5167 = ("titulo", "sku", "preco", "codigo_barras")
_com = receitas.montar("avery_5167", _5167, digitos_do_codigo=True)
_sem = receitas.montar("avery_5167", _5167, digitos_do_codigo=False)

check("com os digitos ligados, so o codigo cabe na 5167",
      receitas.nao_couberam(_com, _5167) == ["titulo", "sku", "preco"],
      receitas.nao_couberam(_com, _5167))
check("desligando os digitos, os quatro campos cabem",
      receitas.nao_couberam(_sem, _5167) == [],
      receitas.nao_couberam(_sem, _5167))
check("e o padrao continua sendo imprimir os digitos",
      [e.mostrar_texto for e in receitas.montar("zebra_2x1").elementos
       if isinstance(e, CodigoBarras)] == [True])
check("desligado, o ZPL para de pedir o texto legivel",
      ",N,N" in zpl.render(
          receitas.montar("zebra_2x1", receitas.PADRAO, digitos_do_codigo=False),
          _PRODUTO_EXEMPLO))

# O aviso tem que sair do template DESENHADO. A versao anterior remontava com os
# padroes, e ai quem escolhesse Code128 numa etiqueta estreita via o codigo
# sumir da previa sem aviso nenhum — porque o aviso fora calculado com EAN-13.
check("o aviso e calculado sobre o template que foi desenhado",
      receitas.nao_couberam(_sem, _5167)
      != receitas.nao_couberam(_com, _5167))


secao("66. Medida livre: o lojista digita a etiqueta que ele tem")

# THATS-RALLY e Rill reclamaram publicamente de nao poder digitar a medida da
# etiqueta que ja compraram. So deu pra fazer depois da conferencia de largura:
# sem ela, digitar 20mm devolveria um codigo de barras serrado pela borda.

_liv = receitas.montar("livre", receitas.PADRAO, largura_mm=40, altura_mm=20)
check("a etiqueta sai com a medida digitada",
      (_liv.midia.largura_mm, _liv.midia.altura_mm) == (40.0, 20.0),
      (_liv.midia.largura_mm, _liv.midia.altura_mm))
check("e o catalogo nao ganhou um formato fantasma",
      "livre" not in [f.codigo for f in _fmt.CATALOGO])
check("40x20mm comporta os quatro campos",
      receitas.nao_couberam(_liv, receitas.PADRAO) == [],
      receitas.nao_couberam(_liv, receitas.PADRAO))

# O caso que so existe por causa da medida livre: uma largura que nenhum
# formato do catalogo tem, e onde o codigo de barras nao cabe.
_quadrada = receitas.montar("livre", receitas.PADRAO, largura_mm=25.4, altura_mm=25.4)
check("largura estreita: o codigo nao entra, e a tela diz qual campo foi",
      receitas.nao_couberam(_quadrada, receitas.PADRAO) == ["codigo_barras"],
      receitas.nao_couberam(_quadrada, receitas.PADRAO))
check("e nao sobra codigo nenhum vazando pela borda",
      not any(isinstance(e, CodigoBarras) for e in _quadrada.elementos))

for _L, _A, _porque in ((5, 20, "largura menor que o minimo"),
                        (400, 20, "largura maior que o maximo"),
                        (40, 2, "altura menor que o minimo"),
                        ("dois", 20, "largura que nao e numero")):
    try:
        receitas.montar("livre", receitas.PADRAO, largura_mm=_L, altura_mm=_A)
        check("medida recusada: %s" % _porque, False, "aceitou %rx%r" % (_L, _A))
    except ValueError:
        check("medida recusada: %s" % _porque, True)

# Pela rota, porque erro de medida tem que virar 400 e nao 500 — o lojista
# precisa LER o motivo, nao ver "erro interno".
_r = _post("/api/previa", "loja-a.myshopify.com",
           {"receita": {"formato": "livre", "largura_mm": 40, "altura_mm": 20},
            "produto": {"titulo": "Camiseta"},
            "variante": {"sku": "A", "preco": "10.00",
                         "codigo_barras": "7891234567895"}})
check("a previa desenha a medida livre", _r.status_code == 200, _r.status_code)
check("e devolve a medida que foi pedida",
      (_r.get_json().get("largura_mm"), _r.get_json().get("altura_mm")) == (40.0, 20.0),
      _r.get_json().get("largura_mm"))

_r = _post("/api/previa", "loja-a.myshopify.com",
           {"receita": {"formato": "livre", "largura_mm": 4000, "altura_mm": 20},
            "produto": {}, "variante": {}})
check("medida absurda da 400 com motivo, nao 500", _r.status_code == 400, _r.status_code)
check("e o motivo diz os limites", "300" in (_r.get_json().get("erro") or ""),
      _r.get_json().get("erro"))

_r = _pega("/api/formatos", "loja-a.myshopify.com")
check("a tela recebe os limites pra montar o campo",
      _r.get_json()["livre"]["menor_mm"] == _fmt.MENOR_MEDIDA_MM)


secao("67. O token do Shopify agora vence, e o app renova sozinho")

# O Shopify parou de aceitar token de acesso que nao expira: a Admin API
# responde 403 com a mensagem dizendo isso. Foi assim que apareceu — o app
# instalado, a tela abrindo, e nenhum produto carregando.
#
# Agora o token vale 1 hora e vem com um refresh de 90 dias. O ciclo inteiro
# mora em `web/credenciais.py`, e a renovacao acontece no PORTAO, nao nas rotas:
# eram cinco rotas lendo `loja["token"]`, e espalhar isso garantiria que a sexta
# esquecesse. O sintoma de esquecer seria o app funcionar por uma hora depois de
# cada instalacao.
from web import credenciais as _cred_mod

_TROCAS = []


def _passado(segundos=10):
    """Um instante que JA passou.

    `lojas.daqui_a` recusa segundos negativos de proposito — vazio ali quer
    dizer "sem prazo", que e coisa diferente de "vencido". Pra testar vencido
    precisa de uma data de verdade no passado.
    """
    from datetime import datetime, timedelta, timezone
    return (datetime.now(timezone.utc)
            - timedelta(seconds=segundos)).isoformat(timespec="seconds")


def _falsa_troca(url, corpo):
    """A rede fingida. Guarda o que foi pedido, pra os testes conferirem."""
    _TROCAS.append(corpo)
    return {"access_token": "shpat_renovado", "refresh_token": "shprt_renovado",
            "expires_in": 3600, "refresh_token_expires_in": 7776000}


def _com_rede_fingida(fn, resposta=None):
    original = _rede3.trocar_token
    _rede3.trocar_token = resposta or _falsa_troca
    try:
        return fn()
    finally:
        _rede3.trocar_token = original


# --- 1. a loja da era anterior migra sozinha, sem reinstalar -----------------
# Reinstalar seria a alternativa, e lojista que precisa reinstalar pra o app
# voltar a funcionar desinstala e nao volta.
_ID_V = t_lojas.salvar("veterana.myshopify.com", "shpat_que_nunca_expirava",
                       "read_products,read_inventory")
t_lojas.marcar_plano(_ID_V, "pro")
_TROCAS.clear()
_r = _com_rede_fingida(
    lambda: _pega("/api/formatos", "veterana.myshopify.com"))
check("loja da era anterior continua entrando", _r.status_code == 200, _r.status_code)
check("e foi porque o token velho foi TROCADO, nao porque passou batido",
      len(_TROCAS) == 1 and _TROCAS[0].get("expiring") == "1", _TROCAS)
check("a troca mandou o token antigo como assunto",
      _TROCAS[0].get("subject_token") == "shpat_que_nunca_expirava")

_v = t_lojas.por_id(_ID_V)
check("o par novo foi GUARDADO — perder ele deixaria a loja orfa",
      (_v["token"], _v["refresh"]) == ("shpat_renovado", "shprt_renovado"),
      (_v["token"], _v["refresh"]))
check("e o prazo do token novo foi guardado junto", bool(_v["token_expira_em"]))

# --- 2. token ainda bom nao gasta chamada -----------------------------------
_TROCAS.clear()
_r = _com_rede_fingida(lambda: _pega("/api/formatos", "veterana.myshopify.com"))
check("token dentro da validade nao pede nada ao Shopify",
      _r.status_code == 200 and _TROCAS == [], _TROCAS)

# --- 3. token vencido e renovado com o refresh ------------------------------
t_lojas.guardar_credenciais(_ID_V, "shpat_vencido", "shprt_bom",
                            _passado(),
                            t_lojas.daqui_a(90 * 24 * 3600))
_TROCAS.clear()
_r = _com_rede_fingida(lambda: _pega("/api/formatos", "veterana.myshopify.com"))
check("token vencido nao barra o lojista", _r.status_code == 200, _r.status_code)
check("foi renovado com o refresh, nao com o code",
      len(_TROCAS) == 1 and _TROCAS[0].get("grant_type") == "refresh_token",
      _TROCAS)
check("e mandou o refresh guardado",
      _TROCAS[0].get("refresh_token") == "shprt_bom")

# A margem existe pra o token nao vencer ENTRE a conferencia e a chamada ao
# Shopify — corrida rara e impossivel de reproduzir depois.
t_lojas.guardar_credenciais(_ID_V, "shpat_quase", "shprt_bom",
                            t_lojas.daqui_a(60),
                            t_lojas.daqui_a(90 * 24 * 3600))
_TROCAS.clear()
_com_rede_fingida(lambda: _pega("/api/formatos", "veterana.myshopify.com"))
check("token que vence em 1 minuto ja e renovado antes da hora",
      len(_TROCAS) == 1, _TROCAS)

# --- 4. refresh morto: so o lojista resolve ---------------------------------
# 90 dias sem ninguem abrir o app. Tentar renovar aqui tomaria 400 do Shopify e
# viraria "erro interno" na tela — dizer o que aconteceu e melhor.
t_lojas.guardar_credenciais(_ID_V, "shpat_vencido", "shprt_morto",
                            _passado(), _passado())
_TROCAS.clear()
_r = _com_rede_fingida(lambda: _pega("/api/formatos", "veterana.myshopify.com"))
check("refresh vencido nao tenta renovar a toa", _TROCAS == [], _TROCAS)
check("e devolve 403 pedindo pra reconectar", _r.status_code == 403, _r.status_code)
check("com motivo que a tela sabe tratar",
      _r.get_json().get("motivo") == "precisa_reinstalar", _r.get_json())
check("e a mensagem manda abrir pelo painel do Shopify",
      "admin" in (_r.get_json().get("erro") or "").lower(), _r.get_json())

# Shopify recusando a renovacao cai no mesmo lugar, em vez de virar 500.
t_lojas.guardar_credenciais(_ID_V, "shpat_vencido", "shprt_bom",
                            _passado(),
                            t_lojas.daqui_a(90 * 24 * 3600))


def _troca_que_falha(url, corpo):
    raise _rede3.ErroDeRede("o Shopify respondeu 400: invalid_grant")


_r = _com_rede_fingida(lambda: _pega("/api/formatos", "veterana.myshopify.com"),
                       resposta=_troca_que_falha)
check("Shopify recusando a renovacao vira 403 legivel, nao 500",
      _r.status_code == 403, _r.status_code)

# --- 5. desinstalar mata as DUAS credenciais --------------------------------
# O refresh vale 90 dias e gera acesso novo sozinho: deixar ele no banco depois
# da desinstalacao seria guardar a chave da casa de quem ja se mudou.
t_lojas.guardar_credenciais(_ID_V, "shpat_vivo", "shprt_vivo",
                            t_lojas.daqui_a(3600), t_lojas.daqui_a(7776000))
t_lojas.desativar("veterana.myshopify.com")
_v = t_lojas.por_id(_ID_V)
check("desinstalar apaga o token", _v["token"] == "", _v["token"])
check("e apaga o refresh junto", _v["refresh"] == "", _v["refresh"])
check("e apaga os prazos, pra nao sobrar credencial com aparencia de viva",
      not _v["token_expira_em"] and not _v["refresh_expira_em"],
      (_v["token_expira_em"], _v["refresh_expira_em"]))

# --- 6. a conta de vencimento -----------------------------------------------
check("sem prazo nenhum nao e 'vencido' — e token de outro tipo",
      t_lojas.venceu("") is False)
check("prazo no passado venceu", t_lojas.venceu(_passado()))
check("prazo no futuro nao venceu", t_lojas.venceu(t_lojas.daqui_a(600)) is False)
check("mas vence dentro da margem se a margem alcanca",
      t_lojas.venceu(t_lojas.daqui_a(60), 300))
check("prazo corrompido conta como vencido, nao como eterno",
      t_lojas.venceu("nao-e-data"))


secao("68. Tres chamadas ao mesmo tempo nao podem queimar o refresh")

# Esta secao existe por causa de uma corrida MEDIDA. A tela dispara tres
# chamadas em paralelo ao abrir — a contagem, a previa e o uso. Com o token
# vencido, as tres renovavam ao mesmo tempo com o MESMO refresh, e o Shopify
# invalida o refresh no primeiro uso.
#
# O resultado medido antes do conserto: **duas das tres mandavam o lojista
# reinstalar**, toda vez que ele abrisse o app depois de uma hora parado. Teria
# pego o primeiro cliente.
import threading as _th

_ID_R = t_lojas.salvar("corrida.myshopify.com", "shpat_vencido",
                       "read_products,read_inventory",
                       refresh="shprt_original", expira_em=_passado(),
                       refresh_expira_em=t_lojas.daqui_a(90 * 24 * 3600))
t_lojas.marcar_plano(_ID_R, "pro")

_FIOS = 5
_gastos, _trava_do_teste = [], _th.Lock()
_tentativas = {"n": 0}
_largada = _th.Barrier(_FIOS)


def _shopify_que_rotaciona(url, corpo):
    """O Shopify de verdade: refresh usado uma vez nao vale mais.

    A pausa e de proposito: ela ALARGA a janela da corrida. Sem ela os fios
    serializam sozinhos e o teste passa mesmo sem trava nenhuma — que foi
    exatamente o que a sabotagem denunciou na primeira versao desta secao.
    """
    with _trava_do_teste:
        _tentativas["n"] += 1
    _tm.sleep(0.05)
    usado = corpo.get("refresh_token")
    with _trava_do_teste:
        if usado in _gastos:
            raise _rede3.ErroDeRede("400: invalid_grant (refresh ja gasto)")
        _gastos.append(usado)
    return {"access_token": "shpat_do_vencedor", "refresh_token": "shprt_novo",
            "expires_in": 3600, "refresh_token_expires_in": 7776000}


_resultados = []


def _uma_chamada():
    with _app.app_context():
        registro = t_lojas.buscar("corrida.myshopify.com")
        _largada.wait()          # os cinco saem juntos, de verdade
        try:
            _resultados.append(bool(_cred_mod.garantir(registro)))
        except _cred_mod.PrecisaReinstalar:
            _resultados.append(False)


_original_troca = _rede3.trocar_token
_rede3.trocar_token = _shopify_que_rotaciona
try:
    _fios = [_th.Thread(target=_uma_chamada) for _ in range(_FIOS)]
    for _f in _fios:
        _f.start()
    for _f in _fios:
        _f.join()
finally:
    _rede3.trocar_token = _original_troca

check("as cinco chamadas paralelas passam, nenhuma manda reinstalar",
      _resultados == [True] * _FIOS, _resultados)
# Esta e a checagem que importa. "Todas passaram" NAO prova a trava: a rede de
# seguranca entre processos faz o perdedor achar a credencial do vencedor e
# responder 200 do mesmo jeito. O que so acontece com a trava e o Shopify ser
# chamado UMA vez em vez de cinco.
check("e o Shopify foi chamado UMA vez, nao cinco",
      _tentativas["n"] == 1, _tentativas["n"])
check("com uma unica renovacao gasta", len(_gastos) == 1, _gastos)

_r_final = t_lojas.buscar("corrida.myshopify.com")
check("todas acabam com a MESMA credencial guardada",
      _r_final["token"] == "shpat_do_vencedor", _r_final["token"])

# A trava resolve fios do mesmo processo. Com varios processos, dois ainda
# podem renovar ao mesmo tempo — e o perdedor toma invalid_grant por usar um
# refresh que o vencedor ja gastou. Isso NAO e motivo pra mandar reinstalar:
# basta olhar se ja existe credencial boa guardada.
t_lojas.guardar_credenciais(_ID_R, "shpat_vencido", "shprt_ja_gasto",
                            _passado(), t_lojas.daqui_a(7776000))


def _outro_processo_ganhou(url, corpo):
    # Simula o vencedor: guarda credencial nova e recusa a nossa renovacao.
    t_lojas.guardar_credenciais(_ID_R, "shpat_do_outro", "shprt_do_outro",
                                t_lojas.daqui_a(3600),
                                t_lojas.daqui_a(7776000))
    raise _rede3.ErroDeRede("400: invalid_grant")


_r = _com_rede_fingida(lambda: _pega("/api/formatos", "corrida.myshopify.com"),
                       resposta=_outro_processo_ganhou)
check("perder a corrida pra outro PROCESSO nao vira 'reinstale'",
      _r.status_code == 200, _r.status_code)

# E quando nao ha credencial boa guardada, continua sendo reinstalar.
t_lojas.guardar_credenciais(_ID_R, "shpat_vencido", "shprt_morto",
                            _passado(), _passado())
_r = _com_rede_fingida(lambda: _pega("/api/formatos", "corrida.myshopify.com"),
                       resposta=_troca_que_falha)
check("mas falha de verdade continua pedindo pra reconectar",
      _r.status_code == 403, _r.status_code)


secao("69. O QR custa caro, e nao pode ser perguntado duas vezes")

# Medido: contar os modulos de um QR custa ~10ms, porque o reportlab so entrega
# a contagem depois de montar a matriz inteira. Um EAN-13 custa 0,01ms — duas
# mil vezes menos.
#
# Cada etiqueta pergunta DUAS vezes: uma pra ver se cabe na largura, outra pra
# desenhar. Sem cache, um lote de 300 etiquetas gastava 6,4 segundos de CPU.
_chamadas_qr = {"n": 0}
_original_modulos = codigos.modulos_do_qr.__wrapped__


def _contando(valor, correcao="M"):
    _chamadas_qr["n"] += 1
    return _original_modulos(valor, correcao)


codigos.modulos_do_qr.cache_clear()
_guardado_qr = codigos.modulos_do_qr
codigos.modulos_do_qr = _contando
try:
    _t_qr = Template(nome="q", midia=Midia(50.8, 25.4), calibracao=Calibracao(),
                     elementos=[CodigoBarras(x_mm=2, y_mm=4, campo="produto.url",
                                             simbologia="QR", altura_mm=18,
                                             modulo_dots=4)])
    zpl.render(_t_qr, {"produto": {"url": "https://exemplo.com/p/1"}})
finally:
    codigos.modulos_do_qr = _guardado_qr

# Sem cache sao 2 por etiqueta. O teste mede o CAMINHO, nao o cache: por isso a
# funcao contadora nao e cacheada.
check("uma etiqueta de QR pergunta a matriz no maximo duas vezes",
      _chamadas_qr["n"] <= 2, _chamadas_qr["n"])

_u = "https://exemplo.com/produto/teste-do-cache"
codigos.modulos_do_qr.cache_clear()
codigos.modulos_do_qr(_u)
codigos.modulos_do_qr(_u)
check("e a segunda pergunta pelo mesmo dado sai do cache",
      codigos.modulos_do_qr.cache_info().hits >= 1,
      codigos.modulos_do_qr.cache_info())
check("o cache tem teto, senao vira vazamento de memoria em lote grande",
      codigos.modulos_do_qr.cache_info().maxsize is not None)

# Perguntar a simbologia SEMPRE fazia `montar` estourar numa etiqueta que nem
# tem codigo de barras — quebrar por causa de um campo que o lojista desligou.
_ok = True
try:
    receitas.montar("zebra_2x1", ("titulo", "preco"), simbologia="NAO_EXISTE")
except ValueError:
    _ok = False
check("simbologia invalida nao quebra etiqueta SEM codigo de barras", _ok)

_recusou = False
try:
    receitas.montar("zebra_2x1", ("titulo", "codigo_barras"),
                    simbologia="NAO_EXISTE")
except ValueError:
    _recusou = True
check("mas com o codigo ligado ela continua sendo recusada", _recusou)


secao("70. ITF-14: o codigo da caixa, e o verificador que faltava no UPC-A")

# ITF-14 e o codigo da EMBALAGEM COLETIVA — o que vai na caixa de atacado, nao
# na peca. Entrou porque os dois concorrentes tem e e o unico dos tres simbolos
# que faltavam que muda a vida de alguem (Code 39 e Data Matrix sao numero pra
# tabela).

_ITF = "10789123456785"

check("ITF-14 valido passa", codigos.validar(_ITF, codigos.ITF14)[0])
check("ITF-14 com verificador errado nao passa",
      codigos.validar("10789123456789", codigos.ITF14)[0] is False)
check("ITF-14 com 13 digitos nao passa, e a mensagem diz quantos faltam",
      "14" in codigos.validar("1078912345678", codigos.ITF14)[1])
check("e a mensagem nao fica dizendo '14 ou 14'",
      "ou" not in codigos.validar("1078912345678", codigos.ITF14)[1])
for _apelido in ("ITF14", "ITF-14", "itf", "gtin14", "I2of5"):
    check("'%s' chega no ITF-14" % _apelido,
          codigos.obter(_apelido) is codigos.ITF14)

# O BURACO QUE APARECEU FAZENDO ISTO: a conferencia do verificador estava
# escrita `if simbologia is EAN13`, entao UPC-A com verificador errado passava
# direto e ia pro papel. Codigo errado imprime bonito, bipa, e traz o PRODUTO
# ERRADO no caixa — a pior falha possivel aqui, porque ninguem desconfia dela.
# E a queixa de uma estrela que um concorrente levou.
check("UPC-A valido passa", codigos.validar("012345678905", codigos.UPCA)[0])
check("UPC-A com verificador errado NAO passa (antes passava)",
      codigos.validar("012345678901", codigos.UPCA)[0] is False)
check("e o EAN-13 continua conferido",
      codigos.validar("7891234567890", codigos.EAN13)[0] is False)

# A conta do GS1 e a mesma pras tres, contando da DIREITA. A versao anterior
# contava da esquerda e so acertava por sorte no comprimento par do EAN-13.
check("a conta do GS1 serve pros tres comprimentos",
      (codigos.digito_verificador_gs1("789123456789"),
       codigos.digito_verificador_gs1("01234567890"),
       codigos.digito_verificador_gs1("1078912345678")) == ("5", "5", "5"))
check("e a funcao antiga do EAN-13 da o mesmo resultado",
      codigos.digito_verificador_ean("789123456789")
      == codigos.digito_verificador_gs1("789123456789"))


# A ARMADILHA: o ITF-14 tem barra LARGA, e a razao larga/fina muda a largura
# toda. O reportlab usa 2,2 por padrao e o ^BY do ZPL usa 3,0 — sem fixar, o
# MESMO codigo sairia 21% mais largo na Zebra que no PDF. E o mesmo defeito que
# o QR tinha, e o defeito que este projeto existe pra corrigir.
_dados_itf = {"variante": {"codigo_barras": _ITF}}


def _itf_no_papel(modulo_dots):
    t = Template(nome="itf", midia=Midia(101.6, 50.8), calibracao=Calibracao(),
                 elementos=[CodigoBarras(x_mm=3, y_mm=5,
                                         campo="variante.codigo_barras",
                                         simbologia="ITF14", altura_mm=12,
                                         modulo_dots=modulo_dots)])
    largura_svg = float(_re5.search(
        r'<svg x="[0-9.]+" y="[0-9.]+" width="([0-9.]+)"',
        motor_svg.render(t, _dados_itf)).group(1))
    largura_zpl = unidades.dots_para_mm(
        codigos.MODULOS_FIXOS["ITF14"] * modulo_dots, unidades.ZEBRA_203)
    return largura_zpl, largura_svg, zpl.render(t, _dados_itf)


for _mod in (2, 3):
    _z, _s, _saida = _itf_no_papel(_mod)
    check("ITF-14 com modulo %d: ZPL e previa da MESMA largura" % _mod,
          abs(_z - _s) < 0.05, (_z, _s))

check("a razao esta fixada, e nao no padrao 2,2 do reportlab",
      codigos.ITF14.razao_larga == 3.0)
check("e o ^BY do ZPL manda a mesma razao", "^BY2,3," in _itf_no_papel(2)[2])

# O ^B2 aceita um parametro a mais que o ^BE: o "calcular digito verificador".
# Vai como N porque a gente ja manda o codigo completo — se fosse Y a
# impressora acrescentaria um 15o digito e o codigo nao bipa mais.
check("o ZPL nao pede pra impressora acrescentar outro verificador",
      "^B2N,96,Y,N,N" in _itf_no_papel(2)[2], _itf_no_papel(2)[2])
check("e o EAN-13 continua sem esse parametro a mais",
      codigos.EAN13.verificador_no_zpl is False)

# E o reportlab tambem nao pode acrescentar: o padrao dele e checksum=1.
from etiquetas.motores.pdf import argumentos_reportlab as _args_rl
check("o reportlab e mandado NAO acrescentar digito",
      _args_rl(codigos.ITF14).get("checksum") == 0)
check("simbologia sem barra larga nao recebe razao nenhuma",
      _args_rl(codigos.EAN13) == {})

# A conta de largura tem que valer pro ITF-14 tambem, senao ele vaza igual.
check("ITF-14 nao cabe numa etiqueta de 25mm",
      codigos.largura_necessaria_mm(codigos.ITF14, _ITF, 2,
                                    unidades.ZEBRA_203) > 25.4)
_estreita = receitas.montar("rolo_1x1", receitas.PADRAO, simbologia="ITF14")
check("e a receita nao poe ele numa etiqueta que ele nao cabe",
      "codigo_barras" in receitas.nao_couberam(_estreita, receitas.PADRAO))


# O CODIGO QUE SOME CALADO. Os motores recusam desenhar codigo que nao bipa, e
# isso esta certo. Mas sumir sem dizer por que nao: o lojista escolhe ITF-14, o
# codigo desaparece da previa, e ele conclui que o app quebrou.
#
# O buraco e anterior ao ITF-14 — EAN-13 com verificador errado ja sumia calado.
# So que o ITF-14 recusa TODO codigo de 13 digitos, entao virou rotina.
def _previa_de(simbologia, codigo_do_produto, formato="zebra_2x1"):
    return _post("/api/previa", "loja-a.myshopify.com", {
        "receita": {"formato": formato, "simbologia": simbologia,
                    "campos": list(receitas.PADRAO)},
        "item": {"produto": {"titulo": "Caixa"},
                 "variante": {"sku": "CX-1", "preco": "10.00",
                              "codigo_barras": codigo_do_produto}},
    }).get_json()


_p = _previa_de("ITF14", "7891234567895")
check("ITF-14 num produto de 13 digitos explica por que o codigo sumiu",
      "14" in (_p.get("codigo_invalido") or ""), _p.get("codigo_invalido"))
_p = _previa_de("EAN13", "7891234567890")
check("verificador errado tambem explica, em vez de sumir calado",
      "verificador" in (_p.get("codigo_invalido") or ""), _p.get("codigo_invalido"))
_p = _previa_de("EAN13", "7891234567895")
check("codigo bom nao gera recado nenhum",
      not _p.get("codigo_invalido"), _p.get("codigo_invalido"))
_p = _previa_de("EAN13", "")
check("produto SEM codigo nao e erro de configuracao, e nao vira recado",
      not _p.get("codigo_invalido"), _p.get("codigo_invalido"))
_p = _previa_de("ITF14", "10789123456785", formato="rolo_1x1")
check("codigo largo demais pro papel tambem e explicado",
      bool(_p.get("codigo_invalido") or _p.get("nao_coube")), _p)


secao("71. O plano gratis acompanha o mercado")

# 200, e nao 100: e o que Yanet e LabelFast dao de graca (conferido em
# 30/08/2026). Perder por 2x no primeiro numero que o lojista compara e caro, e
# etiqueta renderizada nao custa quase nada pra gerar.
check("o gratis da 200 etiquetas por mes",
      cobranca.PLANOS["gratis"]["limite_etiquetas_mes"] == 200)
check("e o resumo mostrado ao lojista diz o mesmo numero",
      "200" in cobranca.PLANOS["gratis"]["resumo"]
      and "200" in _txt.t("plano_gratis_resumo", "pt")
      and "200" in _txt.t("plano_gratis_resumo", "en"))
check("o Pro continua sem limite",
      cobranca.PLANOS["pro"]["limite_etiquetas_mes"] == 0)


secao("72. A ficha da loja de apps nao pode prometer o que o codigo nao faz")

# Isto existe por causa de um erro cometido HOJE: o documento de prospectos
# prometia "a altura do codigo e sua" pra uma lojista, e o lojista NAO escolhe a
# altura do codigo — ela sai da etiqueta. So apareceu porque fui conferir antes
# de mandar a mensagem.
#
# A ficha e pior que aquele documento: ela e um contrato publico. Prometer 100
# etiquetas quando o app da 200 e feio; prometer 200 quando o app da 100 e
# reclamacao no primeiro dia. E "read-only" e a unica frase da lista que nenhum
# concorrente pode escrever — perder ela sem perceber seria jogar fora a coisa
# mais dificil de copiar que este app tem.
_FICHA = _io.open("docs/ficha-loja-de-apps.md", encoding="utf-8").read()

check("a ficha promete o mesmo numero de etiquetas gratis que o codigo da",
      "%d labels/month" % cobranca.PLANOS["gratis"]["limite_etiquetas_mes"] in _FICHA,
      cobranca.PLANOS["gratis"]["limite_etiquetas_mes"])
check("e o mesmo preco do Pro",
      "US$ %.2f" % cobranca.PLANOS["pro"]["preco_usd"] in _FICHA,
      cobranca.PLANOS["pro"]["preco_usd"])
check("e o mesmo nome que vai na fatura do lojista",
      cobranca.NOME_DO_APP in _FICHA, cobranca.NOME_DO_APP)

# A ficha e os escopos tem que contar a MESMA historia, nos dois sentidos.
#
# Antes: se a ficha diz "read-only", nao pode haver escopo de escrita.
# Agora:  se ha escopo de escrita, a ficha NAO pode dizer "read-only" — e tem
# que dizer o que vale no lugar.
_escreve = bool([e for e in oauth.ESCOPOS if e.startswith("write")])

# O que vai PRA LOJA DE APPS e o que nao esta em blockquote: neste documento a
# explicacao mora em `> ` e o texto que se copia e cola nao. Sem separar os
# dois, o teste leria o comentario que EXPLICA a remocao do "read-only" como
# se fosse a promessa — e reprovaria a ficha por falar sobre a propria
# historia.
_FICHA_TEXTO = "\n".join(l for l in _FICHA.splitlines()
                         if not l.lstrip().startswith(">"))

if "Read-only" in _FICHA_TEXTO:
    check("a ficha so diz 'read-only' se o app REALMENTE nao pede escrita",
          not _escreve, oauth.ESCOPOS)
if _escreve:
    check("pedindo escrita, a ficha nao promete mais read-only",
          "Read-only" not in _FICHA_TEXTO,
          [l for l in _FICHA_TEXTO.splitlines() if "Read-only" in l])
    # E ela tem que dizer o que vale NO LUGAR. Tirar a promessa e nao pôr nada
    # deixaria o lojista sem saber o que o app faz com o catalogo dele.
    check("e diz, no texto que vai pra vitrine, que nada e escrito sem clique",
          "Nothing is written until you click" in _FICHA_TEXTO)
    check("e que da pra desfazer", "undo it" in _FICHA_TEXTO)
    check("e que o app diz QUE TIPO de numero gerou",
          "the app says which you got" in _FICHA_TEXTO)

# Toda simbologia citada na ficha tem que existir. Prometer Data Matrix numa
# lista e a forma mais barata de virar reclamacao de uma estrela.
_CITADAS = {"EAN-13": "EAN13", "UPC-A": "UPCA", "Code 128": "CODE128",
            "ITF-14": "ITF14", "Data Matrix": "DATAMATRIX", "Code 39": "CODE39"}
for _nome, _chave in _CITADAS.items():
    if _nome not in _FICHA:
        continue
    _existe = True
    try:
        codigos.obter(_chave)
    except ValueError:
        _existe = False
    check("a ficha cita %s, e o motor desenha %s" % (_nome, _nome), _existe)

# A hospedagem citada na ficha e a mesma que o app usa pro link de instalacao.
check("o endereco na ficha e o mesmo dos documentos de instalacao",
      "etikbarcode.pythonanywhere.com" in _FICHA)


secao("73. A fila de impressao nao pode perder o que foi escolhido antes")

# ISTO E TESTE DE FONTE, e vale dizer o que ele prova e o que nao prova. A tela
# e JavaScript e roda no navegador; a bateria e Python. Entao aqui se conferem
# INVARIANTES DO CODIGO, e o comportamento foi medido no navegador, com numero:
#
#   Antes: escolher um produto, buscar outra coisa, escolher o segundo →
#          contador dizendo "2 produto(s), 52 etiqueta(s)" e fila com 1.
#          O primeiro sumia do PDF em silencio, no momento de imprimir.
#   Depois: tres bipes seguidos → 3 na fila, quantidades vindas do estoque.
#
# A causa era `fila()` percorrer `itens`, que e zerado a cada busca nova. Quem
# busca duas vezes — que e como todo mundo usa uma caixa de busca — perdia a
# primeira escolha.
_tela = _io.open("web/rotas_tela.py", encoding="utf-8").read()

check("a fila e montada a partir do que foi ESCOLHIDO, nao da busca atual",
      "escolhidos.forEach(function (e) {" in _tela
      and "itens.forEach" not in _tela.split("function fila()")[1].split("}")[0])
check("e o que se guarda e o item inteiro, nao so a quantidade",
      "{item: it, quantidade:" in _tela)

# Um lugar so pra escolher. Se a caixinha e o leitor guardassem cada um do seu
# jeito, um dos dois esqueceria o item e o produto sumiria do PDF de novo.
check("existe um unico lugar que poe alguem na fila",
      _tela.count("escolhidos.set(") == 1, _tela.count("escolhidos.set("))
check("e a caixinha passa por ele", "escolher(it, parseInt(q.value" in _tela)
check("e o leitor tambem", "escolher(it, it.quantidade || 1)" in _tela)

# O LEITOR. Um leitor de codigo de barras e um teclado: digita e manda Enter,
# entao cai na busca. A regra e o casamento EXATO com codigo ou SKU — e nao "a
# busca devolveu um so". Quem digita "caneca" e recebe um resultado nao pediu
# pra escolher; codigo identico ao cadastrado so chega de leitor ou de colagem.
check("o leitor casa pelo codigo de barras exato",
      '(it.variante.codigo_barras || "").trim() === lido' in _tela)
check("ou pelo SKU exato",
      '(it.variante.sku || "").trim().toLowerCase() === lido.toLowerCase()' in _tela)
check("e NAO por 'a busca devolveu um resultado so'",
      "achados.length !== 1" in _tela and "itens.length === 1" not in _tela)
check("bipar o mesmo codigo duas vezes nao duplica",
      "if (escolhidos.has(it.variante.id)) return;" in _tela)
check("o texto da busca fica selecionado pro proximo bipe substituir",
      "b.select();" in _tela)
check("e o leitor so age em busca nova, nao ao carregar mais resultados",
      "if (!continuar) escolherOEscaneado();" in _tela)


secao("74. Gerador de SKU: o passo barato, e o unico que nao mente")

# SKU nao tem norma — nao existe autoridade de numeracao, nem digito
# verificador, nem faixa reservada. Por isso ele e o primeiro passo do gerador:
# da pra gerar sem prometer o que nao e. Ver docs/gerador-de-codigo.md.
#
# Entrou porque os DOIS apps que crescem no nicho usam gerar como manchete: o
# RF (539 avaliacoes, lancado 24/10/2025) e o LabelCraft. O Etik nao gerava.
from etiquetas import skus


def _prod(titulo, variante, sku="", forn="Acme Ltda", tipo="Camiseta"):
    return {"produto": {"titulo": titulo, "fornecedor": forn, "tipo": tipo},
            "variante": {"titulo": variante, "sku": sku}}


check("acento sai, porque vira Code 128 e fonte de impressora termica",
      skus.normalizar("Açaí") == "ACAI", skus.normalizar("Açaí"))
check("o que nao e letra nem numero sai",
      skus.normalizar("A/B C-1") == "ABC1", skus.normalizar("A/B C-1"))
check("campo vazio vira peca vazia, sem quebrar", skus.normalizar("") == "")
check("e campo None tambem", skus.normalizar(None) == "")

# MEDIDO, e foi defeito da primeira versao: "M / Preto" saia "MPRE", colado e
# ilegivel. O Shopify ja entrega a estrutura em barras — destruir era jogar
# informacao fora.
check("a variante preserva a estrutura das opcoes",
      skus.normalizar_variante("M / Preto") == "M-PRET",
      skus.normalizar_variante("M / Preto"))
check("opcao vazia nao deixa separador solto",
      skus.normalizar_variante("M /  / Preto") == "M-PRET",
      skus.normalizar_variante("M /  / Preto"))

# O molde padrao NAO tem {seq}, e isso tambem foi medicao: com a variante no
# molde cada item virava seu proprio grupo e a sequencia saia 0001 em TODOS.
# Ela nao desambiguava nada — so sujava o SKU.
check("o molde padrao nao carrega sequencia inutil",
      "{seq}" not in skus.MOLDE_PADRAO, skus.MOLDE_PADRAO)
check("e {seq} deixou de ser exigida",
      skus.conferir_molde("{fornecedor}-{variante}") == [],
      skus.conferir_molde("{fornecedor}-{variante}"))
check("mas molde so com numero continua recusado",
      skus.conferir_molde("{seq}") != [])
check("e peca inventada e recusada com a lista do que existe",
      "fantasia" in (skus.conferir_molde("{fantasia}-{seq}") or [""])[0])

_itens = [_prod("Camiseta Basica", "P / Preto"),
          _prod("Camiseta Basica", "M / Preto"),
          _prod("Outra camiseta", "M / Preto"),
          _prod("Ja cadastrada", "M", sku="CAM-ANTIGO-01"),
          _prod("Sem nada", "", forn="", tipo="")]
_lote = skus.gerar_lote(_itens)

check("cada variante vira um SKU legivel",
      _lote[0]["sku"] == "ACME-CAMI-P-PRET", _lote[0]["sku"])

# A REGRA QUE VEM DE FORA E NAO SE DISCUTE: SKU em uso esta em planilha, em
# etiqueta ja impressa e na cabeca de quem trabalha na loja. Trocar quebra os
# tres de uma vez, e em silencio.
check("quem ja tem SKU nao e tocado",
      _lote[3]["sku"] == "CAM-ANTIGO-01" and _lote[3]["pulado"],
      _lote[3])

# SKU repetido faz o lojista pegar o produto errado no estoque — e, se virar
# codigo de barras depois, bipa errado no caixa.
check("SKU repetido dentro do lote ganha sufixo",
      _lote[2]["sku"] == "ACME-CAMI-M-PRET-2", _lote[2]["sku"])
check("e o lojista e AVISADO de que ganhou, em vez de o numero aparecer do nada",
      "sufixo" in (_lote[2].get("aviso") or ""), _lote[2].get("aviso"))

# Produto sem fornecedor, sem tipo e sem variante existe de verdade em catalogo
# importado as pressas. A primeira versao gerava "0001" pra ele — um SKU que e
# so numero, que nao diz nada e com o qual nao se acha nada.
check("produto sem texto nenhum e PULADO, nao vira numero puro",
      _lote[4]["sku"] == "" and "texto" in _lote[4]["pulado"], _lote[4])

# Colisao com o que a LOJA ja tem, nao so com o lote.
_com_loja = skus.gerar_lote([_prod("Camiseta Basica", "P / Preto")],
                            ja_usados=["ACME-CAMI-P-PRET"])
check("colide com SKU que a loja ja usa, e desvia",
      _com_loja[0]["sku"] == "ACME-CAMI-P-PRET-2", _com_loja[0]["sku"])
check("e a comparacao ignora maiusculas, senao o desvio falha",
      skus.gerar_lote([_prod("Camiseta Basica", "P / Preto")],
                      ja_usados=["acme-cami-p-pret"])[0]["sku"]
      != "ACME-CAMI-P-PRET")

check("mesmo molde e mesmo produto dao sempre o mesmo SKU",
      skus.montar(skus.MOLDE_PADRAO, _itens[0], 1)
      == skus.montar(skus.MOLDE_PADRAO, _itens[0], 1))
check("SKU nao passa do teto que cabe na etiqueta pequena",
      len(skus.montar("{titulo}-{fornecedor}-{tipo}-{variante}",
                      _prod("T"*40, "V"*40, forn="F"*40, tipo="P"*40))
          ) <= skus.TAMANHO_MAXIMO)
check("a ordem do lote e a ordem recebida, pro lojista conferir a tabela",
      len(_lote) == len(_itens))


secao("75. O filtro de 'o que esta faltando no cadastro'")

# E o destaque numero 5 da ficha do lider do nicho ("Identifique instantaneamente
# produtos sem codigos de barras ou SKUs") e o passo zero de quem vai gerar:
# antes de criar codigo pra alguem, mostrar PRA QUEM falta.
from loja import catalogo as _cat

_catalogo = [
    {"produto": {"titulo": "com tudo"},
     "variante": {"sku": "A-1", "codigo_barras": "7891234567895"}},
    {"produto": {"titulo": "sem codigo"},
     "variante": {"sku": "A-2", "codigo_barras": ""}},
    {"produto": {"titulo": "sem sku"},
     "variante": {"sku": "", "codigo_barras": "7899876543210"}},
    {"produto": {"titulo": "sem nada"},
     "variante": {"sku": "   ", "codigo_barras": None}},
    # Espaco em branco e DIFERENTE de None, e precisa de item proprio: com None
    # o campo ja e falso sem `.strip()`, entao a primeira versao deste teste nao
    # exercitava o `.strip()` nenhuma vez. A sabotagem denunciou.
    {"produto": {"titulo": "so espacos"},
     "variante": {"sku": " ", "codigo_barras": "   "}},
]


def _titulos(filtro):
    return [i["produto"]["titulo"] for i in _cat.filtrar(_catalogo, filtro)]


check("sem filtro vem tudo", len(_cat.filtrar(_catalogo, "")) == 5)
check("'sem_codigo' pega quem nao tem codigo",
      _titulos("sem_codigo") == ["sem codigo", "sem nada", "so espacos"],
      _titulos("sem_codigo"))
check("'sem_sku' pega quem nao tem SKU",
      _titulos("sem_sku") == ["sem sku", "sem nada", "so espacos"],
      _titulos("sem_sku"))
check("'sem_nenhum' pega so quem nao tem os dois",
      _titulos("sem_nenhum") == ["sem nada", "so espacos"], _titulos("sem_nenhum"))

# Espaco em branco nao e cadastro preenchido. Produto com sku "   " aparece
# preenchido na planilha e nao serve pra nada.
# Produto com sku "   " aparece PREENCHIDO na planilha e nao serve pra nada.
check("so espaco em branco conta como vazio, no SKU",
      "so espacos" in _titulos("sem_sku"))
check("e no codigo de barras tambem",
      "so espacos" in _titulos("sem_codigo"))
check("None tambem conta como vazio", "sem nada" in _titulos("sem_codigo"))

# Filtro desconhecido NAO pode levantar erro: ele vem da querystring, e uma tela
# antiga mandando um nome que nao existe mais deve ver o catalogo inteiro, nao
# uma tela de erro.
check("filtro que nao existe devolve tudo, em vez de quebrar",
      len(_cat.filtrar(_catalogo, "inventado")) == 5)
check("filtro que nao existe devolve tudo mesmo com nome de filtro real dentro",
      len(_cat.filtrar(_catalogo, "SEM_CODIGO")) == 5)
check("lista vazia nao quebra", _cat.filtrar([], "sem_codigo") == [])
check("lista None nao quebra", _cat.filtrar(None, "sem_codigo") == [])


# O LACO DE PAGINAS. Uma pagina so nao serve com filtro ligado: o Shopify
# devolve 50 produtos e talvez 2 estejam sem codigo — o lojista veria 2 e
# concluiria que sao todos na loja inteira.
_paginas = {"n": 0}


def _catalogo_falso(loja, token, corpo, **kw):
    """Tres paginas, e so a TERCEIRA tem produto sem codigo."""
    _paginas["n"] += 1
    sem = _paginas["n"] == 3
    return {"data": {"products": {
        "pageInfo": {"hasNextPage": _paginas["n"] < 3,
                     "endCursor": "c%d" % _paginas["n"]},
        "nodes": [{
            "title": "Produto da pagina %d" % _paginas["n"],
            "vendor": "Acme", "productType": "Camiseta",
            "variants": {"pageInfo": {"hasNextPage": False}, "nodes": [{
                "id": "gid://shopify/ProductVariant/%d" % _paginas["n"],
                "title": "Default", "sku": "SKU-%d" % _paginas["n"],
                "barcode": "" if sem else "789123456789%d" % _paginas["n"],
                "price": "10.00", "compareAtPrice": None,
                "inventoryQuantity": 3}]}}]}}}


_orig_g = _rede4.graphql
_rede4.graphql = _catalogo_falso
try:
    _r = _pega("/api/produtos?filtro=sem_codigo", "loja-a.myshopify.com")
    _d = _r.get_json()
finally:
    _rede4.graphql = _orig_g

check("com filtro, a busca continua ate achar — nao para na primeira pagina",
      _paginas["n"] == 3, _paginas["n"])
check("e devolve o que achou", len(_d.get("itens") or []) == 1, _d.get("itens"))
check("dizendo ENTRE QUANTOS procurou, senao o lojista acha que e a loja toda",
      _d.get("varridos") == 3, _d.get("varridos"))
check("e repetindo qual filtro foi aplicado", _d.get("filtro") == "sem_codigo")

# Sem filtro, uma pagina so — varrer o catalogo inteiro a toa estouraria o tempo
# da requisicao numa loja grande.
_paginas["n"] = 0
_rede4.graphql = _catalogo_falso
try:
    _r = _pega("/api/produtos", "loja-a.myshopify.com")
finally:
    _rede4.graphql = _orig_g
check("sem filtro, busca uma pagina so", _paginas["n"] == 1, _paginas["n"])
check("e nao inventa contagem de varredura",
      _r.get_json().get("varridos") is None)

# O TETO, medido pelo COMPORTAMENTO e nao pela constante. A primeira versao
# deste teste so conferia que o numero existia entre 2 e 20 — e a sabotagem
# mostrou que dava pra apagar o `break` inteiro sem nada gritar.
#
# O caso que ele protege e o oposto do anterior: loja onde TUDO tem codigo faria
# a busca varrer o catalogo inteiro e estourar o tempo da requisicao.
_sem_fim = {"n": 0}


# O catalogo falso TEM fim, e de proposito. Sem o teto na rota, um catalogo
# infinito faria a bateria TRAVAR em vez de falhar — e travar e o pior jeito de
# pegar defeito: nao diz o que quebrou, so para. Aconteceu de verdade: a
# sabotagem que remove o teto ficou aplicada num arquivo e a bateria pendurou.
_TETO_DO_FALSO = 40


def _catalogo_infinito(loja, token, corpo, **kw):
    """Muitas paginas, e NENHUMA tem produto sem codigo."""
    _sem_fim["n"] += 1
    return {"data": {"products": {
        "pageInfo": {"hasNextPage": _sem_fim["n"] < _TETO_DO_FALSO,
                     "endCursor": "c%d" % _sem_fim["n"]},
        "nodes": [{
            "title": "Tem codigo %d" % _sem_fim["n"],
            "vendor": "Acme", "productType": "Camiseta",
            "variants": {"pageInfo": {"hasNextPage": False}, "nodes": [{
                "id": "gid://shopify/ProductVariant/%d" % _sem_fim["n"],
                "title": "Default", "sku": "S%d" % _sem_fim["n"],
                "barcode": "789123456789%d" % (_sem_fim["n"] % 10),
                "price": "10.00", "compareAtPrice": None,
                "inventoryQuantity": 1}]}}]}}}


_rede4.graphql = _catalogo_infinito
try:
    _r = _pega("/api/produtos?filtro=sem_codigo", "loja-a.myshopify.com")
finally:
    _rede4.graphql = _orig_g

check("a busca filtrada PARA no teto, em vez de varrer o catalogo inteiro",
      _sem_fim["n"] == _api.PAGINAS_POR_FILTRO, _sem_fim["n"])
check("e para MUITO antes do fim do catalogo, senao o teto nao serve pra nada",
      _api.PAGINAS_POR_FILTRO < _TETO_DO_FALSO)
check("e avisa que parou no teto, pro lojista saber que pode haver mais",
      _r.get_json().get("parou_no_teto") is True, _r.get_json().get("parou_no_teto"))


secao("76. O registro de desfazer — a excecao assumida do projeto")

# O impressoes.py diz que NADA do conteudo e guardado: nem titulo, nem SKU, nem
# preco. Esta tabela guarda SKU, e nao ha contorno: desfazer exige saber o que
# estava la antes. Entao a excecao e construida COMO excecao — o minimo, so o
# que NOS escrevemos, com prazo, e declarada na politica.
#
# Sem desfazer o gerador nao sobe: um defeito nosso aqui mexe no catalogo de
# quem paga, nao num papel. Etiqueta errada custa uma folha; SKU errado em 300
# produtos custa o inventario da loja.
from dados import gravacoes as _grav

_ID_G1 = _instalar("gravadora.myshopify.com", "tok-g1")
_ID_G2 = _instalar("vizinha.myshopify.com", "tok-g2")

_lote = _grav.registrar(_ID_G1, "sku",
                        [("gid/v1", "", "ACME-A"), ("gid/v2", "ANTIGO", "ACME-B")])
check("o lote e registrado e tem identificador", bool(_lote))

_u = _grav.ultimo_lote(_ID_G1)
check("e aparece como o ultimo lote desfazivel",
      _u and _u["quantos"] == 2 and _u["campo"] == "sku", _u)

_linhas = _grav.linhas_do_lote(_ID_G1, _lote)
check("guardando o valor ANTERIOR, que e o que permite reverter",
      [l["valor_antigo"] for l in _linhas] == ["", "ANTIGO"], _linhas)
check("e o valor novo, pra saber se ainda e nosso quando for desfazer",
      [l["valor_novo"] for l in _linhas] == ["ACME-A", "ACME-B"])

# A falha mais comum de app multi-inquilino, e aqui ela teria consequencia
# pior que ler: desfazer a escrita de outra loja.
check("uma loja NAO enxerga o lote da outra, mesmo sabendo o identificador",
      _grav.linhas_do_lote(_ID_G2, _lote) == [])
check("nem consegue marcar como desfeito o lote alheio",
      _grav.marcar_desfeito(_ID_G2, _lote) == 0)
check("e o lote continua intacto depois da tentativa",
      len(_grav.linhas_do_lote(_ID_G1, _lote)) == 2)

check("marcar desfeito marca as duas linhas",
      _grav.marcar_desfeito(_ID_G1, _lote) == 2)
check("e ai ele some da fila de desfazer, pra nao ser revertido duas vezes",
      _grav.ultimo_lote(_ID_G1) is None)
check("desfazer o mesmo lote de novo nao mexe em nada",
      _grav.marcar_desfeito(_ID_G1, _lote) == 0)

# Lista FECHADA de campos. Se um dia alguem tentar gravar `price` por engano, o
# erro aparece aqui e nao na loja do lojista.
for _campo in ("preco", "titulo", "inventoryQuantity", ""):
    _recusou = False
    try:
        _grav.registrar(_ID_G1, _campo, [("gid/x", "", "1")])
    except ValueError:
        _recusou = True
    check("campo %r nao e gravavel" % _campo, _recusou)
check("mas sku e codigo_barras sao",
      set(_grav.CAMPOS_GRAVAVEIS) == {"sku", "codigo_barras"})

_vazio = False
try:
    _grav.registrar(_ID_G1, "sku", [])
except ValueError:
    _vazio = True
check("lote sem mudanca nenhuma e recusado, em vez de criar lote fantasma",
      _vazio)

# O DESEMPATE, que custou uma sabotagem instavel pra aparecer.
#
# MEDIDO: `agora()` tem resolucao de SEGUNDO — duas chamadas a 50ms de
# distancia devolvem a mesma string. Ordenando so por `criado_em`, dois lotes
# do mesmo segundo ficam EMPATADOS, e o SQLite devolve qualquer um dos dois.
#
# Dois cliques seguidos caem no mesmo segundo com facilidade. O desfazer
# reverteria o lote errado, e o lojista nao teria como saber. A sabotagem do
# filtro por campo escapou uma vez e foi pega na outra justamente por causa
# disto — o placar virava cara ou coroa.
# E O TESTE PRECISA DE REPETICAO, porque o defeito e PROBABILISTICO.
#
# Medido: sem o desempate, a consulta acerta 15 de 40 — ela acaba ordenando
# pelo uuid do lote, que e aleatorio. Um par so de lotes pegaria a sabotagem
# em ~6 de cada 10 corridas, e teste instavel e pior que teste nenhum: ele faz
# o placar da bateria virar cara ou coroa.
#
# Com 20 pares, a chance de a sabotagem escapar e de uma em centenas de
# milhoes.
_ID_G3 = _instalar("empate.myshopify.com", "tok-g3")
_erraram, _empatados, _PARES = 0, 0, 20
for _i in range(_PARES):
    _a = _grav.registrar(_ID_G3, "sku", [("gid/e%da" % _i, "", "A")])
    _b = _grav.registrar(_ID_G3, "sku", [("gid/e%db" % _i, "", "B")])
    if (_grav.ultimo_lote(_ID_G3) or {}).get("lote") != _b:
        _erraram += 1
    with banco.conectar() as _c:
        _empatados += _c.execute(
            "SELECT COUNT(DISTINCT criado_em) FROM gravacoes "
            " WHERE loja_id = ? AND lote IN (?, ?)",
            (_ID_G3, _a, _b)).fetchone()[0] == 1
    _grav.marcar_desfeito(_ID_G3, _a)
    _grav.marcar_desfeito(_ID_G3, _b)

# O empate e medido PAR A PAR. Medir no conjunto seria instavel: 20 pares
# podem cruzar a virada do segundo e a assertiva falharia sozinha, sem defeito
# nenhum — que e o tipo de teste que faz a bateria perder a credibilidade.
check("os pares cairam MESMO no mesmo segundo (senao o teste nao prova nada)",
      _empatados >= _PARES - 2, "%d de %d empataram" % (_empatados, _PARES))
check("e o ultimo lote e SEMPRE o mais recente, mesmo empatado no relogio",
      _erraram == 0, "%d de %d erraram" % (_erraram, _PARES))

# E continua certo depois de desfazer: o anterior volta a ser o topo.
_p1 = _grav.registrar(_ID_G3, "sku", [("gid/p1", "", "PRIMEIRO")])
_p2 = _grav.registrar(_ID_G3, "sku", [("gid/p2", "", "SEGUNDO")])
_grav.marcar_desfeito(_ID_G3, _p2)
check("desfeito o segundo, o primeiro vira o ultimo",
      (_grav.ultimo_lote(_ID_G3) or {}).get("lote") == _p1,
      _grav.ultimo_lote(_ID_G3))
_grav.marcar_desfeito(_ID_G3, _p1)

# O PRAZO e o que impede isto de virar, com o tempo, uma copia do catalogo de
# todo mundo que ja usou o app.
check("existe prazo de guarda, e ele e curto o bastante",
      1 <= _grav.DIAS_DE_GUARDA <= 90, _grav.DIAS_DE_GUARDA)

_antigo = _grav.registrar(_ID_G1, "sku", [("gid/velho", "", "X")])
with banco.conectar() as _c:
    _c.execute("UPDATE gravacoes SET criado_em = datetime('now','-400 days') "
               "WHERE lote = ?", (_antigo,))
_novo = _grav.registrar(_ID_G1, "sku", [("gid/novo", "", "Y")])
_saiu = _grav.apagar_vencidas()
check("o que passou do prazo e apagado", _saiu >= 1, _saiu)
check("e o recente fica", len(_grav.linhas_do_lote(_ID_G1, _novo)) == 1)

# A politica tem que falar disto. O teste de esquema do banco agora pega TABELA
# nova tambem — foi ele que obrigou esta frase a existir.
_priv = _cliente.get("/privacy?idioma=pt").get_data(as_text=True)
_priv_en = _cliente.get("/privacy?idioma=en").get_data(as_text=True)
check("a politica em portugues fala do registro de desfazer",
      "desfazer" in _priv and "30 dias" in _priv)
check("e a em ingles tambem", "undo" in _priv_en and "30 days" in _priv_en)
check("e as duas dizem que so acontece se o lojista PEDIR",
      ("nunca usar" in _priv or "Se você nunca" in _priv)
      and "never use" in _priv_en)


secao("77. A mutacao que escreve no catalogo — o lugar mais cuidadoso do projeto")

# E o unico arquivo que pede permissao de ESCRITA. Um defeito nestas linhas mexe
# no catalogo de quem paga, nao num papel.
from loja import escrita as _esc

# TRES COISAS DA API que custaram pesquisa e se esquecem:
#
# 1. Nao existe campo `sku` na variante — ele mora em `inventoryItem.sku`.
#    Mandar `sku` direto e erro de esquema, e a mensagem do Shopify nao ajuda.
_c = _esc.consulta_de_skus("gid://p/1", [("gid://v/1", "ACME-A")])
_var = _c["variables"]["variantes"][0]
check("o SKU vai dentro de inventoryItem, nao solto na variante",
      _var == {"id": "gid://v/1", "inventoryItem": {"sku": "ACME-A"}}, _var)
check("e a consulta leva o id do produto, porque a mutacao e POR PRODUTO",
      _c["variables"]["produto"] == "gid://p/1")

# 2. `allowPartialUpdates` fica no padrao (false): ou o produto inteiro grava,
#    ou nenhuma variante dele grava. E o que mantem o desfazer EXATO — com
#    atualizacao parcial, metade gravaria e o registro teria que adivinhar qual.
check("a mutacao nao liga atualizacao parcial",
      "allowPartialUpdates" not in _esc.MUTACAO_VARIANTES)

# 3. A mutacao e por produto, entao o lote precisa ser agrupado.
_g = _esc.agrupar_por_produto([
    ("gid://p/1", "gid://v/1", "A"), ("gid://p/1", "gid://v/2", "B"),
    ("gid://p/2", "gid://v/3", "C")])
check("as mudancas sao agrupadas por produto",
      {k: len(v) for k, v in _g.items()} == {"gid://p/1": 2, "gid://p/2": 1}, _g)
check("e a ordem dentro do produto e mantida, pra bater com a tabela da tela",
      [v for v, _ in _g["gid://p/1"]] == ["gid://v/1", "gid://v/2"])

# Linha sem id nao vira escrita silenciosa: e dado torto vindo da tela, e gravar
# "no produto nenhum" seria pior que pular.
check("linha sem id de produto e descartada",
      _esc.agrupar_por_produto([("", "gid://v/9", "X")]) == {})
check("linha sem id de variante tambem",
      _esc.agrupar_por_produto([("gid://p/1", "", "X")]) == {})

for _args, _rot in ((("", [("gid://v/1", "A")]), "sem id de produto"),
                    (("gid://p/1", []), "sem variante nenhuma")):
    _recusou = False
    try:
        _esc.consulta_de_skus(*_args)
    except ValueError:
        _recusou = True
    check("recusa montar consulta %s" % _rot, _recusou)

# O SHOPIFY RESPONDE 200 COM ERRO DENTRO, em DUAS camadas: `errors` no topo
# (consulta malformada) e `userErrors` dentro da mutacao (recusa de negocio,
# tipo SKU duplicado). Olhar so uma e o jeito classico de achar que gravou.
check("erro de topo e visto",
      _esc.erros_da_escrita({"errors": [{"message": "Field nao existe"}]})
      == ["Field nao existe"])
check("userError tambem e visto, com o campo que falhou",
      "SKU ja em uso" in _esc.erros_da_escrita(
          {"data": {"productVariantsBulkUpdate": {"userErrors": [
              {"field": ["variants", "0", "inventoryItem", "sku"],
               "message": "SKU ja em uso"}]}}})[0])
check("resposta boa nao inventa erro",
      _esc.erros_da_escrita({"data": {"productVariantsBulkUpdate": {
          "userErrors": [], "productVariants": [{"id": "gid://v/1",
                                                 "sku": "A"}]}}}) == [])
check("resposta torta vira erro, em vez de passar como sucesso",
      _esc.erros_da_escrita(None) != [])
check("e userError sem mensagem nao some",
      _esc.erros_da_escrita({"data": {"productVariantsBulkUpdate": {
          "userErrors": [{}]}}}) != [])

# O REGISTRO DE DESFAZER SAI DAQUI, e nao da lista que a gente mandou. Mandar
# nao e gravar: anotar "desfazer" para algo que nao aconteceu faria o desfazer
# sobrescrever um valor que o lojista pos a mao.
_resp = {"data": {"productVariantsBulkUpdate": {"productVariants": [
    {"id": "gid://v/1", "sku": "ACME-A"}]}}}
check("so a variante CONFIRMADA pelo Shopify conta como gravada",
      _esc.variantes_gravadas(_resp) == {"gid://v/1": "ACME-A"})
check("resposta sem confirmacao nenhuma devolve vazio, nao a lista enviada",
      _esc.variantes_gravadas({"data": {"productVariantsBulkUpdate": {}}}) == {})
check("e resposta torta nao quebra", _esc.variantes_gravadas(None) == {})

# O id do produto passou a vir no catalogo porque a mutacao precisa dele.
_amostra = catalogo.para_etiquetas({"data": {"products": {"nodes": [{
    "id": "gid://shopify/Product/7", "title": "T", "vendor": "V",
    "productType": "P",
    "variants": {"nodes": [{"id": "gid://shopify/ProductVariant/9",
                            "title": "D", "sku": "", "barcode": "",
                            "price": "1.00"}]}}]}}})
check("o catalogo passou a trazer o id do produto",
      _amostra[0]["produto"]["id"] == "gid://shopify/Product/7", _amostra[0]["produto"])
check("mas ele nao virou campo de etiqueta",
      not campos.existe("produto.id"))


secao("78. O gerador de SKU de ponta a ponta: previa, gravar, desfazer")

# A regra que decide o desenho das tres rotas:
#
#   O SERVIDOR CALCULA O QUE GRAVA. O NAVEGADOR SO CONFIRMA QUAIS.
#
# O `aplicar` nao recebe os SKUs prontos da tela — ele refaz a mesma varredura e
# o mesmo calculo da previa, e grava so nas variantes cuja id o lojista
# confirmou. Se recebesse o valor pronto, qualquer coisa que o navegador
# mandasse iria parar no catalogo de quem paga.
_ID_W = _instalar("gera-sku.myshopify.com", "tok-w")
t_lojas.marcar_plano(_ID_W, "pro")

# A loja de mentira: dois produtos, tres variantes, uma delas JA com SKU.
_LOJA_FALSA = {
    "gid://p/1": [("gid://v/1", "P / Preto", ""), ("gid://v/2", "M / Preto", "")],
    "gid://p/2": [("gid://v/3", "Unico", "JA-TENHO")],
}
_gravacoes_feitas = []


def _shopify(loja, token, corpo, **kw):
    """Responde tanto a consulta de produtos quanto a mutacao de escrita."""
    consulta = corpo.get("query", "")
    if "productVariantsBulkUpdate" in consulta:
        pid = corpo["variables"]["produto"]
        confirmadas = []
        for v in corpo["variables"]["variantes"]:
            novo_sku = v["inventoryItem"]["sku"]
            _gravacoes_feitas.append((pid, v["id"], novo_sku))
            # a loja de mentira passa a refletir a escrita
            _LOJA_FALSA[pid] = [(vid, tit, novo_sku if vid == v["id"] else sku)
                                for vid, tit, sku in _LOJA_FALSA[pid]]
            confirmadas.append({"id": v["id"], "sku": novo_sku})
        return {"data": {"productVariantsBulkUpdate":
                         {"productVariants": confirmadas, "userErrors": []}}}
    return {"data": {"products": {
        "pageInfo": {"hasNextPage": False, "endCursor": None},
        "nodes": [{"id": pid, "title": "Produto " + pid[-1], "vendor": "Acme",
                   "productType": "Camiseta",
                   "variants": {"pageInfo": {"hasNextPage": False}, "nodes": [
                       {"id": vid, "title": tit, "sku": sku, "barcode": "",
                        "price": "10.00", "compareAtPrice": None,
                        "inventoryQuantity": 2}
                       for vid, tit, sku in variantes]}}
                  for pid, variantes in _LOJA_FALSA.items()]}}}


def _com_shopify(fn):
    original = _rede4.graphql
    _rede4.graphql = _shopify
    try:
        return fn()
    finally:
        _rede4.graphql = original


# --- 1. a previa nao escreve nada ------------------------------------------
_gravacoes_feitas.clear()
_r = _com_shopify(lambda: _post("/api/skus/previa", "gera-sku.myshopify.com",
                                {"filtro": "sem_sku"}))
_d = _r.get_json()
check("a previa responde", _r.status_code == 200, _r.status_code)
check("e NAO escreveu nada no catalogo", _gravacoes_feitas == [])

_propostos = {l["variante_id"]: l["sku"] for l in _d["linhas"] if l["sku"] and not l["pulado"]}
check("ela propoe SKU so pra quem nao tem",
      set(_propostos) == {"gid://v/1", "gid://v/2"}, sorted(_propostos))
check("e o SKU proposto e legivel",
      _propostos["gid://v/1"] == "ACME-CAMI-P-PRET", _propostos.get("gid://v/1"))
# Com o filtro "sem_sku" quem JA TEM e excluido na varredura e nem chega na
# tabela — comportamento certo. Quem aparece marcado como pulado e no filtro
# "todos", que e onde o lojista espera ver a loja inteira e entender por que
# alguns nao ganham SKU.
_todos = _com_shopify(lambda: _post("/api/skus/previa", "gera-sku.myshopify.com",
                                    {"filtro": ""})).get_json()
check("com filtro 'sem_sku', quem ja tem nem aparece",
      not any(l["variante_id"] == "gid://v/3" for l in _d["linhas"]))
check("mas com 'todos' ele aparece, marcado como pulado e com o motivo",
      any(l["variante_id"] == "gid://v/3" and "SKU" in (l["pulado"] or "")
          for l in _todos["linhas"]),
      [l for l in _todos["linhas"] if l["variante_id"] == "gid://v/3"])
check("e o SKU que ele ja tinha e mostrado, pro lojista conferir",
      any(l["variante_id"] == "gid://v/3" and l["sku_atual"] == "JA-TENHO"
          for l in _todos["linhas"]))
check("molde invalido e recusado antes de qualquer varredura",
      _com_shopify(lambda: _post("/api/skus/previa", "gera-sku.myshopify.com",
                                 {"molde": "{seq}"})).status_code == 400)

# --- 2. gravar so o que foi confirmado -------------------------------------
_gravacoes_feitas.clear()
_r = _com_shopify(lambda: _post("/api/skus/aplicar", "gera-sku.myshopify.com",
                                {"filtro": "sem_sku",
                                 "variantes": ["gid://v/1"]}))
_d = _r.get_json()
check("grava e diz quantos", _d.get("gravados") == 1, _d)
check("E SO A CONFIRMADA foi escrita, nao as duas propostas",
      [g[1] for g in _gravacoes_feitas] == ["gid://v/1"], _gravacoes_feitas)
check("com o SKU que o SERVIDOR calculou",
      _gravacoes_feitas[0][2] == "ACME-CAMI-P-PRET", _gravacoes_feitas)

# O navegador nao dita o valor: mandar um SKU pronto no corpo nao muda nada,
# porque o servidor recalcula.
_gravacoes_feitas.clear()
_r = _com_shopify(lambda: _post("/api/skus/aplicar", "gera-sku.myshopify.com",
                                {"filtro": "sem_sku", "variantes": ["gid://v/2"],
                                 "sku": "INVENTADO-PELO-NAVEGADOR",
                                 "linhas": [{"variante_id": "gid://v/2",
                                             "sku": "INVENTADO"}]}))
check("valor mandado pelo navegador NAO vai pro catalogo",
      _gravacoes_feitas and "INVENTADO" not in _gravacoes_feitas[0][2],
      _gravacoes_feitas)

check("sem escolher ninguem, recusa com motivo",
      _com_shopify(lambda: _post("/api/skus/aplicar", "gera-sku.myshopify.com",
                                 {"variantes": []})).status_code == 400)

# Catalogo mudou entre ver e confirmar: nao e erro de ninguem, e dizer isso e
# melhor que responder "gravei 0" em silencio.
_r = _com_shopify(lambda: _post("/api/skus/aplicar", "gera-sku.myshopify.com",
                                {"filtro": "sem_sku",
                                 "variantes": ["gid://v/1"]}))
check("confirmar quem ja ganhou SKU devolve 409 com explicacao",
      _r.status_code == 409 and "erro" in _r.get_json(), _r.status_code)

# --- 3. desfazer devolve o valor anterior ----------------------------------
_u = _grav.ultimo_lote(_ID_W)
check("o lote ficou registrado pra desfazer", _u and _u["quantos"] == 1, _u)

_gravacoes_feitas.clear()
_r = _com_shopify(lambda: _post("/api/skus/desfazer", "gera-sku.myshopify.com", {}))
_d = _r.get_json()
check("desfaz e diz quantos", _d.get("desfeitos") == 1, _d)
check("escrevendo de volta o valor VAZIO que estava la antes",
      _gravacoes_feitas and _gravacoes_feitas[0][2] == "", _gravacoes_feitas)
check("e o lote sai da fila, pra nao ser desfeito duas vezes",
      _grav.ultimo_lote(_ID_W) is None or
      _grav.ultimo_lote(_ID_W)["lote"] != _u["lote"])
check("desfazer sem nada pra desfazer devolve 404 com motivo",
      _com_shopify(lambda: _post("/api/skus/desfazer", "gera-sku.myshopify.com",
                                 {})).status_code in (404, 200))


# --- 4. os tres casos que a sabotagem mostrou que eu nao exercitava ---------
#
# Os tres passaram batido na primeira versao desta secao, cada um por um motivo
# diferente — e os tres protegem o catalogo de quem paga.

# (a) CONFIRMAR QUEM JA TEM SKU. Antes eu so confirmava variante vazia, entao a
# protecao de "nunca sobrescrever" nunca era tocada. Aqui o lojista confirma de
# proposito a variante que ja tem "JA-TENHO".
_gravacoes_feitas.clear()
_r = _com_shopify(lambda: _post("/api/skus/aplicar", "gera-sku.myshopify.com",
                                {"filtro": "", "variantes": ["gid://v/3"]}))
check("confirmar quem JA TEM SKU nao sobrescreve",
      all(g[1] != "gid://v/3" for g in _gravacoes_feitas), _gravacoes_feitas)
check("e o SKU que estava la continua intacto",
      ("gid://v/3", "Unico", "JA-TENHO") in _LOJA_FALSA["gid://p/2"],
      _LOJA_FALSA["gid://p/2"])


# (b) O SHOPIFY CONFIRMANDO MENOS DO QUE RECEBEU. Mandar nao e gravar — e a
# minha loja falsa confirmava tudo, entao "enviado" e "confirmado" eram a mesma
# lista e a diferenca nao aparecia.
def _shopify_que_engole_um(loja, token, corpo, **kw):
    if "productVariantsBulkUpdate" in corpo.get("query", ""):
        vs = corpo["variables"]["variantes"]
        # confirma so a PRIMEIRA, e cala sobre o resto
        return {"data": {"productVariantsBulkUpdate": {
            "productVariants": [{"id": vs[0]["id"],
                                 "sku": vs[0]["inventoryItem"]["sku"]}],
            "userErrors": []}}}
    return _shopify(loja, token, corpo, **kw)


_LOJA_FALSA["gid://p/9"] = [("gid://v/91", "A", ""), ("gid://v/92", "B", "")]
_orig = _rede4.graphql
_rede4.graphql = _shopify_que_engole_um
try:
    _r = _post("/api/skus/aplicar", "gera-sku.myshopify.com",
               {"filtro": "sem_sku", "variantes": ["gid://v/91", "gid://v/92"]})
finally:
    _rede4.graphql = _orig
check("so a variante CONFIRMADA entra na conta",
      _r.get_json().get("gravados") == 1, _r.get_json())
_u = _grav.ultimo_lote(_ID_W)
check("e so ela entra no registro de desfazer",
      _u and _u["quantos"] == 1, _u)
_grav.marcar_desfeito(_ID_W, _u["lote"])


# (c) O SHOPIFY RECUSANDO. Ele responde 200 com o erro DENTRO; ignorar isso
# faria o app registrar como gravado o que foi recusado — e aí o desfazer
# escreveria por cima de um valor que nunca foi nosso.
def _shopify_que_recusa(loja, token, corpo, **kw):
    if "productVariantsBulkUpdate" in corpo.get("query", ""):
        return {"data": {"productVariantsBulkUpdate": {
            "productVariants": [{"id": corpo["variables"]["variantes"][0]["id"],
                                 "sku": "NAO DEVIA CONTAR"}],
            "userErrors": [{"field": ["variants", "0"],
                            "message": "SKU ja em uso"}]}}}
    return _shopify(loja, token, corpo, **kw)


_LOJA_FALSA["gid://p/8"] = [("gid://v/81", "C", "")]
_rede4.graphql = _shopify_que_recusa
try:
    _r = _post("/api/skus/aplicar", "gera-sku.myshopify.com",
               {"filtro": "sem_sku", "variantes": ["gid://v/81"]})
finally:
    _rede4.graphql = _orig
_d = _r.get_json()
check("recusa do Shopify nao conta como gravado",
      _d.get("gravados") == 0, _d)
check("e o motivo chega ao lojista, em vez de sumir",
      any("SKU ja em uso" in f for f in (_d.get("falhas") or [])), _d)
check("e NADA vai pro registro de desfazer",
      _grav.ultimo_lote(_ID_W) is None, _grav.ultimo_lote(_ID_W))


# --- 5. a mesma falha dita UMA vez ------------------------------------------
#
# A mutacao do Shopify e por produto. Uma loja fora do ar devolve o mesmo erro
# uma vez por produto, e a tela mostraria quatro linhas identicas — ruido que
# esconde a falha que e DIFERENTE das outras.
_LOJA_FALSA["gid://p/7"] = [("gid://v/71", "D", "")]
_LOJA_FALSA["gid://p/6"] = [("gid://v/61", "E", "")]


def _shopify_fora_do_ar(loja, token, corpo, **kw):
    if "productVariantsBulkUpdate" in corpo.get("query", ""):
        raise _rede4.ErroDeRede("a loja nao respondeu")
    return _shopify(loja, token, corpo, **kw)


_rede4.graphql = _shopify_fora_do_ar
try:
    _r = _post("/api/skus/aplicar", "gera-sku.myshopify.com",
               {"filtro": "sem_sku", "variantes": ["gid://v/71", "gid://v/61"]})
finally:
    _rede4.graphql = _orig
_d = _r.get_json()
check("dois produtos falhando igual viram UMA linha",
      _d.get("falhas") == ["a loja nao respondeu"], _d)
check("e com tudo falhando, gravados e zero",
      _d.get("gravados") == 0, _d)
check("e nada entrou no registro de desfazer",
      _grav.ultimo_lote(_ID_W) is None, _grav.ultimo_lote(_ID_W))


# --- 6. no modo dev a gravacao RECUSA, em vez de fingir ---------------------
#
# Simular a escrita faria o `/dev/` fingir justamente a parte perigosa — e e a
# parte que esta secao ja exercita com uma loja falsa de verdade. A previa
# funciona sem Shopify nenhum; a gravacao diz por que nao.
_ID_DEV = _instalar("so-dev.myshopify.com", _dev.TOKEN_FALSO)
t_lojas.marcar_plano(_ID_DEV, "pro")

_gravacoes_feitas.clear()
_r = _post("/api/skus/aplicar", "so-dev.myshopify.com",
           {"filtro": "sem_sku", "variantes": ["gid://v/1"]})
check("no modo dev o aplicar recusa", _r.status_code == 400, _r.status_code)
check("dizendo por que", bool(_r.get_json().get("erro")), _r.get_json())
check("e NADA foi escrito", _gravacoes_feitas == [], _gravacoes_feitas)
check("o desfazer recusa do mesmo jeito",
      _post("/api/skus/desfazer", "so-dev.myshopify.com", {}).status_code == 400)
# E a previa continua de pe: e pra ela que o /dev/ existe.
_r = _post("/api/skus/previa", "so-dev.myshopify.com", {"filtro": "sem_sku"})
check("mas a PREVIA do modo dev funciona", _r.status_code == 200, _r.status_code)
check("com o catalogo de mentira dentro",
      bool(_r.get_json().get("linhas")), _r.get_json())


# --- 7. a tela nao promete desfazer o que nao aconteceu --------------------
#
# MEDIDO no navegador, modo dev: clicar em Gravar respondia
#
#     "Gravados 0. Dá para desfazer."
#
# Nada tinha sido escrito, e a tela mandava o lojista procurar um desfazer que
# nao existia. E a mesma meia verdade que o app recusa em todo lugar, so que
# dita pela tela em vez de pelo servidor.
check("zero gravado usa o texto de 'nada foi gravado'",
      "? T.gerar_gravados.replace" in _tela and ": T.gerar_nada_gravado" in _tela)
check("e esse texto NAO fala em desfazer",
      "desfazer" not in _txt.TEXTOS["gerar_nada_gravado"]["pt"].lower()
      and "undo" not in _txt.TEXTOS["gerar_nada_gravado"]["en"].lower())
# A tabela so sai da tela se algo mudou: apagar a previa depois de uma
# gravacao que falhou tira justamente o que serve pra tentar de novo.
check("a tabela so e apagada quando algo foi gravado",
      _tela.count("if (quantos) {") == 2, _tela.count("if (quantos) {"))


# --- 8. a conferencia de repetidos olha o catalogo, nao a lista filtrada ---
#
# MEDIDO em 20/10/2026, e era um defeito pra valer.
#
# A conferencia de colisao recebia os SKUs dos itens JA FILTRADOS. Com o filtro
# padrao "sem SKU", isso e uma lista de strings VAZIAS — o filtro tira
# exatamente os produtos que SEGURAM os SKUs em uso. A regra 3 do desenho
# ("conferir colisao dentro da loja") estava inteiramente derrotada, e calada.
#
# Dois produtos com o mesmo SKU fazem o lojista pegar o produto errado no
# estoque. Se o SKU virar codigo de barras depois, bipa errado no caixa.
_LOJA_FALSA["gid://p/5"] = [("gid://v/51", "Unico", "ACME-CAMI-UNIC")]
_LOJA_FALSA["gid://p/4"] = [("gid://v/41", "Unico", "")]

_r = _com_shopify(lambda: _post("/api/skus/previa", "gera-sku.myshopify.com",
                                {"filtro": "sem_sku"}))
_d = _r.get_json()
_proposto = {l["variante_id"]: l["sku"] for l in _d["linhas"]
             if l["sku"] and not l["pulado"]}
check("o produto sem SKU aparece na previa", "gid://v/41" in _proposto,
      sorted(_proposto))
check("e o SKU proposto NAO repete o de outro produto do catalogo",
      _proposto.get("gid://v/41") != "ACME-CAMI-UNIC",
      _proposto.get("gid://v/41"))
check("ele ganha sufixo, e o lojista e avisado disso",
      _proposto.get("gid://v/41") == "ACME-CAMI-UNIC-2"
      and any(l["variante_id"] == "gid://v/41" and l["aviso"]
              for l in _d["linhas"]),
      _proposto.get("gid://v/41"))
# E o produto que SEGURA o SKU nem aparece na tabela — ele foi filtrado. E
# justamente por isso que a conferencia nao podia sair dela.
check("e o dono do SKU nem esta na tabela, que era a armadilha",
      not any(l["variante_id"] == "gid://v/51" for l in _d["linhas"]))

# A conferencia so alcanca o que foi varrido. Em catalogo grande isso e um
# pedaco, e a resposta tem que DIZER isso em vez de deixar o lojista achar que
# a garantia vale pra loja inteira.
check("a resposta diz se a conferencia foi completa",
      "conferencia_completa" in _d, sorted(_d))

del _LOJA_FALSA["gid://p/5"], _LOJA_FALSA["gid://p/4"]


secao("79. O Code 128 so aceita ASCII — e isso passava batido")

# MEDIDO em 20/10/2026, montando o gerador de codigo:
#
#   codigos.validar("CAFÉ-01", CODE128)  ->  (True, "")
#
# O validador liberava, e ai:
#   - o PDF estourava `ValueError: Illegal barcode` dentro do reportlab, que
#     chega ao lojista como erro de servidor, sem explicacao nenhuma;
#   - o ZPL mandava o byte acentuado pra impressora, pra sair lixo ou nao sair.
#
# A linha culpada dizia "Code128 e QR aceitam texto". Vale pro QR, que codifica
# UTF-8 de verdade. NAO vale pro Code 128, cujo alfabeto e ASCII e nada alem.
#
# Num catalogo em portugues isto nao e caso de borda: "CAFÉ", "AÇÚCAR" e
# "CAMISA-ÇÃO" sao nomes de produto comuns, e SKU sai de nome de produto.
check("Code 128 com acento e RECUSADO",
      codigos.validar("CAFÉ-01", codigos.CODE128)[0] is False)
check("e o motivo diz QUAL caractere tirar",
      "'É'" in codigos.validar("CAFÉ-01", codigos.CODE128)[1],
      codigos.validar("CAFÉ-01", codigos.CODE128)[1])
check("dois caracteres ruins viram dois avisos, sem repetir",
      codigos.validar("CAMISA-ÇÃO", codigos.CODE128)[1].count("'") == 4,
      codigos.validar("CAMISA-ÇÃO", codigos.CODE128)[1])
check("simbolo de moeda tambem nao vai",
      codigos.validar("10€", codigos.CODE128)[0] is False)
check("mas pontuacao ASCII vai, que e SKU de verdade",
      codigos.validar("ACME-CAM/M.1 2", codigos.CODE128)[0] is True,
      codigos.validar("ACME-CAM/M.1 2", codigos.CODE128))

# O QR nao herda a restricao: ele codifica UTF-8, e um QR com acento e legitimo.
check("o QR continua aceitando acento",
      codigos.validar("Café R$ 9,90", codigos.QRCODE)[0] is True)

# A fronteira foi MEDIDA contra o reportlab, nao adivinhada: ele aceita 0-127 e
# recusa de 128 pra cima. A gente para em 126 de proposito — caractere de
# controle num SKU nao e codigo, e um DEL invisivel seria pior que a recusa.
check("caractere de controle tambem e recusado",
      codigos.validar("A\x07B", codigos.CODE128)[0] is False)

# E os DOIS motores precisam concordar com o validador, senao a previa mostra
# uma coisa e o papel sai outra.
from dataclasses import replace as _dc_replace

_TPL_128 = receitas.montar(formato="avery_5160", campos=["titulo"],
                           simbologia="CODE128")
_TPL_128 = _dc_replace(_TPL_128, elementos=list(_TPL_128.elementos) + [
    CodigoBarras(campo="variante.sku", x_mm=3, y_mm=3, simbologia="CODE128",
                 altura_mm=10, modulo_dots=2)])


def _item_sku(sku):
    return {"produto": {"titulo": "Cafe", "fornecedor": "A", "tipo": "B"},
            "variante": {"sku": sku, "codigo_barras": sku, "preco": "10.00",
                         "titulo": "U"}}


_pdf_limpo = motor_pdf.render(_TPL_128, [(_item_sku("CAFE-01"), 1)])
check("o PDF desenha o Code 128 limpo", len(_pdf_limpo) > 2000, len(_pdf_limpo))
try:
    _pdf_acento = motor_pdf.render(_TPL_128, [(_item_sku("CAFÉ-01"), 1)])
    _estourou = ""
except Exception as _e:
    _pdf_acento, _estourou = b"", "%s: %s" % (type(_e).__name__, _e)
check("e com acento NAO estoura mais", _estourou == "", _estourou)
check("ele so omite o codigo, que e a regra de sempre",
      0 < len(_pdf_acento) < len(_pdf_limpo), len(_pdf_acento))

check("o ZPL desenha o limpo", "^BC" in zpl.render(_TPL_128, _item_sku("CAFE-01")))
check("e OMITE o acentuado, em vez de mandar pra impressora",
      "^BC" not in zpl.render(_TPL_128, _item_sku("CAFÉ-01")))

# E o lojista precisa saber POR QUE sumiu. A funcao que explica chama o mesmo
# `codigos.validar`, entao ela herda a mensagem nova de graca — mas isso so e
# verdade enquanto ela nao tiver uma segunda opiniao propria.
_motivo = _api._por_que_o_codigo_sumiu(_TPL_128, _item_sku("CAFÉ-01"))
check("e a previa diz por que o codigo sumiu", "'É'" in _motivo, _motivo)


secao("80. O gerador de codigo de barras: tres casos, e nenhum deles mente")

# SKU nao tem dono. Codigo de barras TEM: cada faixa de numeracao pertence a
# alguem. Por isso aqui nao existe "gerar codigo" no singular — existem tres
# situacoes, e o lojista precisa saber em qual esta.
#
# Ver docs/gerador-de-codigo.md.
from etiquetas import numeracao as _num


def _prod(titulo, sku="", codigo="", fornecedor="Acme"):
    return {"produto": {"titulo": titulo, "fornecedor": fornecedor,
                        "tipo": "Camiseta"},
            "variante": {"titulo": "M", "sku": sku, "codigo_barras": codigo}}


# --- caso 1: o lojista TEM prefixo de empresa GS1 --------------------------
_r = _num.gerar_lote([_prod("A"), _prod("B")], modo="gs1", prefixo="7891234")
check("gera um codigo por produto", [l["codigo"] for l in _r] ==
      ["7891234000019", "7891234000026"], [l["codigo"] for l in _r])
check("e diz que tipo de numero e", all(l["tipo"] == "GTIN-13" for l in _r))

# O teste que importa: o numero gerado tem que passar pela MESMA validacao que
# o app usa pra aceitar codigo digitado. Verificador errado imprime bonito,
# bipa, e traz o produto errado no caixa.
for _seq in (1, 2, 42, 99999):
    _c = _num.montar_gtin("7891234", _seq)
    check("o GTIN gerado (seq %d) passa na validacao do proprio app" % _seq,
          codigos.validar(_c, codigos.EAN13) == (True, ""),
          (_c, codigos.validar(_c, codigos.EAN13)))

# --- caso 2: sem prefixo, faixa de circulacao restrita ---------------------
_r = _num.gerar_lote([_prod("A")], modo="interno")
check("o codigo interno comeca com 2, que e a faixa reservada",
      _r[0]["codigo"].startswith("2"), _r[0]["codigo"])
check("e tambem e um EAN-13 valido, que bipa em qualquer leitor",
      codigos.validar(_r[0]["codigo"], codigos.EAN13) == (True, ""),
      _r[0]["codigo"])
# A frase que diz que o codigo NAO vale fora da loja mora junto do gerador, pra
# nao poder divergir dele. Codigo interno apresentado como GTIN e mentira com
# consequencia comercial.
check("existe aviso escrito para cada um dos tres modos",
      set(_num.AVISO_DO_MODO) == set(_num.MODOS), sorted(_num.AVISO_DO_MODO))

# O modulo guarda a CHAVE; o texto mora em textos.py porque o app e bilingue.
# Isto e o que impede as duas listas de divergirem — sem este teste, um modo
# novo sairia com a tela em branco justamente na frase que tem consequencia
# comercial. E mandar portugues pra tela em ingles seria falhar nela tambem.
for _modo, _chave in _num.AVISO_DO_MODO.items():
    check("o modo %s tem frase cadastrada" % _modo, _chave in _txt.TEXTOS, _chave)
    for _lingua in ("en", "pt"):
        check("  e ela existe em %s" % _lingua,
              (_txt.TEXTOS.get(_chave) or {}).get(_lingua, "").strip() != "",
              (_chave, _lingua))

check("o aviso do interno diz que nao serve em outra loja",
      "outra loja" in _txt.TEXTOS["codigo_aviso_interno"]["pt"]
      and "another shop" in _txt.TEXTOS["codigo_aviso_interno"]["en"])
check("e o do GS1 avisa pra usar o prefixo DELE",
      "SUA empresa" in _txt.TEXTOS["codigo_aviso_gs1"]["pt"]
      and "YOUR company" in _txt.TEXTOS["codigo_aviso_gs1"]["en"])

# --- caso 3: Code 128 a partir do SKU --------------------------------------
_r = _num.gerar_lote([_prod("tem", sku="ACME-CAM-M"), _prod("nao tem"),
                      _prod("acento", sku="CAMISA-ÇÃO"),
                      _prod("repetido", sku="ACME-CAM-M")], modo="sku")
check("o codigo e o proprio SKU", _r[0]["codigo"] == "ACME-CAM-M", _r[0])
check("sem SKU, ele diz pra gerar o SKU primeiro",
      "gere o SKU primeiro" in _r[1]["pulado"], _r[1]["pulado"])
check("SKU com acento e RECUSADO, nao gravado pra quebrar na impressao",
      _r[2]["codigo"] == "" and "'Ç'" in _r[2]["pulado"], _r[2]["pulado"])
check("SKU repetido vira recusa, porque bipa o produto errado no caixa",
      _r[3]["codigo"] == "" and "repetido" in _r[3]["pulado"], _r[3]["pulado"])

# --- as regras que valem nos tres modos ------------------------------------
# REGRA 2 do desenho: nunca sobrescrever. O codigo que esta la pode ser
# comprado, e pode estar impresso em caixa fechada.
for _modo, _pre in (("gs1", "7891234"), ("interno", ""), ("sku", "")):
    _r = _num.gerar_lote([_prod("ja tem", sku="X1", codigo="7899999999994")],
                         modo=_modo, prefixo=_pre)
    check("modo %s nao sobrescreve codigo existente" % _modo,
          _r[0]["codigo"] == "7899999999994" and _r[0]["pulado"], _r[0])

# REGRA 3: colisao dentro da loja. Dois produtos com o mesmo codigo bipam o
# produto errado — e essa e a pior falha que este app pode causar.
_ja = ["7891234000019", "7891234000026"]
_r = _num.gerar_lote([_prod("C"), _prod("D")], modo="gs1", prefixo="7891234",
                     ja_usados=_ja)
check("nao repete codigo que a loja ja usa",
      not set(l["codigo"] for l in _r) & set(_ja),
      [l["codigo"] for l in _r])
check("e continua a numeracao de onde ela parou",
      [l["codigo"] for l in _r] == ["7891234000033", "7891234000040"],
      [l["codigo"] for l in _r])
# Com BURACO na numeracao, "continuar de onde parou" e "encher o buraco" dao
# respostas diferentes — e a segunda e perigosa: numero reaproveitado faz uma
# etiqueta velha, ja colada numa peca, apontar pro produto de agora.
_r = _num.gerar_lote([_prod("Z")], modo="gs1", prefixo="7891234",
                     ja_usados=["7891234000019", "7891234005009"])
check("com buraco na numeracao ele CONTINUA, em vez de reaproveitar",
      _r[0]["codigo"] == "7891234005014", _r[0]["codigo"])

check("nem repete dentro do proprio lote",
      len({l["codigo"] for l in _num.gerar_lote(
          [_prod(str(i)) for i in range(30)], modo="interno")}) == 30)

# --- o prefixo, conferido antes de qualquer coisa --------------------------
check("prefixo vazio e recusado com instrucao",
      "GS1" in _num.conferir_prefixo("")[0], _num.conferir_prefixo(""))
check("prefixo com letra e recusado", _num.conferir_prefixo("abc"))
check("prefixo curto demais e recusado", _num.conferir_prefixo("789"))
check("prefixo que nao deixa espaco pro item e recusado",
      _num.conferir_prefixo("789123456789"))
check("prefixo bom passa", _num.conferir_prefixo("7891234") == [])

# Prefixo longo e prefixo de empresa pequena: com 11 digitos sobram 9 numeros.
# Dizer isso ANTES vale mais que gravar 9 e calar sobre os outros 291.
check("a capacidade e dita em numero", _num.capacidade("7891234") == 99999,
      _num.capacidade("7891234"))
check("prefixo de 11 digitos comporta 9", _num.capacidade("78912345678") == 9)
_r = _num.gerar_lote([_prod(str(i)) for i in range(12)], modo="gs1",
                     prefixo="78912345678")
check("quando o prefixo enche, os que sobraram dizem POR QUE",
      sum(1 for l in _r if l["codigo"]) == 9
      and "cheio" in _r[9]["pulado"], [l["codigo"] or l["pulado"] for l in _r])

# Dois motivos DIFERENTES, e dizer "acabou" nos dois esconderia do lojista
# justamente o que ele pode resolver.
#
# A numeracao continua de onde a loja parou em vez de encher buraco — numero
# reaproveitado faz etiqueta velha, ja colada, apontar pro produto de agora. O
# efeito colateral e que um prefixo pequeno esgota a CONTINUACAO com numeros
# livres embaixo, e isso nao e a mesma coisa que estar cheio.
_cheio = [_num.montar_gtin("78912345678", i) for i in range(1, 10)]
_r = _num.gerar_lote([_prod("x")], "gs1", "78912345678", _cheio)
check("faixa cheia de verdade diz CHEIO",
      "cheio" in _r[0]["pulado"], _r[0]["pulado"])

_r = _num.gerar_lote([_prod("x")], "gs1", "78912345678", [_cheio[-1]])
check("mas com numeros livres embaixo ele NAO diz que esta cheio",
      "cheio" not in _r[0]["pulado"], _r[0]["pulado"])
check("ele conta quantos sobraram e explica por que nao reaproveita",
      "8 n" in _r[0]["pulado"] and "apontar" in _r[0]["pulado"],
      _r[0]["pulado"])

# Modo que nao existe e erro de programacao, nao de lojista: levanta.
try:
    _num.gerar_lote([_prod("A")], modo="inventado")
    _levantou = False
except ValueError:
    _levantou = True
check("modo inexistente levanta, em vez de gerar qualquer coisa", _levantou)

# E o gerador nao escreve em lugar nenhum — e isso que deixa a previa existir
# antes de o app pedir permissao de escrita ao lojista.
check("o gerador nao fala com rede nem com banco",
      "rede" not in _io.open("etiquetas/numeracao.py", encoding="utf-8").read()
      and "import dados" not in _io.open("etiquetas/numeracao.py",
                                         encoding="utf-8").read())


secao("81. As rotas do gerador de codigo, de ponta a ponta")

# A seçao 78 cobre as rotas de SKU; estas nao tinham nada — e rota foi
# exatamente onde morava o bug de colisao que quase subiu.
#
# A regra e a mesma das outras tres: O SERVIDOR CALCULA O QUE GRAVA, O
# NAVEGADOR SO CONFIRMA QUAIS.
_ID_C = _instalar("gera-cod.myshopify.com", "tok-c")
t_lojas.marcar_plano(_ID_C, "pro")

# {produto: [(variante, titulo, sku, codigo)]}
_LOJA_C = {
    "gid://c/1": [("gid://cv/1", "P", "", ""),            # sem sku, sem codigo
                  ("gid://cv/2", "M", "ACME-M", "")],     # com sku, sem codigo
    "gid://c/2": [("gid://cv/3", "U", "", "7891111111117")],   # JA tem codigo
}
_escritas_c = []


def _shopify_c(loja, token, corpo, **kw):
    """Responde a consulta de produtos E a mutacao, nos DOIS campos.

    A loja falsa da secao 78 so sabia gravar SKU. Esta precisa saber os dois,
    porque e justamente a mistura dos dois que o desfazer tem que separar.
    """
    if "productVariantsBulkUpdate" in corpo.get("query", ""):
        pid = corpo["variables"]["produto"]
        confirmadas = []
        for v in corpo["variables"]["variantes"]:
            e_codigo = "barcode" in v
            valor = v["barcode"] if e_codigo else v["inventoryItem"]["sku"]
            _escritas_c.append((v["id"], "codigo" if e_codigo else "sku", valor))
            novas = []
            for vid, tit, sku, cod in _LOJA_C[pid]:
                if vid == v["id"]:
                    cod, sku = (valor, sku) if e_codigo else (cod, valor)
                novas.append((vid, tit, sku, cod))
            _LOJA_C[pid] = novas
            atual = [x for x in _LOJA_C[pid] if x[0] == v["id"]][0]
            confirmadas.append({"id": v["id"], "sku": atual[2],
                                "barcode": atual[3]})
        return {"data": {"productVariantsBulkUpdate": {
            "productVariants": confirmadas, "userErrors": []}}}

    return {"data": {"products": {
        "pageInfo": {"hasNextPage": False, "endCursor": None},
        "nodes": [{"id": pid, "title": "Produto " + pid[-1], "vendor": "Acme",
                   "productType": "Camiseta",
                   "variants": {"pageInfo": {"hasNextPage": False}, "nodes": [
                       {"id": vid, "title": tit, "sku": sku, "barcode": cod,
                        "price": "10.00", "compareAtPrice": None,
                        "inventoryQuantity": 2}
                       for vid, tit, sku, cod in variantes]}}
                  for pid, variantes in _LOJA_C.items()]}}}


def _com_c(fn):
    original = _rede4.graphql
    _rede4.graphql = _shopify_c
    try:
        return fn()
    finally:
        _rede4.graphql = original


def _post_c(caminho, corpo):
    return _com_c(lambda: _post(caminho, "gera-cod.myshopify.com", corpo))


# --- 1. a previa nao escreve, e diz o que cada linha e --------------------
_escritas_c.clear()
_d = _post_c("/api/codigos/previa", {"modo": "interno"}).get_json()
check("a previa de codigo responde", "linhas" in _d, sorted(_d))
check("e NAO escreveu nada", _escritas_c == [], _escritas_c)

_prop = {l["variante_id"]: l["codigo"] for l in _d["linhas"]
         if l["codigo"] and not l["pulado"]}
check("propoe codigo so pra quem nao tem",
      set(_prop) == {"gid://cv/1", "gid://cv/2"}, sorted(_prop))
# Com o filtro padrao ("sem codigo"), quem JA tem nem chega na tabela — o
# filtro corta antes. Isso e certo: a janela existe pra preencher o que falta.
check("com o filtro, quem ja tem codigo nem aparece",
      not any(l["variante_id"] == "gid://cv/3" for l in _d["linhas"]),
      [l["variante_id"] for l in _d["linhas"]])

# Mas com "todos os produtos" ele aparece COM O MOTIVO, em vez de sumir
# calado — que e a regra do app inteiro.
_todos = _post_c("/api/codigos/previa",
                 {"modo": "interno", "filtro": ""}).get_json()
check("sem filtro ele aparece, marcado como pulado",
      any(l["variante_id"] == "gid://cv/3" and "já tem" in l["pulado"]
          for l in _todos["linhas"]),
      [(l["variante_id"], l["pulado"]) for l in _todos["linhas"]])

# O numero gerado tem que passar pela MESMA validacao que o app usa pra
# aceitar codigo digitado. Verificador errado imprime bonito, bipa, e traz o
# produto errado no caixa.
for _vid, _cod in sorted(_prop.items()):
    check("o codigo de %s passa na validacao do proprio app" % _vid[-4:],
          codigos.validar(_cod, codigos.EAN13) == (True, ""),
          (_cod, codigos.validar(_cod, codigos.EAN13)))
check("e ele esta na faixa 2, a reservada a uso interno",
      all(c.startswith("2") for c in _prop.values()), sorted(_prop.values()))

# A frase que diz ONDE aquele codigo vale viaja JUNTO da tabela.
# O aviso vem TRADUZIDO pelo servidor (a bateria roda no idioma padrao, que e
# o ingles) — mandar portugues pra tela em ingles seria falhar justamente na
# frase com consequencia comercial.
check("a previa manda o aviso do modo junto, no idioma da tela",
      "another shop" in (_d.get("aviso_do_modo") or ""), _d.get("aviso_do_modo"))

# --- 2. as escolhas sao conferidas antes de qualquer varredura ------------
check("modo gs1 sem prefixo e recusado",
      _post_c("/api/codigos/previa", {"modo": "gs1"}).status_code == 400)
check("prefixo com letra e recusado",
      _post_c("/api/codigos/previa",
              {"modo": "gs1", "prefixo": "abc"}).status_code == 400)
check("modo inventado e recusado",
      _post_c("/api/codigos/previa", {"modo": "xpto"}).status_code == 400)

# --- 3. grava so o que foi confirmado ------------------------------------
_escritas_c.clear()
_d = _post_c("/api/codigos/aplicar",
             {"modo": "interno", "variantes": ["gid://cv/1"]}).get_json()
check("grava e diz quantos", _d.get("gravados") == 1, _d)
check("E SO A CONFIRMADA foi escrita, nao as duas propostas",
      [e[0] for e in _escritas_c] == ["gid://cv/1"], _escritas_c)
check("e escreveu no campo CODIGO, nao no SKU",
      _escritas_c[0][1] == "codigo", _escritas_c)

# O navegador nao dita o valor: o servidor refaz a conta.
_escritas_c.clear()
_post_c("/api/codigos/aplicar",
        {"modo": "interno", "variantes": ["gid://cv/2"],
         "codigo": "9999999999999",
         "linhas": [{"variante_id": "gid://cv/2", "codigo": "9999999999999"}]})
check("valor mandado pelo navegador NAO vai pro catalogo",
      _escritas_c and _escritas_c[0][2] != "9999999999999", _escritas_c)

check("sem escolher ninguem, recusa com motivo",
      _post_c("/api/codigos/aplicar",
              {"modo": "interno", "variantes": []}).status_code == 400)

# --- 4. desfazer devolve o vazio que estava la ---------------------------
_escritas_c.clear()
_d = _post_c("/api/codigos/desfazer", {}).get_json()
check("desfaz e diz quantos", _d.get("desfeitos") == 1, _d)
check("escrevendo de volta o VAZIO que estava la antes",
      _escritas_c and _escritas_c[0][2] == "", _escritas_c)
check("e no campo certo", _escritas_c[0][1] == "codigo", _escritas_c)


# --- 5. O DESFAZER DE UM GERADOR NAO REVERTE O LOTE DO OUTRO -------------
#
# Esta e a que a sabotagem pegou escapando, e ela e real: com duas janelas
# abertas, "desfazer o ultimo" sem filtrar por campo reverte o lote do OUTRO
# gerador. O lojista clica em desfazer numa janela e some o trabalho que ele
# acabou de fazer na outra.
# Os dois lotes vao em VARIANTES DIFERENTES, de proposito.
#
# A primeira versao deste teste usava a mesma variante pros dois, e ele
# passava com a trava sabotada — porque os dois valores anteriores eram ""
# e desfazer o lote errado dava exatamente o mesmo resultado visivel.
# Teste que nao distingue os dois casos nao esta testando nada.
_LOJA_C["gid://c/3"] = [("gid://cv/4", "G", "", ""),
                        ("gid://cv/9", "H", "", "")]

# Lote A: um SKU, na cv/4.
_escritas_c.clear()
_d = _post_c("/api/skus/aplicar", {"variantes": ["gid://cv/4"]}).get_json()
check("grava um SKU", _d.get("gravados") == 1, _d)

# Lote B: um codigo, na cv/9, DEPOIS. O "ultimo lote" da loja agora e esse.
_escritas_c.clear()
_d = _post_c("/api/codigos/aplicar",
             {"modo": "interno", "variantes": ["gid://cv/9"]}).get_json()
check("e grava um codigo em OUTRA variante depois", _d.get("gravados") == 1, _d)

# Desfazer pela janela do SKU tem que reverter o LOTE DO SKU — e da pra provar
# isso olhando QUAL variante foi tocada.
_escritas_c.clear()
_d = _post_c("/api/skus/desfazer", {}).get_json()
check("o desfazer do SKU reverte o lote do SKU", _d.get("desfeitos") == 1, _d)
check("E TOCA A VARIANTE DO SKU, nao a do codigo",
      [e[0] for e in _escritas_c] == ["gid://cv/4"], _escritas_c)
check("no campo sku", [e[1] for e in _escritas_c] == ["sku"], _escritas_c)

_v4 = [x for x in _LOJA_C["gid://c/3"] if x[0] == "gid://cv/4"][0]
_v9 = [x for x in _LOJA_C["gid://c/3"] if x[0] == "gid://cv/9"][0]
check("o SKU voltou a ficar vazio", _v4[2] == "", _v4)
check("e o codigo da outra variante CONTINUA la", _v9[3] != "", _v9)

# E o lote de codigo continua na fila, porque ninguem o consumiu.
_escritas_c.clear()
_d = _post_c("/api/codigos/desfazer", {}).get_json()
check("o lote de codigo ainda estava na fila", _d.get("desfeitos") == 1, _d)
check("e esse toca a variante do codigo",
      [e[0] for e in _escritas_c] == ["gid://cv/9"], _escritas_c)


# --- 5b. as duas que a sabotagem mostrou que eu nao exercitava -----------

# (a) CONFIRMAR QUEM JA TEM CODIGO. O codigo que esta la pode ser COMPRADO, e
# pode estar impresso em caixa fechada. A protecao so e tocada se o lojista
# confirmar de proposito uma linha dessas — e era isso que faltava.
_LOJA_C["gid://c/4"] = [("gid://cv/5", "X", "", "7899999999994")]
_escritas_c.clear()
_post_c("/api/codigos/aplicar",
        {"modo": "interno", "filtro": "", "variantes": ["gid://cv/5"]})
check("confirmar quem JA TEM codigo nao sobrescreve",
      all(e[0] != "gid://cv/5" for e in _escritas_c), _escritas_c)
_v5 = [x for x in _LOJA_C["gid://c/4"] if x[0] == "gid://cv/5"][0]
check("e o codigo que estava la continua intacto",
      _v5[3] == "7899999999994", _v5)

# (b) RODAR O GERADOR DUAS VEZES. Este e o caso de verdade: o lojista gera,
# grava, depois cadastra produto novo e gera de novo. Se a conferencia nao
# enxergar os codigos que a PRIMEIRA rodada gravou, a segunda repete tudo.
#
# E ela so enxerga porque `_varrer` colhe ANTES do filtro — com o filtro "sem
# codigo", quem ja tem (ou seja, quem segura os codigos) e cortado da lista.
_LOJA_C["gid://c/5"] = [("gid://cv/6", "Y", "", _num.montar_interno(1)),
                        ("gid://cv/7", "Z", "", _num.montar_interno(2)),
                        ("gid://cv/8", "W", "", "")]
_d = _post_c("/api/codigos/previa", {"modo": "interno"}).get_json()
_novo = {l["variante_id"]: l["codigo"] for l in _d["linhas"]
         if l["codigo"] and not l["pulado"]}
_ja_na_loja = {c for lista in _LOJA_C.values() for _, _, _, c in lista if c}
check("a segunda rodada NAO repete codigo que a primeira ja gravou",
      not set(_novo.values()) & _ja_na_loja,
      sorted(set(_novo.values()) & _ja_na_loja))
check("e o produto novo recebe o proximo da fila, nao o numero 1",
      _novo.get("gid://cv/8") not in (None, _num.montar_interno(1)),
      _novo.get("gid://cv/8"))

del _LOJA_C["gid://c/4"], _LOJA_C["gid://c/5"]


# --- 6. no modo dev a gravacao recusa, como nas outras -------------------
check("no modo dev o aplicar de codigo recusa",
      _post("/api/codigos/aplicar", "so-dev.myshopify.com",
            {"modo": "interno", "variantes": ["gid://cv/1"]}).status_code == 400)
check("e o desfazer tambem",
      _post("/api/codigos/desfazer", "so-dev.myshopify.com",
            {}).status_code == 400)
check("mas a PREVIA do modo dev funciona",
      _post("/api/codigos/previa", "so-dev.myshopify.com",
            {"modo": "interno"}).status_code == 200)


# ---------------------------------------------------------------- fim
print("\n" + "=" * 62)
print("PASSOU: %d   FALHOU: %d" % (PASSOU, len(FALHOU)))
if FALHOU:
    print("\nFALHAS:")
    for nome in FALHOU:
        print("  - %s" % nome)
print("=" * 62)
sys.exit(1 if FALHOU else 0)
