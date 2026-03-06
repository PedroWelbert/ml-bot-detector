# ml-bot-detector
Projeto final do Workshop PECEGE/POLI USP (Ciência de Dados e IA). Consiste em um pipeline de Machine Learning que analisa padrões de tráfego no access_log do Apache para identificar e alertar sobre bots maliciosos, otimizando o tempo de mitigação manual em servidores de baixo custo.

<img width="2245" height="1587" alt="model_canvas_ml_bot_detector" src="https://github.com/user-attachments/assets/9731adee-5fdd-47e8-84ee-1e8f5885984f" />

# Machine Learning Canvas: Sistema de Detecção de Bots

### 1. Proposta de Valor (O Problema e a Solução)
* **Qual é o problema de negócio?** Instâncias F1-micro no GCP ficam sobrecarregadas (CPU, RAM, Disco) e caem devido a acessos massivos de bots. O processo atual de mitigação é 100% manual, lento e reativo (acessar via SSH, ler logs, reiniciar serviços e bloquear IP no firewall).
* **Qual é a solução proposta pela IA?** Um modelo preditivo de classificação que analisa o comportamento de tráfego de forma contínua para identificar e sinalizar automaticamente (e futuramente bloquear) IPs maliciosos antes da indisponibilidade do serviço.

### 2. Ação e Decisão (Como a IA será usada)
* **Qual decisão o modelo vai apoiar?** A decisão de intervir em um IP específico.
* **Como o usuário vai interagir com isso?** O modelo enviará um alerta automatizado (ex: via Telegram/Discord) indicando qual IP deve ser bloqueado, com a probabilidade de ser um bot. Na fase 2, a ação será a integração direta com o Firewall do GCP para bloqueio automático.

### 3. O Modelo (A Inteligência)
* **Qual é a tarefa de Machine Learning?** Classificação Binária (Supervisionada ou Detecção de Anomalias Não-Supervisionada).
* **Qual é a Variável Alvo (Target)?** `1` = Bot Malicioso (Ataque/Scraping abusivo) | `0` = Tráfego Legítimo (Usuário real ou Bot benigno, como o Googlebot).

### 4. Dados (A Matéria-Prima)
* **Quais são as fontes de dados?** `access_log` do servidor Apache2.
* **Como os dados serão obtidos?** Via exportação para o GCP Cloud Logging ou download via script para ambiente externo.
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
* **Restrições de Latência/Frequência:** O processamento não precisa ser em tempo real (streaming milissegundo). Pode ser em lotes (batch) processando os logs a cada 10 minutos.
