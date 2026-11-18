# Uso de Inteligência Artificial no projeto

## IA usada no desenvolvimento

| Etapa | Ferramenta | Como foi usada |
|---|---|---|
| Pesquisa das orientações | Assistente de IA generativa (Claude) | Localizar as páginas oficiais (Banco Central, gov.br, Planalto, consumidor.gov.br, Febraban, WhatsApp) de onde foram tiradas as orientações da base. |
| Redação das orientações | Assistente de IA generativa (Claude) | Resumir o conteúdo das páginas oficiais em linguagem simples. |
| Código | Assistente de IA generativa (Claude) | Apoio na escrita do `src/sistema.py`, usando recursos vistos nas fases 1 a 7 (listas, dicionários, funções, arquivos JSON, `try/except`). |
| Modelos de instrução | Assistente de IA generativa (Claude) | Sugestão e comparação dos modelos A, B e C de instrução de resposta. |
| Plano de testes | Assistente de IA generativa (Claude) | Sugestão de perguntas diretas, reformulações, perguntas fora do tema e casos-limite. |

## IA usada no protótipo (opção 7: chat com Claude Haiku 5.5)

O assistente funciona de dois jeitos:

1. **Opções 1 a 6 (sem IA externa):** toda resposta vem direto da base `data/base_conhecimento.json`, por busca de palavras-chave. Os modelos A e B são instruções de resposta que o próprio código aplica. Essas opções não "alucinam": se a pergunta não bate com a base, o assistente avisa que não tem orientação confiável. São as opções usadas nos testes e indicadores (opção 3).
2. **Opção 7 (chat com LLM):** usa o modelo `claude-haiku-5-5`, da Anthropic, pela biblioteca oficial `anthropic`. O modelo recebe o prompt do Modelo C (`docs/prompts.md`) com a base verificada inteira e a regra de responder **somente** com ela e citar a fonte.

### Como as respostas do modelo externo são confrontadas com a base

- **Na instrução:** o modelo é proibido de usar conhecimento fora da base, deve terminar cada resposta com a fonte e o link da orientação usada e deve dizer quando não sabe.
- **No código:** depois de cada resposta da IA, o sistema roda a busca local na mesma pergunta e mostra a **"Conferência com a base verificada"**, com as orientações (id, título e link) que correspondem à pergunta, ou o aviso de que nenhuma corresponde. O usuário pode comparar a resposta gerada com a orientação verificada.
- **Privacidade:** mensagens que parecem conter CPF, telefone ou e-mail não são enviadas à API, e o usuário é avisado de que as mensagens vão para a Anthropic.

### Teste do chat com IA (17/11/2026)

| Mensagem | Comportamento observado | Avaliação |
|---|---|---|
| "caí num golpe do pix, o que faço?" | Orientação do MED, com prazo de 80 dias e aviso de confirmação. Citou a fonte do Banco Central, a mesma da orientação GOL01 mostrada na conferência. Respondeu em 1,7 s. | Correta e fiel à base. |
| "e se o banco não resolver?" (continuação) | Usou o contexto da conversa, avisou que a base não tem esse caso exato e indicou consumidor.gov.br e Procon, citando as duas fontes. | Correta. A conferência local, que olha só a última mensagem, listou 3 assuntos possíveis; a IA lidou melhor com a continuação. |
| "como tiro passaporte?" | Disse que não tem orientação verificada e sugeriu os temas disponíveis. A conferência confirmou que nenhuma orientação corresponde. | Correta, mas citou "Polícia Federal", informação que não está na base. É um pequeno vazamento de conhecimento externo, registrado como limitação. |

## Validação crítica realizada

1. **Fontes conferidas uma a uma:** cada orientação foi comparada com a página oficial indicada no campo `link`, e a data da conferência está em `data_verificacao`.
2. **Correções feitas:** quando a página oficial dizia algo diferente do resumo sugerido pela IA, o texto foi corrigido para seguir a fonte. Exemplos: o WhatsApp não divulga e-mail de suporte nas páginas oficiais, por isso a base indica o "Fale conosco"; a taxa da 2ª via da CIN não foi confirmada em fonte federal, por isso a orientação diz apenas que "pode ter taxa, dependendo do estado".
3. **Nada de número sem fonte:** prazos e valores (7 dias de arrependimento, 30/90 dias de garantia, 80 dias do MED, 10 dias de resposta no consumidor.gov.br) aparecem apenas quando estão na lei ou na página oficial citada.
4. **Testes automáticos:** as 20 perguntas de `data/perguntas_teste.json` são executadas pela opção 3 do menu, e o resultado é comparado com a resposta esperada, que foi definida antes de rodar o teste.
5. **Revisão humana:** o grupo revisou o código, rodou o sistema e conferiu se as respostas citam a fonte correta e se os avisos de limitação aparecem.

## Limites assumidos

- Regras de bancos, órgãos e serviços mudam. A data de verificação mostra quando a informação foi conferida, e o assistente pede confirmação no canal oficial nos assuntos com prazos ou procedimentos que mudam com frequência.
- O chat com IA pode reescrever a orientação com outras palavras e, como visto no teste do passaporte, às vezes acrescenta conhecimento geral que não está na base. A conferência com a base reduz esse risco, mas não verifica a resposta automaticamente; por isso, os indicadores oficiais do projeto são calculados com a busca local (opção 3).
- A IA foi ferramenta de apoio. As decisões sobre o que entra na base, a estratégia de busca e a interpretação dos indicadores são da equipe.
