# Uso de Inteligência Artificial no projeto

## Onde a IA foi usada

| Etapa | Ferramenta | Como foi usada |
|---|---|---|
| Pesquisa das orientações | Assistente de IA generativa (Claude) | Localizar as páginas oficiais (Banco Central, gov.br, Planalto, consumidor.gov.br, Febraban, WhatsApp) de onde foram tiradas as orientações da base. |
| Redação das orientações | Assistente de IA generativa (Claude) | Resumir o conteúdo das páginas oficiais em linguagem simples. |
| Código | Assistente de IA generativa (Claude) | Apoio na escrita do `src/sistema.py`, usando apenas recursos vistos nas fases 1 a 7 (listas, dicionários, funções, arquivos JSON, `try/except`). |
| Modelos de instrução | Assistente de IA generativa (Claude) | Sugestão e comparação dos modelos A e B de instrução de resposta. |
| Plano de testes | Assistente de IA generativa (Claude) | Sugestão de perguntas diretas, reformulações, perguntas fora do tema e casos-limite. |

## O protótipo não usa IA externa em tempo de execução

O Citizen Assist AI **não chama nenhum modelo de linguagem** durante o uso. Toda resposta mostrada ao cidadão vem da base `data/base_conhecimento.json`, que foi conferida nas fontes oficiais. Os modelos A e B funcionam como **instruções de resposta**: definem o papel do assistente, o formato e as regras, e o código aplica essas regras. Por isso o assistente não "alucina": se a pergunta não bate com a base, ele avisa que não tem orientação confiável.

## Validação crítica realizada

1. **Fontes conferidas uma a uma:** cada orientação foi comparada com a página oficial indicada no campo `link`, e a data da conferência está em `data_verificacao`.
2. **Correções feitas:** quando a página oficial dizia algo diferente do resumo sugerido pela IA (prazos, nomes de serviços, datas de vigência), o texto foi corrigido para seguir a fonte oficial.
3. **Nada de número sem fonte:** prazos e valores (por exemplo, 7 dias do direito de arrependimento e 30/90 dias da garantia legal) aparecem apenas quando estão escritos na lei ou na página oficial citada.
4. **Testes automáticos:** as 15 perguntas de `data/perguntas_teste.json` são executadas pela opção 3 do menu, e o resultado é comparado com a resposta esperada, que foi definida antes de rodar o teste.
5. **Revisão humana:** o integrante revisou o código, rodou o sistema e conferiu se as respostas citam a fonte correta e se os avisos de limitação aparecem.

## Limites assumidos

- Regras de bancos, órgãos e serviços mudam. A data de verificação mostra quando a informação foi conferida, e o assistente pede confirmação no canal oficial para assuntos com prazos ou procedimentos que mudam com frequência.
- A IA foi ferramenta de apoio. As decisões sobre o que entra na base, a estratégia de busca e a interpretação dos indicadores são da equipe.
