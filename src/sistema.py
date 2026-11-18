import json
import os
import time

try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import requests
except ImportError:
    requests = None

TELEGRAM_API = "https://api.telegram.org/bot"

MODELO_IA = "claude-haiku-5-5"

INSTRUCAO_IA = """Você é o Citizen Assist AI, um assistente informativo e NÃO oficial que orienta cidadãos \
brasileiros sobre golpes digitais, direitos do consumidor e documentos, com linguagem simples.

Regras:
- Responda somente com base nas orientações da BASE VERIFICADA abaixo. Não use outro conhecimento.
- Sempre termine a resposta com a linha "Fonte: <referencia> - <link>" da orientação usada.
- Se a pergunta não estiver coberta pela base, diga que não tem uma orientação verificada sobre isso, \
sugira os temas disponíveis e recomende procurar o canal oficial. Nunca invente prazos, valores ou procedimentos.
- Se a pergunta for vaga, pergunte qual situação a pessoa está vivendo, citando os assuntos possíveis.
- Quando a orientação tiver "confirmar": true, avise que regras e prazos podem mudar e devem ser confirmados no canal oficial.
- Nunca peça CPF, senhas, telefone, endereço ou outros dados pessoais.
- Nunca diga que é um canal oficial de órgão público, banco ou empresa.
- Responda em português do Brasil, em até 6 frases curtas, sem tabelas.

BASE VERIFICADA (JSON):
"""

ARQUIVO_BASE = "data/base_conhecimento.json"
ARQUIVO_TESTES = "data/perguntas_teste.json"
ARQUIVO_RESULTADOS = "data/resultados_testes.csv"
ARQUIVO_COMPARACAO = "data/comparacao_modelos.csv"
ARQUIVO_AVALIACOES = "data/avaliacoes_uso.csv"

CAMPOS_OBRIGATORIOS = ["id", "tema", "titulo", "palavras_chave", "orientacao",
                       "referencia", "link", "data_verificacao"]

PONTUACAO_MINIMA = 2

ACENTOS = {"á": "a", "à": "a", "â": "a", "ã": "a", "é": "e", "ê": "e", "í": "i",
           "ó": "o", "ô": "o", "õ": "o", "ú": "u", "ü": "u", "ç": "c"}

PALAVRAS_VAZIAS = ["que", "como", "para", "por", "com", "uma", "uns", "umas", "dos", "das",
                   "nos", "nas", "meu", "minha", "meus", "minhas", "sobre", "qual", "quais",
                   "quando", "onde", "ser", "foi", "tem", "ter", "fazer", "faco", "posso",
                   "pode", "preciso", "quero", "isso", "esse", "essa", "este", "esta", "aos",
                   "mais", "muito", "nao", "sim", "seu", "sua", "voce", "devo", "agora",
                   "dia", "algo", "alguem", "ele", "ela", "eles", "elas", "entao", "pra",
                   "pelo", "pela", "acontece", "fiz", "estou", "sei", "saber"]

INSTRUCOES = {
    "A": {
        "nome": "Modelo A - Resposta direta",
        "papel": "Responder a pergunta com a orientação encontrada.",
        "formato": "Orientação em um parágrafo seguida do nome da fonte.",
        "regras": "Usar somente a base de conhecimento."
    },
    "B": {
        "nome": "Modelo B - Assistente cidadão estruturado",
        "papel": "Você é o Citizen Assist AI, um assistente informativo e não oficial "
                 "que orienta cidadãos com linguagem simples.",
        "formato": "Assunto, o que fazer, fonte com link e data de verificação, "
                   "avisos e próximos assuntos.",
        "regras": "Usar somente a base verificada, sempre citar a fonte, avisar quando for "
                  "preciso confirmar no canal oficial, nunca inventar orientação e nunca "
                  "pedir dados pessoais."
    }
}

AVISO_NAO_OFICIAL = ("O Citizen Assist AI é um projeto acadêmico informativo e não é canal "
                     "oficial de nenhum órgão público ou empresa.")

margem = " " * 4


def normalizar(texto):
    texto = texto.lower()
    limpo = ""
    for letra in texto:
        letra = ACENTOS.get(letra, letra)
        if letra.isalnum():
            limpo += letra
        else:
            limpo += " "
    return limpo


def radical(palavra):
    if palavra.endswith("oes") or palavra.endswith("aes"):
        return palavra[:-3] + "ao"
    if len(palavra) > 4 and palavra.endswith("s"):
        return palavra[:-1]
    return palavra


def extrair_palavras(texto):
    palavras = []
    for palavra in normalizar(texto).split():
        if len(palavra) > 2 and palavra not in PALAVRAS_VAZIAS:
            palavra = radical(palavra)
            if palavra not in palavras:
                palavras.append(palavra)
    return palavras


def carregar_base():
    try:
        with open(ARQUIVO_BASE, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
    except FileNotFoundError:
        print(f"ERRO: arquivo {ARQUIVO_BASE} não encontrado. Execute a partir da pasta do projeto.")
        return []
    except json.JSONDecodeError:
        print(f"ERRO: o arquivo {ARQUIVO_BASE} está vazio ou com formato JSON inválido.")
        return []

    if type(dados) != list or len(dados) == 0:
        print("ERRO: a base de conhecimento não possui orientações.")
        return []

    base = []
    ids = []
    for posicao, registro in enumerate(dados, start=1):
        if type(registro) != dict:
            print(f"Aviso: registro {posicao} ignorado (formato inválido).")
            continue
        faltando = []
        for campo in CAMPOS_OBRIGATORIOS:
            if campo not in registro or registro[campo] == "" or registro[campo] == []:
                faltando.append(campo)
        if len(faltando) > 0:
            print(f"Aviso: registro {posicao} ignorado, campos ausentes: {', '.join(faltando)}.")
            continue
        if registro["id"] in ids:
            print(f"Aviso: registro {registro['id']} ignorado (identificador repetido).")
            continue
        ids.append(registro["id"])
        base.append(registro)

    for registro in base:
        validos = []
        for codigo in registro.get("relacionados", []):
            if codigo in ids:
                validos.append(codigo)
        registro["relacionados"] = validos

    return base


def montar_indice(base):
    indice = {}
    for registro in base:
        indice[registro["id"]] = registro
    return indice


def montar_temas(base):
    temas = {}
    for registro in base:
        if registro["tema"] not in temas:
            temas[registro["tema"]] = []
        temas[registro["tema"]].append(registro)
    return temas


def pontuar(palavras_usuario, registro):
    chaves = []
    for chave in registro["palavras_chave"]:
        for palavra in extrair_palavras(chave):
            if palavra not in chaves:
                chaves.append(palavra)
    texto_pergunta = extrair_palavras(registro.get("pergunta", "") + " " + registro["titulo"])

    pontos = 0
    for palavra in palavras_usuario:
        if palavra in chaves:
            pontos += 2
        elif palavra in texto_pergunta:
            pontos += 1
    return pontos


def buscar(pergunta, base):
    palavras = extrair_palavras(pergunta)
    if pergunta.strip() == "":
        return "vazia", []
    if len(palavras) == 0:
        return "sem_resposta", []

    maior = 0
    pontuados = []
    for registro in base:
        pontos = pontuar(palavras, registro)
        pontuados.append([pontos, registro])
        if pontos > maior:
            maior = pontos

    if maior < PONTUACAO_MINIMA:
        return "sem_resposta", []

    empatados = []
    for pontos, registro in pontuados:
        if pontos == maior:
            empatados.append(registro)

    if len(empatados) > 1:
        return "ambigua", empatados
    return "ok", empatados


def formatar_modelo_a(registro):
    return f"{registro['orientacao']}\nFonte: {registro['referencia']}"


def formatar_modelo_b(registro):
    texto = f"Assunto: {registro['tema']} > {registro['titulo']}\n"
    texto += f"O que fazer: {registro['orientacao']}\n"
    texto += f"Fonte: {registro['referencia']} - {registro['link']}\n"
    texto += f"Informação verificada em: {registro['data_verificacao']}\n"
    if registro.get("confirmar", False):
        texto += "Atenção: regras e prazos podem mudar. Confirme no canal oficial antes de agir.\n"
    texto += AVISO_NAO_OFICIAL
    return texto


def formatar(registro, modelo):
    if modelo == "A":
        return formatar_modelo_a(registro)
    return formatar_modelo_b(registro)


def linha():
    print("-" * 70)


def ler_opcao(mensagem, quantidade):
    escolha = input(mensagem).strip()
    if escolha == "":
        return 0
    if not escolha.isdigit() or int(escolha) < 1 or int(escolha) > quantidade:
        print("Opção inexistente. Digite um dos números da lista.")
        return -1
    return int(escolha)


def mostrar_resposta(registro, indice, modelo):
    while True:
        linha()
        print(formatar(registro, modelo))
        linha()
        relacionados = registro["relacionados"]
        if len(relacionados) == 0:
            return
        print("Assuntos relacionados para continuar a consulta:")
        for numero, codigo in enumerate(relacionados, start=1):
            print(f"{margem}{numero} - {indice[codigo]['titulo']}")
        escolha = -1
        while escolha == -1:
            escolha = ler_opcao("Digite o número do assunto ou Enter para voltar ao menu: ",
                                len(relacionados))
        if escolha == 0:
            return
        registro = indice[relacionados[escolha - 1]]


def texto_sem_resposta(temas):
    texto = "Não encontrei uma orientação confiável na base para essa pergunta.\n"
    texto += "Prefiro não inventar uma resposta. Você pode:\n"
    texto += (f"{margem}- usar palavras como: pix, golpe, boleto, whatsapp, garantia, "
              f"arrependimento, cobrança, documento, boletim de ocorrência;\n")
    texto += f"{margem}- escolher um dos temas disponíveis: {', '.join(temas.keys())};\n"
    texto += f"{margem}- procurar diretamente o canal oficial do órgão ou da empresa."
    return texto


def parece_dado_pessoal(texto):
    digitos = 0
    for letra in texto:
        if letra.isdigit():
            digitos += 1
    return digitos >= 8 or "@" in texto


def consultar_pergunta(base, indice, temas, modelo):
    pergunta = input("Digite sua pergunta: ")
    if parece_dado_pessoal(pergunta):
        print("Por segurança, não digite CPF, telefone, e-mail ou outros dados pessoais.")
        print("Reescreva a pergunta sem essas informações.")
        return

    inicio = time.perf_counter()
    situacao, encontrados = buscar(pergunta, base)
    tempo = (time.perf_counter() - inicio) * 1000

    if situacao == "vazia":
        print("Você não digitou nenhuma pergunta. Tente, por exemplo: 'caí num golpe do pix'.")
    elif situacao == "sem_resposta":
        print(texto_sem_resposta(temas))
    elif situacao == "ambigua":
        print("Sua pergunta combina com mais de um assunto. Qual deles você procura?")
        for numero, registro in enumerate(encontrados, start=1):
            print(f"{margem}{numero} - {registro['titulo']}")
        escolha = ler_opcao("Digite o número do assunto ou Enter para voltar: ", len(encontrados))
        if escolha > 0:
            mostrar_resposta(encontrados[escolha - 1], indice, modelo)
    else:
        mostrar_resposta(encontrados[0], indice, modelo)
    print(f"(tempo de busca: {tempo:.2f} ms)")


def consultar_tema(indice, temas, modelo):
    nomes = list(temas.keys())
    print("Temas disponíveis:")
    for numero, nome in enumerate(nomes, start=1):
        print(f"{margem}{numero} - {nome} ({len(temas[nome])} orientações)")
    escolha = ler_opcao("Escolha o tema ou Enter para voltar: ", len(nomes))
    if escolha <= 0:
        return
    registros = temas[nomes[escolha - 1]]
    print(f"Assuntos em {nomes[escolha - 1]}:")
    for numero, registro in enumerate(registros, start=1):
        print(f"{margem}{numero} - {registro['titulo']}")
    escolha = ler_opcao("Escolha o assunto ou Enter para voltar: ", len(registros))
    if escolha > 0:
        mostrar_resposta(registros[escolha - 1], indice, modelo)


def carregar_perguntas_teste():
    try:
        with open(ARQUIVO_TESTES, "r", encoding="utf-8") as arquivo:
            return json.load(arquivo)
    except FileNotFoundError:
        print(f"ERRO: arquivo {ARQUIVO_TESTES} não encontrado.")
    except json.JSONDecodeError:
        print(f"ERRO: o arquivo {ARQUIVO_TESTES} está vazio ou inválido.")
    return []


def executar_testes(base):
    perguntas = carregar_perguntas_teste()
    if len(perguntas) == 0:
        return

    resultados = []
    acertos = 0
    tempos = []
    por_tipo = {}

    for teste in perguntas:
        inicio = time.perf_counter()
        situacao, encontrados = buscar(teste["pergunta"], base)
        tempo = (time.perf_counter() - inicio) * 1000
        tempos.append(tempo)

        if situacao == "ok":
            obtido = encontrados[0]["id"]
        else:
            obtido = situacao.upper()

        acerto = obtido == teste["esperado"]
        if acerto:
            acertos += 1

        tipo = teste["tipo"]
        if tipo not in por_tipo:
            por_tipo[tipo] = [0, 0]
        por_tipo[tipo][1] += 1
        if acerto:
            por_tipo[tipo][0] += 1

        resultados.append([teste["id"], tipo, teste["pergunta"], teste["esperado"], obtido,
                           "acerto" if acerto else "erro", f"{tempo:.3f}"])

    print(f"{'ID':<5}{'TIPO':<14}{'ESPERADO':<14}{'OBTIDO':<14}{'RESULTADO':<10}{'TEMPO(ms)':>10}")
    for r in resultados:
        print(f"{r[0]:<5}{r[1]:<14}{r[3]:<14}{r[4]:<14}{r[5]:<10}{r[6]:>10}")

    total = len(resultados)
    taxa = acertos / total * 100
    media = sum(tempos) / len(tempos)
    linha()
    print(f"Perguntas testadas: {total}")
    print(f"Respostas corretas: {acertos}")
    print(f"Taxa de acerto: {taxa:.1f}%")
    print(f"Tempo médio de consulta: {media:.3f} ms (máximo {max(tempos):.3f} ms)")
    print("Taxa de acerto por tipo de pergunta:")
    for tipo in por_tipo:
        certos, quantidade = por_tipo[tipo]
        print(f"{margem}{tipo:<14}{certos}/{quantidade} = {certos / quantidade * 100:.1f}%")

    try:
        with open(ARQUIVO_RESULTADOS, "w", encoding="utf-8") as arquivo:
            arquivo.write("id;tipo;pergunta;esperado;obtido;resultado;tempo_ms\n")
            for r in resultados:
                arquivo.write(";".join(r) + "\n")
            arquivo.write(f"TOTAL;;;;{acertos}/{total};{taxa:.1f}%;{media:.3f}\n")
        print(f"Resultados salvos em {ARQUIVO_RESULTADOS}")
    except OSError:
        print("Não foi possível salvar o arquivo de resultados.")

    comparar_modelos(base)
    mostrar_avaliacoes()


def avaliar_resposta(texto):
    criterios = {
        "cita a fonte": "Fonte:" in texto,
        "traz link verificável": "http" in texto,
        "informa data de verificação": "verificada em" in texto,
        "identifica o assunto": "Assunto:" in texto,
        "avisa que não é oficial": "não é canal oficial" in texto,
    }
    return criterios


def comparar_modelos(base):
    linha()
    print("Comparação dos modelos de instrução de resposta (todas as orientações da base)")
    nomes_criterios = list(avaliar_resposta("").keys())
    resumo = {}
    for modelo in ["A", "B"]:
        contagem = {}
        for criterio in nomes_criterios:
            contagem[criterio] = 0
        palavras = 0
        for registro in base:
            texto = formatar(registro, modelo)
            palavras += len(texto.split())
            criterios = avaliar_resposta(texto)
            for criterio in criterios:
                if criterios[criterio]:
                    contagem[criterio] += 1
        resumo[modelo] = [contagem, palavras / len(base)]

    print(f"{'CRITÉRIO':<32}{'MODELO A':>12}{'MODELO B':>12}")
    for criterio in nomes_criterios:
        a = resumo["A"][0][criterio] / len(base) * 100
        b = resumo["B"][0][criterio] / len(base) * 100
        print(f"{criterio:<32}{a:>11.0f}%{b:>11.0f}%")
    print(f"{'média de palavras por resposta':<32}{resumo['A'][1]:>12.1f}{resumo['B'][1]:>12.1f}")

    try:
        with open(ARQUIVO_COMPARACAO, "w", encoding="utf-8") as arquivo:
            arquivo.write("criterio;modelo_a_pct;modelo_b_pct\n")
            for criterio in nomes_criterios:
                a = resumo["A"][0][criterio] / len(base) * 100
                b = resumo["B"][0][criterio] / len(base) * 100
                arquivo.write(f"{criterio};{a:.0f};{b:.0f}\n")
            arquivo.write(f"media_palavras;{resumo['A'][1]:.1f};{resumo['B'][1]:.1f}\n")
        print(f"Comparação salva em {ARQUIVO_COMPARACAO}")
    except OSError:
        print("Não foi possível salvar o arquivo de comparação.")


def avaliar_uso():
    print("Avaliação de facilidade de uso (não informe nome ou dados pessoais).")
    nota = input("De 1 (muito difícil) a 5 (muito fácil), qual nota você dá? ").strip()
    if nota not in ["1", "2", "3", "4", "5"]:
        print("Nota inválida. Digite um número de 1 a 5.")
        return
    dificuldade = input("Teve alguma dificuldade? (Enter para pular): ").strip()
    dificuldade = dificuldade.replace(";", ",")
    if parece_dado_pessoal(dificuldade):
        dificuldade = "(comentário removido por conter possível dado pessoal)"
    try:
        with open(ARQUIVO_AVALIACOES, "a", encoding="utf-8") as arquivo:
            arquivo.write(f"{nota};{dificuldade}\n")
        print("Obrigado! Avaliação registrada.")
    except OSError:
        print("Não foi possível registrar a avaliação.")


def mostrar_avaliacoes():
    linha()
    notas = []
    try:
        with open(ARQUIVO_AVALIACOES, "r", encoding="utf-8") as arquivo:
            for registro in arquivo.readlines():
                partes = registro.strip().split(";")
                if len(partes) >= 1 and partes[0].isdigit():
                    notas.append(int(partes[0]))
    except FileNotFoundError:
        pass
    if len(notas) == 0:
        print("Facilidade de uso: nenhuma avaliação registrada ainda (opção 4 do menu).")
        return
    print(f"Facilidade de uso: {len(notas)} avaliações, nota média {sum(notas) / len(notas):.1f} de 5")


def adicionar_orientacao(base):
    print("Nova orientação (Enter em branco cancela).")
    novo = {}
    novo["id"] = input("Identificador (ex.: GOL07): ").strip().upper()
    if novo["id"] == "":
        return base
    for registro in base:
        if registro["id"] == novo["id"]:
            print("Já existe uma orientação com esse identificador.")
            return base
    novo["tema"] = input("Tema: ").strip()
    novo["titulo"] = input("Título do assunto: ").strip()
    novo["pergunta"] = input("Pergunta típica: ").strip()
    chaves = input("Palavras-chave separadas por vírgula: ").split(",")
    novo["palavras_chave"] = []
    for chave in chaves:
        if chave.strip() != "":
            novo["palavras_chave"].append(chave.strip())
    novo["orientacao"] = input("Orientação resumida: ").strip()
    novo["referencia"] = input("Referência (nome da fonte): ").strip()
    novo["link"] = input("Link da fonte: ").strip()
    novo["data_verificacao"] = input("Data de verificação (AAAA-MM-DD): ").strip()
    novo["confirmar"] = input("Exige confirmação no canal oficial? (s/n): ").strip().lower() == "s"
    novo["relacionados"] = []

    for campo in CAMPOS_OBRIGATORIOS:
        if novo[campo] == "" or novo[campo] == []:
            print(f"Campo obrigatório vazio: {campo}. Orientação não adicionada.")
            return base

    try:
        with open(ARQUIVO_BASE, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        dados.append(novo)
        with open(ARQUIVO_BASE, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    except (OSError, json.JSONDecodeError):
        print("Não foi possível gravar a base de conhecimento.")
        return base
    print("Orientação adicionada com sucesso.")
    return carregar_base()


def mostrar_instrucoes():
    for modelo in ["A", "B"]:
        instrucao = INSTRUCOES[modelo]
        print(instrucao["nome"])
        print(f"{margem}Papel: {instrucao['papel']}")
        print(f"{margem}Formato: {instrucao['formato']}")
        print(f"{margem}Regras: {instrucao['regras']}")


def trocar_modelo(modelo):
    mostrar_instrucoes()
    escolha = input("Qual modelo deseja usar? (A/B): ").strip().upper()
    if escolha in ["A", "B"]:
        print(f"Modelo de resposta alterado para {INSTRUCOES[escolha]['nome']}.")
        return escolha
    print("Opção inexistente. O modelo atual foi mantido.")
    return modelo


def texto_conferencia(pergunta, base):
    situacao, encontrados = buscar(pergunta, base)
    texto = "Conferência com a base verificada:"
    if situacao == "ok" or situacao == "ambigua":
        for registro in encontrados:
            texto += f"\n{margem}{registro['id']} - {registro['titulo']}: {registro['link']}"
    else:
        texto += (f"\n{margem}Nenhuma orientação da base corresponde a essa pergunta. "
                  f"Confirme a informação no canal oficial.")
    return texto


def ler_texto_resposta(resposta):
    texto = ""
    for bloco in resposta.content:
        if bloco.type == "text":
            texto += bloco.text
    return texto


def criar_cliente_ia():
    if anthropic is None:
        return None, "A biblioteca anthropic não está instalada. Execute: uv sync (ou pip install anthropic)."
    try:
        return anthropic.Anthropic(), ""
    except anthropic.AnthropicError:
        return None, "Credencial da Anthropic não encontrada. Defina a variável ANTHROPIC_API_KEY."


def perguntar_ia(cliente, instrucao, historico, mensagem):
    historico.append({"role": "user", "content": mensagem})
    try:
        resposta = cliente.messages.create(
            model=MODELO_IA,
            max_tokens=4096,
            system=instrucao,
            cache_control={"type": "ephemeral"},
            output_config={"effort": "low"},
            messages=historico,
        )
    except anthropic.AuthenticationError:
        historico.pop()
        return "Chave da API inválida ou ausente. Defina a variável ANTHROPIC_API_KEY."
    except anthropic.RateLimitError:
        historico.pop()
        return "Muitas requisições no momento. Aguarde um pouco e tente de novo."
    except anthropic.APIConnectionError:
        historico.pop()
        return "Sem conexão com a API da Anthropic. Verifique a internet."
    except anthropic.APIStatusError as erro:
        historico.pop()
        return f"Erro da API ({erro.status_code}). Tente novamente mais tarde."
    except (anthropic.AnthropicError, TypeError):
        historico.pop()
        return "Credencial da Anthropic não encontrada. Defina a variável ANTHROPIC_API_KEY."

    if resposta.stop_reason == "refusal":
        historico.pop()
        return "Não posso ajudar com esse pedido. Tente reformular a pergunta."

    historico.append({"role": "assistant", "content": resposta.content})
    return ler_texto_resposta(resposta)


def conversar_com_ia(base):
    cliente, erro = criar_cliente_ia()
    if cliente is None:
        print(erro)
        return

    instrucao = INSTRUCAO_IA + json.dumps(base, ensure_ascii=False, indent=1)
    historico = []

    linha()
    print(f"CHAT COM IA ({MODELO_IA}) - respostas geradas a partir da base verificada.")
    print("As mensagens são enviadas à API da Anthropic. Não digite dados pessoais.")
    print("Digite 'sair' para voltar ao menu.")
    linha()

    while True:
        mensagem = input("Você: ").strip()
        if mensagem.lower() == "sair":
            return
        if mensagem == "":
            print("Digite uma pergunta ou 'sair' para voltar.")
            continue
        if parece_dado_pessoal(mensagem):
            print("Por segurança, não digite CPF, telefone, e-mail ou outros dados pessoais.")
            print("A mensagem não foi enviada. Reescreva sem essas informações.")
            continue

        inicio = time.perf_counter()
        resposta = perguntar_ia(cliente, instrucao, historico, mensagem)
        tempo = time.perf_counter() - inicio
        print(f"Assistente: {resposta}")
        print(f"(resposta em {tempo:.1f} s)")
        print(texto_conferencia(mensagem, base))
        linha()


BOAS_VINDAS = """Olá! Eu sou o Citizen Assist AI.
Oriento sobre golpes digitais, direitos do consumidor e documentos, sempre com a fonte oficial.

Como usar:
- Escreva sua dúvida, por exemplo: caí num golpe do pix
- /temas mostra todos os assuntos
- /ia conversa com a inteligência artificial (respostas baseadas na mesma base verificada)
- /busca volta para a busca direta na base verificada
- /ajuda mostra esta mensagem

Não envie CPF, senhas, telefone ou outros dados pessoais.
""" + AVISO_NAO_OFICIAL


def texto_relacionados(registro, indice):
    if len(registro["relacionados"]) == 0:
        return ""
    texto = "\n\nAssuntos relacionados (toque para abrir):"
    for codigo in registro["relacionados"]:
        texto += f"\n/{codigo.lower()} - {indice[codigo]['titulo']}"
    return texto


def texto_temas(temas):
    texto = "Assuntos disponíveis (toque para abrir):"
    for nome in temas:
        texto += f"\n\n{nome}:"
        for registro in temas[nome]:
            texto += f"\n/{registro['id'].lower()} - {registro['titulo']}"
    return texto


def responder_telegram(texto, base, indice, temas, sessao, cliente_ia, instrucao):
    texto = texto.strip()
    if texto == "":
        return "Envie sua dúvida em texto. Exemplo: caí num golpe do pix"

    if texto.startswith("/"):
        comando = texto.split()[0].split("@")[0].lower()
        if comando == "/start" or comando == "/ajuda":
            return BOAS_VINDAS
        if comando == "/temas":
            return texto_temas(temas)
        if comando == "/busca":
            sessao["modo"] = "busca"
            sessao["historico"] = []
            return "Modo busca ativado: respondo direto com a base verificada."
        if comando == "/ia":
            if cliente_ia is None:
                return "O chat com IA não está disponível agora. Use a busca direta escrevendo sua dúvida."
            sessao["modo"] = "ia"
            sessao["historico"] = []
            return (f"Modo IA ativado ({MODELO_IA}). Pode perguntar à vontade; "
                    f"as mensagens são enviadas à API da Anthropic. Use /busca para sair.")
        codigo = comando[1:].upper()
        if codigo in indice:
            registro = indice[codigo]
            return formatar_modelo_b(registro) + texto_relacionados(registro, indice)
        return "Comando não reconhecido. Use /ajuda para ver as opções."

    if parece_dado_pessoal(texto):
        return ("Por segurança, não envie CPF, telefone, e-mail ou outros dados pessoais. "
                "Reescreva a pergunta sem essas informações.")

    if sessao["modo"] == "ia":
        resposta = perguntar_ia(cliente_ia, instrucao, sessao["historico"], texto)
        return resposta + "\n\n" + texto_conferencia(texto, base)

    situacao, encontrados = buscar(texto, base)
    if situacao == "ok":
        registro = encontrados[0]
        return formatar_modelo_b(registro) + texto_relacionados(registro, indice)
    if situacao == "ambigua":
        resposta = "Sua pergunta combina com mais de um assunto. Qual deles você procura?"
        for registro in encontrados:
            resposta += f"\n/{registro['id'].lower()} - {registro['titulo']}"
        return resposta
    return texto_sem_resposta(temas) + "\n\nUse /temas para ver todos os assuntos."


def chamar_telegram(token, metodo, dados):
    try:
        resposta = requests.post(TELEGRAM_API + token + "/" + metodo, json=dados, timeout=40)
        return resposta.json()
    except (requests.RequestException, ValueError):
        return {"ok": False}


def iniciar_telegram(base):
    if requests is None:
        print("A biblioteca requests não está instalada. Execute: uv sync (ou pip install requests).")
        return

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token == "":
        token = input("Token do bot (gerado no @BotFather): ").strip()
    if token == "":
        print("Token não informado.")
        return

    dados = chamar_telegram(token, "getMe", {})
    if not dados.get("ok"):
        print("Não foi possível conectar ao Telegram. Verifique o token e a internet.")
        return

    cliente_ia, erro = criar_cliente_ia()
    if cliente_ia is None:
        print(f"Aviso: {erro} O modo /ia ficará indisponível no bot.")

    instrucao = INSTRUCAO_IA + json.dumps(base, ensure_ascii=False, indent=1)
    indice = montar_indice(base)
    temas = montar_temas(base)
    sessoes = {}
    proxima = 0

    linha()
    print(f"Bot @{dados['result']['username']} em funcionamento. Pressione Ctrl+C para parar.")
    linha()

    try:
        while True:
            dados = chamar_telegram(token, "getUpdates", {"offset": proxima, "timeout": 30})
            if not dados.get("ok"):
                print("Falha ao buscar mensagens. Nova tentativa em 5 segundos.")
                time.sleep(5)
                continue

            for atualizacao in dados["result"]:
                proxima = atualizacao["update_id"] + 1
                mensagem = atualizacao.get("message")
                if mensagem is None:
                    continue

                chat_id = mensagem["chat"]["id"]
                if chat_id not in sessoes:
                    sessoes[chat_id] = {"modo": "busca", "historico": []}
                sessao = sessoes[chat_id]

                if sessao["modo"] == "ia":
                    chamar_telegram(token, "sendChatAction", {"chat_id": chat_id, "action": "typing"})

                inicio = time.perf_counter()
                resposta = responder_telegram(mensagem.get("text", ""), base, indice, temas,
                                              sessao, cliente_ia, instrucao)
                chamar_telegram(token, "sendMessage", {"chat_id": chat_id, "text": resposta[:4000],
                                                       "disable_web_page_preview": True})
                tempo = time.perf_counter() - inicio
                print(f"Mensagem respondida (modo {sessao['modo']}, {tempo:.1f} s)")
    except KeyboardInterrupt:
        print("\nBot do Telegram parado.")


def menu():
    base = carregar_base()
    modelo = "B"
    if len(base) == 0:
        print("O assistente não pode funcionar sem uma base de conhecimento válida.")
        return

    print("=" * 70)
    print("CITIZEN ASSIST AI - Golpes digitais, direitos do consumidor e documentos")
    print(AVISO_NAO_OFICIAL)
    print("Não digite CPF, senhas, telefone ou outros dados pessoais.")
    print("=" * 70)

    while True:
        indice = montar_indice(base)
        temas = montar_temas(base)
        print(f"\n{len(base)} orientações carregadas em {len(temas)} temas.")
        print("1 - Escolher um tema")
        print("2 - Fazer uma pergunta")
        print("3 - Executar testes e indicadores")
        print("4 - Avaliar a facilidade de uso")
        print("5 - Adicionar orientação à base")
        print(f"6 - Trocar modelo de resposta (atual: {modelo})")
        print(f"7 - Conversar com a IA (chat com {MODELO_IA})")
        print("8 - Iniciar o bot do Telegram")
        print("0 - Sair")
        opcao = input("Escolha uma opção: ").strip()

        if opcao == "1":
            consultar_tema(indice, temas, modelo)
        elif opcao == "2":
            consultar_pergunta(base, indice, temas, modelo)
        elif opcao == "3":
            executar_testes(base)
        elif opcao == "4":
            avaliar_uso()
        elif opcao == "5":
            base = adicionar_orientacao(base)
        elif opcao == "6":
            modelo = trocar_modelo(modelo)
        elif opcao == "7":
            conversar_com_ia(base)
        elif opcao == "8":
            iniciar_telegram(base)
        elif opcao == "0":
            print("Até logo! Em caso de dúvida, procure sempre o canal oficial.")
            break
        elif opcao == "":
            print("Você não escolheu nenhuma opção.")
        else:
            print("Opção inexistente. Digite um número de 0 a 8.")


if __name__ == "__main__":
    menu()
