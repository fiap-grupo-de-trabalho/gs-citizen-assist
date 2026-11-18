# Plano de testes e indicadores

## 1. Perguntas de teste

Arquivo: `data/perguntas_teste.json`, com 20 perguntas. A resposta esperada foi definida **antes** da execução.

| Tipo | Quantidade | Objetivo |
|---|---|---|
| direta | 5 | Pergunta parecida com a pergunta típica do registro |
| reformulacao | 8 | Mesma dúvida com outras palavras, gírias ou relato da situação ("Hackearam meu zap") |
| fora_do_tema | 3 | Assuntos fora da base (passaporte, INSS, previsão do tempo): deve responder SEM_RESPOSTA |
| limite | 4 | Entrada vazia, consulta ambígua ("golpe", "whatsapp") e texto sem sentido |

Como executar: `python src/sistema.py` e, no menu, a opção **3 - Executar testes e indicadores**. O resultado é salvo em `data/resultados_testes.csv`.

## 2. Resultados obtidos

| ID | Tipo | Pergunta | Esperado | Obtido | Resultado |
|---|---|---|---|---|---|
| T01 | direta | Caí num golpe do Pix, o que eu faço? | GOL01 | GOL01 | acerto |
| T02 | direta | Como saber se um boleto é falso? | GOL04 | GOL04 | acerto |
| T03 | direta | Posso desistir de uma compra feita pela internet? | CON01 | CON01 | acerto |
| T04 | direta | Como tirar a segunda via da identidade? | DOC02 | DOC02 | acerto |
| T05 | direta | Como registrar boletim de ocorrência pela internet? | DOC01 | DOC01 | acerto |
| T06 | reformulacao | Meu filho mandou mensagem de um número novo pedindo dinheiro | GOL02 | GOL02 | acerto |
| T07 | reformulacao | Ligaram dizendo ser do banco e pediram minha senha | GOL05 | GOL05 | acerto |
| T08 | reformulacao | A geladeira que eu comprei chegou quebrada | CON03 | CON03 | acerto |
| T09 | reformulacao | Me cobraram uma conta que eu já tinha pago | CON04 | CON04 | acerto |
| T10 | reformulacao | Roubaram meu celular, como faço o bloqueio? | GOL06 | GOL06 | acerto |
| T11 | reformulacao | Quero ver quais chaves pix estão no meu nome | DOC04 | DOC04 | acerto |
| T12 | reformulacao | Hackearam meu zap | GOL03 | GOL03 | acerto |
| T13 | reformulacao | A loja não quer resolver meu problema, onde reclamo? | CON05 | CON05 | acerto |
| T14 | fora_do_tema | Como faço para tirar passaporte? | SEM_RESPOSTA | SEM_RESPOSTA | acerto |
| T15 | fora_do_tema | Como pedir aposentadoria no INSS? | SEM_RESPOSTA | SEM_RESPOSTA | acerto |
| T16 | fora_do_tema | Qual a previsão do tempo para amanhã? | SEM_RESPOSTA | SEM_RESPOSTA | acerto |
| T17 | limite | (entrada vazia) | VAZIA | VAZIA | acerto |
| T18 | limite | golpe | AMBIGUA | GOL01 | **erro** |
| T19 | limite | asdfgh qwerty | SEM_RESPOSTA | SEM_RESPOSTA | acerto |
| T20 | limite | whatsapp | AMBIGUA | AMBIGUA | acerto |

## 3. Indicadores

| Indicador | Valor |
|---|---|
| Taxa de acerto geral | **95,0%** (19 de 20) |
| Acerto em perguntas diretas | 100% (5/5) |
| Acerto em reformulações | 100% (8/8) |
| Acerto em perguntas fora do tema | 100% (3/3) |
| Acerto em casos-limite | 75% (3/4) |
| Tempo médio de consulta | cerca de 0,4 ms por pergunta (varia a cada execução; o máximo ficou abaixo de 1 ms) |

## 4. Interpretação

- **A busca por palavras-chave com pontuação funciona bem com a base pequena:** todas as perguntas diretas e reformuladas foram respondidas com o registro certo, e nenhuma pergunta fora do tema recebeu resposta inventada. Esse último ponto é o mais importante para a confiabilidade.
- **O erro do T18 ("golpe") mostra uma limitação real:** a ambiguidade só é detectada quando dois ou mais registros **empatam** na pontuação. A palavra "golpe" está nas palavras-chave apenas do registro do Pix (GOL01), então o sistema escolheu esse registro, quando o ideal seria perguntar "golpe de quê?". Já "whatsapp" (T20) aparece em dois registros, e a ambiguidade foi detectada corretamente.
- **O tempo de consulta é desprezível:** a busca sequencial percorre os 16 registros em menos de 1 ms. Com uma base de milhares de registros, seria preciso um índice invertido (dicionário de palavra para lista de registros).
- **Limitações da avaliação:** as perguntas de teste foram escritas pela própria equipe, que conhece as palavras-chave, e isso tende a inflar a taxa de acerto. Além disso, 20 perguntas é uma amostra pequena.

## 5. Melhorias possíveis

1. **Detectar perguntas genéricas:** quando a pergunta tem só uma palavra e ela aparece em vários registros do mesmo tema (como "golpe"), mostrar a lista de assuntos do tema em vez de escolher um.
2. **Tratar sinônimos e erros de digitação:** um dicionário de sinônimos ("zap" → "whatsapp", "BO" → "boletim de ocorrência") e uma comparação aproximada de palavras.
3. **Testar com perguntas reais:** coletar perguntas de usuários de teste (sem dados pessoais) para não depender de perguntas escritas pela equipe.

## 6. Teste de facilidade de uso (pelo bot do Telegram)

O teste de usabilidade é feito no **bot em produção** ([t.me/citizen_assist_ai_bot](https://t.me/citizen_assist_ai_bot)), porque é assim que o cidadão vai usar o assistente: pelo celular, conversando com a IA. A busca local e os indicadores das seções 1 a 5 medem a **precisão da base**; este teste mede se uma pessoa real **consegue ser ajudada** na conversa.

### Como aplicar

- **Participantes:** pelo menos 1, de preferência alguém do público-alvo (pessoa mais velha ou com pouca familiaridade com tecnologia), usando o **próprio celular**.
- **Antes de começar:** explique que é um teste do assistente, não da pessoa, e peça para ela **não enviar dados reais** (CPF, telefone, senhas).
- **Durante:** leia cada tarefa em voz alta e não ajude. Anote se concluiu, o tempo (do início da tarefa até a pessoa dizer que entendeu) e o que gerou dúvida.
- **Tempo de resposta do bot:** fica registrado nos logs do container no Dokploy ("Mensagem respondida em X s"), junto com a conferência com a base.

### Roteiro de tarefas

| Nº | Tarefa lida ao participante | Critério de sucesso |
|---|---|---|
| 1 | "Abra o assistente pelo QR Code (ou link) e comece a conversa." | Encontra o bot, toca em **Iniciar** e lê a mensagem de boas-vindas |
| 2 | "Imagine que você fez um Pix para um golpista. Pergunte ao assistente o que fazer, do seu jeito." | Diz qual é a primeira ação (avisar o banco e pedir a devolução pelo MED) e aponta onde está a fonte |
| 3 | "E se o banco não resolver? Continue a conversa." | O bot usa o contexto, e a pessoa entende que pode reclamar no consumidor.gov.br ou no Procon |
| 4 | "Você comprou um produto pela internet e se arrependeu. Pergunte se pode devolver." | Diz o prazo de 7 dias |
| 5 | "Pergunte como tirar o passaporte." | Entende que o bot não tem essa orientação e indica o canal oficial |

### Perguntas depois do teste (notas de 1 a 5)

| Pergunta | Escala |
|---|---|
| P1. Foi fácil usar o assistente? | 1 = muito difícil · 5 = muito fácil |
| P2. As respostas foram fáceis de entender? | 1 = nada claras · 5 = muito claras |
| P3. Você se sentiu acolhido(a) pela conversa? | 1 = nada · 5 = muito |
| P4. Você seguiria a orientação do assistente? | 1 = de jeito nenhum · 5 = com certeza |
| P5. Você percebeu que a resposta citava uma fonte oficial? | sim / não |
| P6. O que mais atrapalhou? E o que mais ajudou? | resposta livre |

### Resultado do teste de usabilidade

> **A PREENCHER PELA EQUIPE após aplicar o roteiro.** Para mais participantes, repita as colunas.

**Participante 1** (perfil, sem dados pessoais; ex.: "mulher, 60+, usa WhatsApp todo dia"): ____

| Tarefa | Concluiu? (s/n) | Tempo (s) | Dificuldade observada |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |

| P1 Facilidade | P2 Clareza | P3 Acolhimento | P4 Confiança | P5 Viu a fonte? |
|---|---|---|---|---|
| | | | | |

Comentários (P6): ____

### Indicadores de usabilidade

| Indicador | Como calcular | Resultado |
|---|---|---|
| Taxa de conclusão das tarefas | tarefas concluídas ÷ tarefas aplicadas | ____ |
| Tempo médio por tarefa | soma dos tempos ÷ tarefas | ____ |
| Tempo médio de resposta do bot | média dos "Mensagem respondida em X s" nos logs do Dokploy | ____ |
| Nota média de facilidade (P1) | média das notas | ____ |
| Nota média de clareza (P2) | média das notas | ____ |

### Interpretação

> **A PREENCHER:** o que funcionou, onde houve dificuldade e qual melhoria isso sugere (por exemplo: respostas longas demais para o celular, pessoa não percebeu a fonte, dúvida sobre como começar).
