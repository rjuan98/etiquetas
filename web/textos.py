"""Todo texto que o lojista lê, nos dois idiomas. O único lugar.

## Por que fica em `web/` e não espalhado

O motor (`etiquetas/`) e o lado Shopify (`loja/`) **não sabem o que é idioma**.
Eles falam em identificador — `"titulo"`, `"pro"`, `"zebra_2x1"` — e quem
transforma isso em palavra é a borda web, que é a única que sabe quem está
lendo.

Se o `receitas.py` carregasse "Título do produto" em português, traduzir viraria
mexer no motor, e o motor tem arquivo-espelho justamente pra não mudar.

## Inglês é o padrão, e isso é decisão de mercado

As 565 avaliações que fizeram este projeto existir são em inglês, e é lá que
está o volume de lojas. Português existe porque o autor é brasileiro e o suporte
sai mais barato na própria língua — não porque o mercado peça.

Idioma desconhecido cai no inglês. É melhor um lojista alemão ler inglês do que
português.

## Como escrever aqui

Chave em português (é a língua de quem mantém), valor traduzido. Frase inteira,
nunca pedaço concatenado: "Plano " + nome quebra em idioma que inverte a ordem.
Use `%s` e formate no uso.
"""

PADRAO = "en"

TEXTOS = {
    # ------------------------------------------------------------ a tela
    # Nome do produto: não traduz, como "Google Docs" não traduz. É o mesmo nome
    # que vai na loja de apps e na fatura do lojista (ver `cobranca.NOME_DO_APP`).
    "app_titulo":          {"en": "Etik Barcode Labels",
                            "pt": "Etik Barcode Labels"},
    "carregando":          {"en": "loading…",            "pt": "carregando…"},
    "montando":            {"en": "building…",           "pt": "montando…"},
    "ver_planos":          {"en": "See plans",           "pt": "Ver planos"},
    "planos":              {"en": "Plans",               "pt": "Planos"},
    "fechar":              {"en": "Close",               "pt": "Fechar"},

    "produtos":            {"en": "Products",            "pt": "Produtos"},
    "buscar":              {"en": "Search",              "pt": "Buscar"},
    "buscar_dica":         {"en": "Search by name, SKU or barcode",
                            "pt": "Buscar por nome, SKU ou código"},
    "carregando_catalogo": {"en": "Loading your catalog…",
                            "pt": "Carregando o catálogo…"},
    "carregar_mais":       {"en": "Load more products",
                            "pt": "Carregar mais produtos"},
    "col_produto":         {"en": "Product",             "pt": "Produto"},
    "col_codigo":          {"en": "Barcode",             "pt": "Código"},
    "col_quantas":         {"en": "How many",            "pt": "Quantas"},
    "sem_codigo":          {"en": "no barcode",          "pt": "sem código"},
    "nenhum_produto":      {"en": "No products found.",  "pt": "Nenhum produto encontrado."},
    "escolher":            {"en": "Select %s",           "pt": "Escolher %s"},
    "quantas_de":          {"en": "How many labels of %s",
                            "pt": "Quantas etiquetas de %s"},

    "a_etiqueta":          {"en": "The label",           "pt": "A etiqueta"},
    "o_que_aparece":       {"en": "What shows up",       "pt": "O que aparece"},
    "formato_do_papel":    {"en": "Label stock",         "pt": "Formato do papel"},
    "por_folha":           {"en": "%d per sheet",        "pt": "%d por folha"},

    "preco_e_codigo":      {"en": "Price and barcode",   "pt": "Preço e código"},
    "simbolo":             {"en": "Symbol",              "pt": "Símbolo"},
    "posicao":             {"en": "Position",            "pt": "Posição"},
    "decimal":             {"en": "Decimal",             "pt": "Decimal"},
    "tipo_de_codigo":      {"en": "Barcode type",        "pt": "Tipo de código"},
    "rotulo_sku":          {"en": 'Write "SKU:" before the code',
                            "pt": 'Escrever "SKU:" antes do código'},

    "sai_torta":           {"en": "Is the label printing crooked?",
                            "pt": "A etiqueta está saindo torta?"},
    "regua_ajuda":         {"en": "Print the ruler at <strong>actual size "
                                  "(100%)</strong>, measure with a real ruler "
                                  "where the frame landed, and type the "
                                  "difference. Works with any printer.",
                            "pt": "Imprima a régua em <strong>tamanho real "
                                  "(100%)</strong>, meça com régua de verdade "
                                  "onde a moldura caiu, e escreva a diferença. "
                                  "Vale pra qualquer impressora."},
    "desvio_x":            {"en": "Shift horizontally (mm)",
                            "pt": "Desviar na horizontal (mm)"},
    "desvio_y":            {"en": "Shift vertically (mm)",
                            "pt": "Desviar na vertical (mm)"},
    "baixar_regua":        {"en": "Download the ruler",  "pt": "Baixar a régua"},

    "modelo":              {"en": "Template",            "pt": "Modelo"},
    "modelo_salvo":        {"en": "Saved template",      "pt": "Modelo salvo"},
    "novo_modelo":         {"en": "— New template —",    "pt": "— Novo modelo —"},
    "nome":                {"en": "Name",                "pt": "Nome"},
    "nome_dica":           {"en": "Shelf label",         "pt": "Etiqueta de prateleira"},
    "salvar":              {"en": "Save",                "pt": "Salvar"},
    "duplicar":            {"en": "Duplicate",           "pt": "Duplicar"},
    "apagar":              {"en": "Delete",              "pt": "Apagar"},
    "apagar_mesmo":        {"en": "Delete for real?",    "pt": "Apagar mesmo?"},
    "ainda_nao_salvo":     {"en": "Not saved yet.",      "pt": "Ainda não salvo."},
    "alteracao_nao_salva": {"en": "You have unsaved changes.",
                            "pt": "Tem alteração não salva."},
    "salvo":               {"en": "Saved.",              "pt": "Salvo."},
    "limite_de_modelos_aviso": {
        "en": "Your plan keeps %d template. Saving will ask for Pro.",
        "pt": "Seu plano guarda %d modelo. Salvar vai pedir o Pro."},

    "nenhum_escolhido":    {"en": "no product selected",
                            "pt": "nenhum produto escolhido"},
    "conta_escolhidos":    {"en": "%d product(s), %d label(s)",
                            "pt": "%d produto(s), %d etiqueta(s)"},
    "termica":             {"en": "Thermal printer (ZPL)",
                            "pt": "Impressora térmica (ZPL)"},
    "baixar_pdf":          {"en": "Download PDF",        "pt": "Baixar PDF"},
    "termica_e_do_pro":    {"en": "Thermal printing is part of the Pro plan",
                            "pt": "A impressora térmica faz parte do plano Pro"},

    # --------------------------------------------------------- mensagens
    "erro_servidor":       {"en": "I couldn't reach the server.",
                            "pt": "Não consegui falar com o servidor."},
    "erro_previa":         {"en": "Something went wrong building the preview.",
                            "pt": "Não consegui montar a prévia."},
    "erro_catalogo":       {"en": "I couldn't read your catalog.",
                            "pt": "Não consegui ler o catálogo."},
    "erro_arquivo":        {"en": "I couldn't generate the file.",
                            "pt": "Não consegui gerar o arquivo."},
    "erro_generico":       {"en": "Something went wrong. Try again.",
                            "pt": "Alguma coisa deu errado. Tente de novo."},
    "erro_abrir_modelo":   {"en": "I couldn't open that template.",
                            "pt": "Não consegui abrir o modelo."},
    "erro_salvar":         {"en": "I couldn't save.",    "pt": "Não consegui salvar."},
    "erro_duplicar":       {"en": "I couldn't duplicate it.",
                            "pt": "Não consegui duplicar."},
    "erro_apagar":         {"en": "I couldn't delete it.",
                            "pt": "Não consegui apagar."},
    "erro_planos":         {"en": "I couldn't load the plans.",
                            "pt": "Não consegui ler os planos."},
    "erro_assinar":        {"en": "I couldn't start the subscription.",
                            "pt": "Não consegui iniciar a assinatura."},
    "nao_coube":           {"en": "Didn't fit on this label: %s. Pick a bigger "
                                  "stock or turn off a field.",
                            "pt": "Não coube nesta etiqueta: %s. Escolha um "
                                  "papel maior ou desligue algum campo."},
    "variantes_cortadas":  {"en": "These products have more than 100 variants "
                                  "and only the first 100 showed up: %s.",
                            "pt": "Estes produtos têm mais de 100 variações e só "
                                  "as 100 primeiras apareceram: %s."},
    "abrir_pelo_admin":    {"en": "Open the app from your Shopify admin.",
                            "pt": "Abra o app pelo painel do Shopify."},
    "sessao_expirada":     {"en": "Session expired. Reload the page.",
                            "pt": "Sessão expirada. Recarregue a página."},
    "nao_instalado":       {"en": "This app isn't installed on this store.",
                            "pt": "Este app não está instalado nesta loja."},
    "desinstalado":        {"en": "The app was uninstalled from this store. "
                                  "Install it again.",
                            "pt": "O app foi desinstalado desta loja. Instale de novo."},
    "fora_do_admin":       {"en": "This app runs inside your Shopify admin. "
                                  "Open it from your store.",
                            "pt": "Este app funciona dentro do painel do Shopify. "
                                  "Abra pelo admin da sua loja."},
    "instalar_aqui":       {"en": "Click here to install the app.",
                            "pt": "Clique aqui pra instalar o app."},
    "abrindo_autorizacao": {"en": "Opening the authorization screen…",
                            "pt": "Abrindo a tela de autorização…"},
    "clique_se_nao_abrir": {"en": "Click here if it doesn't open by itself.",
                            "pt": "Clique aqui se não abrir sozinho."},

    # ---------------------------------------------------------- cobrança
    "plano_com_limite":    {"en": "%s plan — %d of %d labels this month",
                            "pt": "Plano %s — %d de %d etiquetas neste mês"},
    "plano_sem_limite":    {"en": "%s plan",             "pt": "Plano %s"},
    "seu_plano":           {"en": "your plan",           "pt": "seu plano"},
    "gratis_minusculo":    {"en": "free",                "pt": "grátis"},
    "por_mes":             {"en": "US$ %s/mo",           "pt": "US$ %s/mês"},
    "abrindo":             {"en": "opening…",            "pt": "abrindo…"},
    "teste_gratis":        {"en": "%d days free to try. Billing goes on the "
                                  "invoice you already pay Shopify — no card, "
                                  "no signup.",
                            "pt": "%d dias grátis pra testar. A cobrança entra na "
                                  "fatura que você já paga à Shopify — sem cartão, "
                                  "sem cadastro."},

    "plano_gratis_nome":   {"en": "Free",                "pt": "Grátis"},
    "plano_pro_nome":      {"en": "Pro",                 "pt": "Pro"},
    "plano_gratis_resumo": {"en": "1 template, 100 labels a month, sheet labels",
                            "pt": "1 modelo, 100 etiquetas por mês, folha adesiva"},
    "plano_pro_resumo":    {"en": "Unlimited labels and templates. "
                                  "Thermal printing included.",
                            "pt": "Etiquetas e modelos ilimitados. "
                                  "Inclui impressora térmica."},

    "erro_limite_mes":     {"en": "You've used %d of the %d labels in your "
                                  "monthly plan. Go Pro for no limit.",
                            "pt": "Você já gerou %d das %d etiquetas do mês. "
                                  "Assine o Pro pra não ter limite."},
    "erro_limite_modelos": {"en": "Your plan allows %d template(s). "
                                  "Go Pro for unlimited templates.",
                            "pt": "Seu plano permite %d modelo(s). "
                                  "Assine o Pro pra ter modelos ilimitados."},
    "erro_motor_bloqueado": {"en": "Thermal printing is part of the Pro plan.",
                             "pt": "Impressora térmica faz parte do plano Pro."},
    "erro_lote_grande":    {"en": "That's %d labels at once. The batch limit is "
                                  "%d — split it up.",
                            "pt": "São %d etiquetas de uma vez. O limite por lote "
                                  "é %d — divida em partes."},
    "erro_sem_itens":      {"en": "Nothing selected to print.",
                            "pt": "Nenhum item pra imprimir."},
    "erro_modelo_sumido":  {"en": "Template not found.",
                            "pt": "Modelo não encontrado."},
    "erro_escolha_modelo": {"en": "Pick a label template.",
                            "pt": "Escolha um modelo de etiqueta."},
    "erro_modelo_invalido": {"en": "Invalid template: %s",
                             "pt": "Modelo inválido: %s"},
    "erro_modelo_problemas": {"en": "There are problems with this template.",
                              "pt": "Modelo com problemas."},
    "erro_motor":          {"en": "Printer type %r doesn't exist.",
                            "pt": "Motor %r não existe."},
    "erro_graphql":        {"en": "Shopify refused the query.",
                            "pt": "O Shopify recusou a consulta."},
    "erro_assinatura_recusada": {"en": "Shopify refused the subscription.",
                                 "pt": "O Shopify recusou a assinatura."},
    "erro_dominio":        {"en": "Invalid store domain.",
                            "pt": "Domínio de loja inválido."},
    "erro_instalacao":     {"en": "Installation refused.",
                            "pt": "Instalação recusada."},
    "erro_instalacao_rede": {"en": "I couldn't finish the installation: %s",
                             "pt": "Não consegui concluir a instalação: %s"},
    "nao_autorizado":      {"en": "Not authorized.",     "pt": "Não autorizado."},

    # ---------------------------------- o produto de exemplo da prévia
    # Aparece antes de o lojista escolher qualquer coisa. Etiqueta em branco na
    # primeira tela parece app quebrado; um exemplo mostra o que vai sair.
    "exemplo_titulo":      {"en": "White Porcelain Mug 300ml",
                            "pt": "Caneca de Porcelana Branca 300ml"},
    "exemplo_variante":    {"en": "White / 300ml",       "pt": "Branca / 300ml"},
    "exemplo_fornecedor":  {"en": "Real Ceramics",       "pt": "Cerâmica Real"},
    "exemplo_moeda":       {"en": "$",                   "pt": "R$"},

    # ------------------------------------------------- campos da etiqueta
    "campo_titulo":        {"en": "Product title",       "pt": "Título do produto"},
    "campo_variante":      {"en": "Variant (color, size)",
                            "pt": "Variação (cor, tamanho)"},
    "campo_fornecedor":    {"en": "Vendor",              "pt": "Fornecedor"},
    "campo_sku":           {"en": "SKU",                 "pt": "SKU"},
    "campo_preco":         {"en": "Price",               "pt": "Preço"},
    "campo_codigo_barras": {"en": "Barcode",             "pt": "Código de barras"},

    # ---------------------------------------------- formatos (só o sufixo)
    "formato_varejo":      {"en": "retail",              "pt": "varejo"},
    "formato_envio":       {"en": "shipping",            "pt": "envio"},
    "formato_multiuso":    {"en": "multipurpose",        "pt": "multiuso"},
    "formato_endereco":    {"en": "address",             "pt": "endereço"},
    "formato_joia":        {"en": "jewelry, 2 flaps",    "pt": "joia, 2 abas"},
    "formato_por_folha":   {"en": "%s per sheet",        "pt": "%s por folha"},
    "formato_polegada":    {"en": "in",                  "pt": "pol"},

    # ------------------------------------------------------- privacidade
    "privacidade_dados":   {"en": "This app doesn't collect or store customer "
                                  "data. It only reads products and variants, "
                                  "to build labels.",
                            "pt": "Este app não coleta nem guarda dados de "
                                  "clientes. Ele lê apenas produtos e variantes, "
                                  "pra montar etiquetas."},
    "privacidade_apagado": {"en": "There was nothing to erase: this app stores "
                                  "no customer data.",
                            "pt": "Não havia nada pra apagar: este app não guarda "
                                  "dados de clientes."},
}


def idioma_de(bruto: str) -> str:
    """Qual idioma servir, a partir do que o Shopify (ou o navegador) mandou.

    O Shopify põe `?locale=pt-BR` na URL quando abre o app embutido. Se não vier,
    o `Accept-Language` do navegador serve. Desconhecido cai no inglês.

    Só o prefixo importa: `pt-BR` e `pt-PT` recebem o mesmo texto. Separar as
    duas variantes seria manter duas tabelas quase idênticas por causa de meia
    dúzia de palavras.
    """
    if not bruto:
        return PADRAO
    prefixo = str(bruto).strip().lower().replace("_", "-").split("-")[0]
    return prefixo if any(prefixo in v for v in TEXTOS.values()) else PADRAO


def t(chave: str, idioma: str = PADRAO) -> str:
    """O texto. Chave que não existe volta como a própria chave, entre colchetes.

    Devolver a chave em vez de estourar é de propósito: um texto faltando vira
    uma tela feia, e uma exceção vira uma tela em branco. Feio dá pra ver e
    consertar; branco o lojista só reporta como "não abre".
    """
    linha = TEXTOS.get(chave)
    if not linha:
        return "[%s]" % chave
    return linha.get(idioma) or linha.get(PADRAO) or "[%s]" % chave


def tabela(idioma: str = PADRAO) -> dict:
    """Todos os textos num dicionário, pra mandar de uma vez pra tela."""
    return {chave: t(chave, idioma) for chave in TEXTOS}
