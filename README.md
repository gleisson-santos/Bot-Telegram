# 🤖 Gateway Telegram <-> Make (Bot-Telegram)

Este projeto implementa um **Gateway Bidirecional** de automação integrando o **Telegram** e o **Make.com** (antigo Integromat). O bot atua como uma ponte para ingestão de conteúdo (recebimento de fotos) e publicação automática em canais.

![Bidirectional](https://img.shields.io/badge/Flow-Bidirectional-blue)
![Telegram](https://img.shields.io/badge/Plataform-Telegram-blue)
![Make](https://img.shields.io/badge/Backend-Make.com-purple)

## 🔄 Fluxo de Funcionamento

O sistema opera em duas vias:

### 1. Ingestão (Telegram ➡️ Make)
Ao receber uma imagem (ou mensagem encaminhada) no chat privado ou grupo:
1.  O bot identifica se é uma imagem única ou galeria (álbum).
2.  No caso de galerias, seleciona automaticamente a imagem de **maior resolução**.
3.  Extrai metadados importantes: legenda (caption), nome do chat de origem e ID.
4.  Envia um JSON consolidado para o Webhook do Make.com configurar automações (ex: salvar em banco, repostar em outra rede).

### 2. Publicação (Make ➡️ Telegram)
O bot expõe um **Servidor HTTP Webhook** (`POST /webhook`) que permite ao Make enviar comandos de volta para o Telegram:
1.  O Make envia um JSON contendo a URL da imagem e a legenda.
2.  O bot baixa a imagem e a publica automaticamente no **Canal do Telegram** configurado (`TELEGRAM_CHANNEL_ID`).
3.  Responde com status de sucesso para o Make.

## 🛠️ Tecnologias

*   **Linguagem**: Python 3.x
*   **Libs Principais**: `python-telegram-bot` (Wrapper assíncrono), `requests`, `python-dotenv`.
*   **Servidor Web**: `http.server` (Python Stdlib) rodando em thread paralela para Health Checks e Webhooks.

## ⚙️ Configuração

### Variáveis de Ambiente
Obrigatórias para execução:

```env
TELEGRAM_TOKEN=12345:SeuTokenAqui
MAKE_WEBHOOK_URL=https://hook.us1.make.com/seuwebhook
TELEGRAM_CHANNEL_ID=-100123456789  # ID do canal para repostagem
PORT=5000                           # Porta do servidor HTTP
```

### Endpoints HTTP
*   `GET /ping`: Health Check simples ("Pong! Online").
*   `POST /webhook`: Endpoint para receber dados do Make.
    *   **Payload Esperado**:
        ```json
        {
          "file_url": "https://exemplo.com/foto.jpg",
          "caption": "Legenda da publicação",
          "source_chat_name": "Origem (opcional)",
          "source_chat_id": "123 (opcional)"
        }
        ```

## 🚀 Como Rodar

1.  Clone o repositório e instale as dependências:
    ```bash
    pip install -r requirements.txt
    ```
2.  Execute o bot:
    ```bash
    python bot.py
    ```

## 📝 Licença

Desenvolvido por [Gleisson Santos](https://github.com/gleisson-santos).
