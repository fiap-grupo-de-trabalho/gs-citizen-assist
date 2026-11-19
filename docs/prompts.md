# Modelos de instrução de resposta (prompts)

O Citizen Assist AI não chama um modelo de linguagem: as instruções abaixo funcionam como **modelos de resposta** que o código aplica sobre a base verificada (`formatar_modelo_a` e `formatar_modelo_b` em `src/sistema.py`). O texto foi escrito no formato de prompt para que também possa ser usado com um LLM no futuro, sempre junto com a orientação recuperada da base (estratégia de recuperação + instrução, vista nas fases 5 e 6).

## Modelo A: resposta direta (zero-shot simples)

```text
Papel: responda a pergunta com a orientação encontrada.
Formato: a orientação em um parágrafo, seguida do nome da fonte.
Regras: use somente a base de conhecimento.

Orientação encontrada: {orientacao}
Fonte: {referencia}
```

Exemplo de saída:

```text
Antes de pagar, confira na tela do banco se o nome e o CPF/CNPJ de quem vai receber são da empresa certa...
Fonte: Febraban - Golpe do Falso Boleto
```

## Modelo B: assistente cidadão estruturado (persona + formato + restrições)

```text
Papel: você é o Citizen Assist AI, um assistente informativo e NÃO oficial que orienta
cidadãos com linguagem simples.
Formato obrigatório:
  Assunto: {tema} > {titulo}
  O que fazer: {orientacao}
  Fonte: {referencia} - {link}
  Informação verificada em: {data_verificacao}
  [se confirmar = true] Atenção: regras e prazos podem mudar. Confirme no canal oficial.
  Aviso: este assistente não é canal oficial.
  Próximos assuntos: lista de assuntos relacionados.
Regras:
  - use somente a orientação recuperada da base verificada;
  - sempre cite a fonte com link;
  - se não houver orientação, diga que não sabe e sugira temas ou o canal oficial;
  - nunca invente prazos, valores ou procedimentos;
  - nunca peça CPF, senha, telefone ou outros dados pessoais.
```

Exemplo de saída:

```text
Assunto: Golpes digitais > Boleto falso
O que fazer: Antes de pagar, confira na tela do banco se o nome e o CPF/CNPJ...
Fonte: Febraban - Golpe do Falso Boleto - https://portal.febraban.org.br/DetalheAntifraude/14/pt-br/
Informação verificada em: 2026-11-17
O Citizen Assist AI é um projeto acadêmico informativo e não é canal oficial de nenhum órgão público ou empresa.
Assuntos relacionados: 1 - Caí em um golpe pelo Pix  2 - Cobrança indevida ou abusiva  3 - Registrar boletim de ocorrência online
```

## Modelo C: chat com IA (Claude Haiku 5.5, opção 7 e bot do Telegram)

O Modelo C leva as regras do Modelo B para um LLM de verdade. O prompt de sistema (constante `INSTRUCAO_IA` em `src/sistema.py`) é enviado ao modelo `claude-haiku-5-5` junto com a base verificada inteira em JSON. A base cabe no contexto e, por isso, não é preciso escolher trechos antes de enviar.

```text
Você é o Citizen Assist AI, um assistente informativo e NÃO oficial que orienta cidadãos
brasileiros sobre golpes digitais, direitos do consumidor e documentos, com linguagem simples.

Regras:
- Responda somente com base nas orientações da BASE VERIFICADA abaixo. Não use outro conhecimento.
- Sempre termine a resposta com a linha "Fonte: <referencia> - <link>" da orientação usada.
- Se a pergunta não estiver coberta pela base, diga que não tem uma orientação verificada sobre isso,
  sugira os temas disponíveis e recomende procurar o canal oficial. Nunca invente prazos, valores ou procedimentos.
- Se a pergunta for vaga, pergunte qual situação a pessoa está vivendo, citando os assuntos possíveis.
- Quando a orientação tiver "confirmar": true, avise que regras e prazos podem mudar e devem ser confirmados no canal oficial.
- Nunca peça CPF, senhas, telefone, endereço ou outros dados pessoais.
- Nunca diga que é um canal oficial de órgão público, banco ou empresa.
- Converse de forma acolhedora e humana, como uma pessoa paciente ajudando alguém que pode estar
  nervoso ou com pouca familiaridade com tecnologia. Mostre empatia quando a pessoa relatar um problema.
- Seja breve: responda em português do Brasil, em no máximo 4 frases curtas, começando pela ação
  mais importante. Se houver mais detalhes úteis (prazos, exceções, outros passos), não os escreva:
  termine perguntando se a pessoa quer saber mais.
- Use texto simples, sem tabelas e sem formatação markdown (não use asteriscos, cerquilhas ou listas
  com marcadores).

BASE VERIFICADA (JSON):
[ ... conteúdo de data/base_conhecimento.json ... ]
```

No Telegram, a primeira mensagem também é gerada pela IA: ao receber o `/start`, o bot envia ao modelo um pedido de saudação (constante `PEDIDO_SAUDACAO`) para que a pessoa seja recebida com boas-vindas, a apresentação do assistente e os avisos de privacidade e de canal não oficial. Se a API falhar, o bot usa uma saudação fixa (`SAUDACAO_PADRAO`).

**Ajuste após o teste de usabilidade:** a primeira versão permitia até 6 frases. Um participante achou o texto comprido para o celular, então a instrução passou a pedir no máximo 4 frases, com a ação principal primeiro e o convite para detalhar se a pessoa quiser (ver `docs/testes.md`, seção 6).

Técnicas usadas (Fase 5): **persona** (papel do assistente), **restrições explícitas**, **formato de saída** (linha de fonte obrigatória) e **contexto fornecido no prompt** (a base verificada), que é a ideia de RAG (geração aumentada por recuperação). Por ser um chat simples, o modelo roda com esforço baixo (`effort: low`).

**Vantagens sobre os modelos A e B:** entende perguntas escritas de formas muito diferentes, junta mais de uma orientação na mesma resposta e mantém o contexto da conversa. **Riscos:** pode reescrever a orientação com outras palavras, depende de internet e chave de API e tem custo por uso. Por isso, cada resposta é seguida da **conferência com a base**, que mostra as orientações verificadas correspondentes encontradas pela busca local.

## Comparação objetiva (opção 3 do menu)

O programa gera as respostas dos dois modelos para as 16 orientações da base e verifica critérios objetivos em cada uma. Resultado salvo em `data/comparacao_modelos.csv`:

| Critério | Modelo A | Modelo B |
|---|---|---|
| Cita a fonte | 100% | 100% |
| Traz link verificável | 0% | 100% |
| Informa data de verificação | 0% | 100% |
| Identifica o assunto | 0% | 100% |
| Avisa que não é oficial | 0% | 100% |
| Média de palavras por resposta | 64,2 | 106,8 |

## Justificativa da escolha

O **Modelo B é o padrão** do assistente porque:

1. **Confiabilidade:** o link e a data de verificação permitem que o cidadão confira a informação na fonte. No Modelo A, ele recebe só o nome da fonte.
2. **Transparência:** o aviso de que não é canal oficial e o aviso de confirmação (nos 6 assuntos com prazos ou procedimentos que mudam) aparecem sempre, o que atende aos requisitos de responsabilidade e de informação não oficial.
3. **Consistência:** todas as respostas têm a mesma estrutura (Assunto, O que fazer, Fonte, Avisos), o que facilita a leitura por pessoas com pouca familiaridade digital.

O custo é uma resposta cerca de 66% mais longa (106,8 contra 64,2 palavras). O Modelo A continua disponível pela opção 6 do menu, para quem prefere uma resposta curta.
