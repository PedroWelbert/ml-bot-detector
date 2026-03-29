# ml-bot-detector
Projeto final do Workshop PECEGE/POLI USP (Ciência de Dados e IA). Consiste em um pipeline de Machine Learning que analisa padrões de tráfego no access_log do Apache para identificar e alertar sobre bots maliciosos, otimizando o tempo de mitigação manual em servidores de baixo custo.

<img width="2245" height="1587" alt="model_canvas_ml_bot_detector" src="https://github.com/user-attachments/assets/9731adee-5fdd-47e8-84ee-1e8f5885984f" />

## Machine Learning Canvas: Sistema de Detecção de Bots

### 1. Proposta de Valor (O Problema e a Solução)
* **Qual é o problema de negócio?** Instâncias F1-micro no GCP ficam sobrecarregadas (CPU, RAM, Disco) e caem devido a acessos massivos de bots. O processo atual de mitigação é 100% manual, lento e reativo (acessar via SSH, ler logs, reiniciar serviços e bloquear IP no firewall).
* **Qual é a solução proposta pela IA?** Um modelo preditivo de classificação que analisa o comportamento de tráfego de forma contínua para identificar e sinalizar automaticamente (e futuramente bloquear) IPs maliciosos antes da indisponibilidade do serviço.

### 2. Ação e Decisão (Como a IA será usada)
* **Qual decisão o modelo vai apoiar?** A decisão de intervir em um IP específico.
* **Como o usuário vai interagir com isso?** O modelo enviará um alerta automatizado (ex: via Telegram/Discord) indicando o IP suspeito e o grau de confiança da detecção, permitindo bloqueio com 1 clique (ou automático no futuro).

### 3. Fontes de Dados (Onde aprenderemos)
* **Onde estão os dados brutos?** Arquivos `access_log` do Apache/Nginx das VMs afetadas.
* **O que precisamos coletar?** Um log com um ataque já conhecido (para rotular como `1 - Bot`) e logs de dias normais de tráfego (para rotular como `0 - Humano`).

### 4. Engenharia e Feature Selection (Preparação)
* **Como formatar o log para o modelo?** Regex para transformar as linhas de log em tabelas (CSV). Exportação para o GCP Cloud Logging ou download via script para ambiente externo.
* **Quais são as Features (variáveis de entrada) principais?**
    * Taxa de requisições: Quantidade de acessos do mesmo IP por minuto.
    * Proporção de Erros: % de status HTTP 4xx e 5xx versus status 200.
    * Variância de Navegação: Quantidade de URLs/Endpoints diferentes acessados (bots tendem a focar em poucos endpoints, como `/wp-json/`, `/wp-login.php` ou `/graphql`).

### 5. Métricas de Avaliação (Como medir o sucesso)
* **Métrica de Negócio (Offline/Online):** Redução do tempo de inatividade (downtime) das VMs em 90% e redução de 75% do tempo manual gasto na mitigação de ataques.
* **Métrica do Modelo de IA:** **Precisão (Precision)**. 
    * *Por que não a Acurácia?* Porque boa parte do tráfego é normal. Acurácia seria enganosa.
    * *Qual o custo do erro?* O Falso Positivo (bloquear um IP legítimo) é muito mais grave para o negócio do que o Falso Negativo (deixar um bot passar por mais alguns minutos). Logo, o modelo precisa ter altíssima precisão antes de acionar um alerta.

### 6. Arquitetura e Restrições (O Deploy)
* **Onde o modelo vai rodar?** Externamente à F1-micro. Rodará em uma Cloud Function no GCP (ou script isolado no WSL/Ubuntu) para não consumir os recursos (CPU/RAM) da máquina que já está no limite.

---

## 🚀 Desenvolvimento e Pipeline (MLOps)

Para seguir as melhores práticas de Engenharia de Projetos em IA, o desenvolvimento foi modularizado em 4 etapas (notebooks), separando a exploração de dados, a engenharia de features, o treinamento e a avaliação em ambientes distintos.

### 📓 01. Análise Exploratória de Dados (EDA)
Foco na extração de inteligência dos logs brutos e na identificação de padrões comportamentais sem depender do IP (para evitar generalização falha):
* Mapeamento de tentativas de acesso a caminhos sensíveis e de configuração (`wp-login`, `xmlrpc`, `env`, `setup`).
* Análise da variação de tamanho de respostas (Bots tendem a ter variância zero, pois recebem os mesmos códigos de erro repetidamente).
* Análise de consumo de assets (Humanos carregam `.css`, `.js`, `.png`; bots navegam diretamente para o alvo).

### 📓 02. Pré-processamento e Feature Engineering
Foco em preparar a matriz matemática para o algoritmo de classificação:
* Limpeza de ruídos e dados de alta cardinalidade (IPs, URLs originais).
* Conversão de variáveis categóricas via **One-Hot Encoding**.
* **Correção de Data Leakage (Viés Temporal):** Durante a análise, identificou-se que o modelo poderia simplesmente decorar o horário absoluto do ataque. Para garantir que o modelo aprenda o comportamento, a variável `hora` foi removida e substituída pela **Intensidade** (`req_por_minuto`).
* Divisão em bases de Treino (80%) e Teste (20%) utilizando amostragem estratificada.

### 📓 03. Modelagem e Treinamento
* Implementação do algoritmo **Random Forest Classifier**, escolhido por sua capacidade de lidar com múltiplas regras de decisão não-lineares.
* O treinamento foi realizado exclusivamente sobre os dados de treino (isolando o teste).
* **Model Registry:** O artefato treinado foi serializado em um arquivo `.pkl`, permitindo que o cérebro da aplicação seja carregado em qualquer ambiente sem necessidade de retreinamento.

### 📓 04. Avaliação Profunda e Métricas
O modelo carregado foi submetido aos dados inéditos, atingindo resultados excepcionais e validados contra viés:
* **F1-Score e Acurácia:** **0.99 (99%)**.
* **Matriz de Confusão:** Comprovou a ausência de Falsos Positivos, requisito crítico de negócio estabelecido no ML Canvas (garantindo que usuários/clientes reais não sejam bloqueados).
* **Feature Importance:** A análise matemática do algoritmo confirmou que a variável de intensidade (`req_por_minuto`) aliada aos status de resposta e caminhos suspeitos foram os principais motores para as decisões corretas do modelo.