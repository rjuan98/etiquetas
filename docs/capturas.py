"""Gera as capturas de tela da loja de apps, do app rodando de verdade.

    python servidor.py          (numa janela, com MODO_DEV=1)
    python docs/capturas.py     (na outra)

## Por que isto é um script e não eu clicando

Captura tirada na mão não se refaz. Quando a tela muda — e ela vai mudar — alguém
precisa lembrar da sequência exata de cliques que produziu cada imagem, e não
lembra. As capturas então envelhecem, e a loja de apps passa a mostrar um app que
não existe mais.

Aqui cada imagem é uma cena declarada em `web/dev.py`, e refazer as quatro é
rodar um comando.

## E por que são do app de verdade

Poderia ser mais bonito desenhar as telas num programa de imagem. Seria mentira:
o lojista instala esperando o que viu, e a distância entre a captura e o produto
é exatamente a reclamação que originou este projeto. O que está nas imagens é o
que sai da tela, com o catálogo de demonstração.

## O navegador

Usa o Chrome que já está instalado, em modo sem janela. Sem dependência nova, e
é o mesmo motor que o lojista usa pra ver o app.
"""
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

LARGURA, ALTURA = 1600, 900        # o que a loja de apps pede
ENDERECO = "http://localhost:5000"

# Cada captura: (arquivo, cena em dev.py, o que ela conta)
CAPTURAS = [
    ("01-principal.png", "principal",
     "Escolher produtos e ver a etiqueta antes de imprimir"),
    ("02-campos.png", "campos",
     "Ligar e desligar cada campo, e trocar o formato do papel"),
    ("03-calibracao.png", "calibracao",
     "Corrigir impressora que sai torta, em milímetro"),
    ("04-planos.png", "planos",
     "Os planos, cobrados na fatura que o lojista já paga"),
]

CHROMES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium",
]


def achar_navegador() -> str:
    for c in CHROMES:
        if os.path.exists(c):
            return c
    raise SystemExit("Não achei Chrome, Brave nem Edge. Instale um deles.")


def servidor_de_pe() -> bool:
    try:
        with urllib.request.urlopen(ENDERECO + "/saude", timeout=4) as r:
            return json.loads(r.read()).get("ok") is True
    except (urllib.error.URLError, ValueError, OSError):
        return False


def capturar(navegador: str, destino: str, cena: str):
    """Uma captura. Espera a cena terminar em vez de chutar um tempo.

    O `--virtual-time-budget` faz o Chrome adiantar os temporizadores da página e
    só então fotografar. Sem isso a captura sai no meio do carregamento — com a
    prévia ainda escrita "building…", que é justamente a tela que não pode ir
    pra loja de apps.
    """
    url = "%s/dev/?locale=en-US&cena=%s" % (ENDERECO, cena)
    dom = destino + ".html"
    # O `--dump-dom` sai pela saída padrão, então ela vai pro arquivo e só o
    # erro é capturado. É por esse HTML que a gente confere se a cena montou,
    # em vez de confiar que a imagem existir significa que deu certo.
    with open(dom, "wb") as saida:
        subprocess.run([
            navegador,
            "--headless=new",
            # O idioma do NAVEGADOR, nao so o da pagina. Sem isto os campos
            # numericos saiam "1,5" na captura em ingles, porque quem formata
            # <input type=number> e o navegador, nao o app.
            "--lang=en-US",
            "--disable-gpu",
            "--hide-scrollbars",
            "--force-device-scale-factor=1",
            "--window-size=%d,%d" % (LARGURA, ALTURA),
            "--virtual-time-budget=9000",
            "--screenshot=" + destino,
            "--dump-dom",
            url,
        ], stdout=saida, stderr=subprocess.DEVNULL, timeout=90)
    return dom


def principal():
    aqui = os.path.dirname(os.path.abspath(__file__))
    pasta = os.path.join(aqui, "capturas")
    os.makedirs(pasta, exist_ok=True)

    if not servidor_de_pe():
        raise SystemExit(
            "O servidor não está no ar em %s.\n"
            "Suba ele numa outra janela: python servidor.py" % ENDERECO)

    navegador = achar_navegador()
    print("navegador: %s\n" % navegador)

    problemas = []
    for arquivo, cena, conta in CAPTURAS:
        destino = os.path.join(pasta, arquivo)
        if os.path.exists(destino):
            os.remove(destino)
        inicio = time.time()
        dom = capturar(navegador, destino, cena)

        # A cena precisa DIZER que montou. Sem esta conferência, uma cena que
        # estourou no meio gerava uma imagem perfeitamente válida da tela errada,
        # e o script relatava sucesso — foi exatamente o que aconteceu.
        html = io.open(dom, encoding="utf-8", errors="replace").read()
        os.remove(dom)
        # Só a tag <html> vale: o nome do atributo também aparece dentro do
        # script que o escreve, e procurar no documento inteiro dava um falso
        # positivo em toda captura.
        abertura = re.search(r"<html[^>]*>", html)
        abertura = abertura.group(0) if abertura else ""
        erro = re.search(r'data-cena-erro="([^"]*)"', abertura)
        if erro:
            problemas.append("%s: a cena estourou — %s" % (arquivo, erro.group(1)[:90]))
            print("  XX  %-20s CENA ESTOUROU: %s" % (arquivo, erro.group(1)[:70]))
            continue
        if "data-cena-pronta" not in abertura:
            problemas.append("%s: a cena não terminou de montar" % arquivo)
            print("  XX  %-20s CENA NAO MONTOU" % arquivo)
            continue

        if not os.path.exists(destino):
            problemas.append("%s não foi gerada" % arquivo)
            print("  XX  %-20s NAO GEROU" % arquivo)
            continue

        try:
            from PIL import Image
            with Image.open(destino) as img:
                medida = img.size
                # Imagem quase toda de uma cor só é sinal de captura tirada antes
                # de a página montar. Vale conferir, porque o arquivo existe e
                # parece sucesso.
                cores = len(set(img.convert("L").getdata()))
        except ImportError:
            medida, cores = None, None

        if medida and medida != (LARGURA, ALTURA):
            problemas.append("%s saiu %sx%s" % (arquivo, *medida))
        if cores is not None and cores < 30:
            problemas.append("%s parece vazia (%d tons)" % (arquivo, cores))

        print("  ok  %-20s %s  %.1fs  — %s"
              % (arquivo, medida or "?", time.time() - inicio, conta))

    print()
    if problemas:
        print("PROBLEMAS:")
        for p in problemas:
            print("  - %s" % p)
        return 1
    print("%d capturas em %s" % (len(CAPTURAS), pasta))
    return 0


if __name__ == "__main__":
    sys.exit(principal())
