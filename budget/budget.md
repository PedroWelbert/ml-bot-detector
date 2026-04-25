# 📊 Relatório de Estimativa de Custos: Sistema de Detecção de Bots

**Arquitetura:** Serverless (GCP) com inferência de Machine Learning sob demanda.  
**Frequência de Execução:** A cada 5 minutos (Aproximadamente 8.640 execuções / mês).

---

### 1. Google Cloud Storage (Armazenamento do Modelo)

- **O que faz:** Guarda o arquivo `modelo_rf_bot_detector.pkl` de 23 MB.
- **Cota Gratuita Mensal do GCP:** 5 GB de armazenamento Standard.
- **Nosso Consumo:** 0,023 GB (menos de 0,5% da cota).
- **Custo Estimado:** R$ 0,00

### 2. Google Cloud Logging (Coleta de Logs do Apache)

- **O que faz:** Recebe e armazena os registros de acesso (`access_log`) da VM.
- **Cota Gratuita Mensal do GCP:** 50 GB de ingestão e armazenamento de logs.
- **Nosso Consumo:** Apenas os metadados de texto dos últimos 5 minutos de acesso de um blog padrão. Geralmente consome menos de 0,5 GB por mês (1% da cota).
- **Custo Estimado:** R$ 0,00

### 3. Google Cloud Run / Cloud Functions (Processamento Python)

- **O que faz:** Acorda de 5 em 5 minutos, baixa o `.pkl`, lê o Cloud Logging, corre o Random Forest e notifica o Discord.
- **Cota Gratuita Mensal do GCP:**
  - 2 Milhões de requisições.
  - 360.000 GB-segundos de memória.
  - 180.000 vCPU-segundos de processamento.
- **Nosso Consumo:** \* 8.640 requisições (0,43% da cota).
  - Assumindo que a função leve 2 segundos para correr usando 512MB de RAM, o consumo será de ~8.640 GB-segundos (2,4% da cota de memória).
- **Custo Estimado:** R$ 0,00

### 4. Google Cloud Scheduler (Gatilho Temporal)

- **O que faz:** Dispara o webhook (Cron) a cada 5 minutos para o Cloud Run.
- **Cota Gratuita Mensal do GCP:** 3 Jobs (tarefas) por conta de faturamento.
- **Nosso Consumo:** 1 Job exclusivo para o detetor de bots (33% da cota).
- **Custo Estimado:** R$ 0,00

### 5. Saída de Rede (Network Egress para o Discord)

- **O que faz:** Envia um pequeno pacote JSON com o IP e a probabilidade de ser bot para a API do Discord.
- **Cota Gratuita Mensal do GCP:** 200 GB de saída para a internet.
- **Nosso Consumo:** Kilobytes (0,0001% da cota).
- **Custo Estimado:** R$ 0,00

---

## 💰 Custo Total Estimado: R$ 0,00 / Mês

---

### **Conclusão Técnica para a Diretoria:**

A arquitetura foi desenhada utilizando o modelo de computação **Serverless** (Sem servidor). Isso significa que não estamos a pagar por máquinas ociosas aguardando tráfego. O sistema liga, executa o cálculo de Inteligência Artificial em cerca de 2 segundos, e desliga completamente.

Como o tráfego do blog e a frequência de checagem (a cada 5 ou 10 minutos) se encaixam com enorme folga no **"Always Free Tier"** (Nível Gratuito Permanente) do Google Cloud, a empresa ganha uma camada ativa de segurança com Inteligência Artificial sem adicionar nenhum custo recorrente de infraestrutura.
