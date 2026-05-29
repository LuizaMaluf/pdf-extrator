# PDF Extractor

Pipeline para extração estruturada de dados de relatórios governamentais em PDF com layouts e conteúdos heterogêneos. Organizado por tipo de relatório (Domínio), com aprendizado contínuo via feedback humano e API para consulta estruturada dos dados extraídos por Domínio e período.

## Language

**Domain (Domínio)**:
Um tipo específico de relatório governamental com estrutura própria (layout, seções, campos). Determina qual Extractor e qual Schema são aplicados. Um mesmo ministério pode ter múltiplos Domínios.
_Avoid_: Ministério, fonte, categoria

**Extractor**:
A lógica de extração específica de um Domínio, combinando parser determinístico (campos estruturados) e LLM (conteúdo não estruturado). Um Extractor por Domínio.
_Avoid_: Parser, leitor, processador

**Schema**:
O conjunto de campos esperados de uma extração de um Domínio. Ciclo de vida: `draft` (emergindo das primeiras extrações) → `validated` (declarado padrão pelo validador). Um Schema `validated` pode ganhar novos campos via Correction, mas nunca perder campos já estabelecidos — campos obsoletos são marcados como `deprecated`.
_Avoid_: Template, estrutura, modelo de dados

**Extraction Job**:
Unidade assíncrona de trabalho disparada pelo upload de um PDF. Retorna um `job_id`; o cliente consulta o status até a conclusão.
_Avoid_: Tarefa, processamento, request

**Validation**:
Revisão humana de um Extraction Job concluído, com correção campo a campo do resultado extraído.
_Avoid_: Revisão, aprovação, auditoria

**Correction**:
Edição campo a campo feita pelo validador durante uma Validation. Cada Correction alimenta os Few-Shot Examples do Domínio.
_Avoid_: Ajuste, fix, edição

**Few-Shot Example**:
Extração corrigida e validada armazenada como exemplo concreto para guiar extrações futuras do mesmo Domínio via prompt. Selecionados por similaridade semântica com o PDF sendo processado, não por recência.
_Avoid_: Exemplo de treinamento, amostra

**Schema Version**:
Snapshot imutável do Schema no momento em que um Extraction Job é executado. Cada Extraction Job fica vinculado à Schema Version ativa naquele instante. Reprocessamento com uma Schema Version mais nova é sempre explícito e manual.
_Avoid_: Versão, snapshot, histórico

**Domain Registration**:
Protocolo de onboarding ativado quando um PDF de Domínio desconhecido é carregado. Coleta: órgão de origem, contexto mínimo do relatório, seções prioritárias, campos conhecidos antecipadamente (mínimo 2–3) e periodicidade (anual, trimestral, mensal). O resultado alimenta a primeira extração como contexto de prompt, e o Schema `draft` emerge da primeira Validation.
_Avoid_: Cadastro, configuração, setup

**Confidence**:
Grau de certeza da classificação automática de Domínio de um PDF. Abaixo de um limiar, a classificação requer confirmação humana antes de prosseguir.
_Avoid_: Score, probabilidade, certeza

**Role**:
Perfil de permissão de um usuário do sistema. `analyst` (ciência política ou tecnologia) pode fazer upload e Validation. `admin` (tecnologia) pode adicionalmente declarar Schemas como `validated` e gerenciar Domínios via Domain Registration.
_Avoid_: Usuário, perfil, grupo

## Example dialogue

> "Recebi um PDF novo do Ministério da Saúde."
> "É de qual Domínio? Execução orçamentária ou indicadores epidemiológicos? São Extractors diferentes."
> "Execução orçamentária. O Schema desse Domínio já está validated?"
> "Está. O Extractor vai usar o Schema como contrato e os Few-Shot Examples das últimas Corrections para guiar o LLM."
> "E se a extração vier errada?"
> "O validador abre a Validation, corrige campo a campo — essa Correction vira um novo Few-Shot Example automaticamente."
> "Como o sistema escolhe quais exemplos usar na próxima extração?"
> "Por similaridade semântica com o PDF atual — não pelos mais recentes. Um relatório de 2019 pode ter exemplos mais úteis do que o de 2024 se a estrutura for mais parecida."
> "E se chegar um PDF de um Domínio que nunca vimos?"
> "Dispara o Domain Registration — a pessoa de ciência política responde sobre o órgão, contexto, seções prioritárias, campos que ela sabe que existem e a periodicidade. Com isso o sistema faz a primeira tentativa e o Schema `draft` emerge da primeira Validation."
