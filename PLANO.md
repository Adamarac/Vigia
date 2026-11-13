# Projeto e decisões de implementação — Vigia

Monitor de tela que lê a cor de regiões configuradas e avisa no Telegram quando o estado muda.
Este documento registra o problema, o princípio que orienta o desenho e as decisões técnicas
efetivamente adotadas no código.

## 1. Problema e premissas

- O sistema alvo roda em rede segregada; o acesso é por RDP via CyberArk (PSM). Não há rota de
  rede do sistema para a internet, logo nenhum webhook sai de lá.
- O que existe na máquina local é a **imagem** da tela do sistema (janela do RDP). Tudo o que a
  solução pode usar são os pixels dessa imagem.
- A máquina local tem acesso à internet (ou a um proxy) para chegar em `api.telegram.org`.
- A janela do RDP precisa estar visível na tela local (não minimizada, não coberta, estação não
  bloqueada) enquanto o monitor roda. É um requisito operacional, não um detalhe.
- **Restrição de postura:** a ferramenta não pode parecer um capturador de tela. Nenhuma imagem é
  gravada, transmitida ou retida; leem-se apenas pixels dos retângulos configurados, em baixa
  frequência, e só números (cor, cobertura, estado) saem do processo. Ver 2.1.
- O sistema sinaliza estado por cor de fundo de um elemento (semáforo, célula, LED).

## 2. Arquitetura

O código segue uma arquitetura em camadas no estilo portas e adaptadores. O núcleo de domínio
não conhece tela, rede, disco nem interface gráfica; as camadas externas o adaptam ao mundo. As
dependências entre componentes são declaradas como `Protocol` e injetadas na raiz de composição,
o que torna o núcleo testável sem uma tela ou uma conexão reais.

```
máquina local (Windows)

  janela RDP ──pixels──▶ leitura (amostra de pontos, só das regiões configuradas)
                              │ Amostra de cores
                              ▼
                         domínio: classificação por cobertura
                              │ significado por região
                              ▼
                         domínio: máquina de estados (debounce, cooldown)
                              │ transição
                              ▼
                         notificação ──texto──▶ Telegram Bot API

  ui (seletor/painel) ──grava──▶ config.toml
```

| Camada | Responsabilidade |
|---|---|
| `dominio` | Objetos de valor e regras de negócio puros, sem I/O. |
| `leitura` | Adaptadores que leem pixels da tela e tratam DPI. |
| `notificacao` | Entrega de mensagens de texto (Telegram, console, composto). |
| `config` | Modelos imutáveis e leitura/gravação de TOML. |
| `app` | Orquestração do ciclo (monitor, executor) e raiz de composição. |
| `ui` | Painel e overlays em tkinter. |

### 2.1 Princípio: ler cores, não tirar fotos

O processo é um observador contínuo que lê alguns pixels, não um capturador que tira fotos da
tela. O que ele faz e o que nunca faz:

| Faz | Nunca faz |
|---|---|
| Lê pixels **apenas dos retângulos configurados**, como uma grade de pontos dentro deles | Ler o monitor ou a janela inteira |
| Mantém a leitura em memória só durante o ciclo e descarta | Gravar PNG/JPG em disco, inclusive arquivos temporários |
| Guarda e registra apenas números: cor dominante, cobertura, estado, hora | Enviar imagem para o Telegram ou para qualquer lugar |
| Lê em intervalo baixo (5 s por padrão) e só notifica em transição de estado | Gravar vídeo ou manter sessão contínua de duplicação de tela |
| Faz uma única conexão de saída, texto, para `api.telegram.org` | Abrir portas de entrada ou falar com outros hosts |

Dois modos de leitura, escolhidos por região:

- **Amostragem (padrão):** uma grade de pontos dentro do retângulo (ex. 5×5 = 25 pixels) lida com
  `GetPixel` do GDI. Não existe bitmap em nenhum momento, só uma lista de valores RGB. É
  suficiente para a cor de fundo de um semáforo, célula ou LED.
- **Retângulo (só quando precisa):** leitura do retângulo exato da região com `mss.grab(bbox)`,
  em memória, para regiões que exigem cobertura mais fina. O buffer é descartado ao fim do ciclo.

A restrição de "não capturar imagens" é verificada por um teste de arquitetura, não apenas
prometida: `tests/test_sem_imagens.py` falha se o pacote passar a importar bibliotecas de imagem
(PIL, OpenCV, imageio) ou usar termos como `.png`, `sendPhoto` ou `.save(`.

### 2.2 Decisões

| Tema | Decisão | Motivo |
|---|---|---|
| Linguagem | Python 3.11+ com `uv` e build `hatchling` | Bibliotecas maduras; ambiente e scripts reprodutíveis |
| Leitura | Amostragem de pontos por região (GDI `GetPixel`); `mss.grab(bbox)` só do retângulo quando a região exigir | Nunca lê o monitor inteiro; nenhum bitmap persistido; independe do cliente RDP |
| Frequência | 5 s por padrão | Alarme por cor não precisa de resposta em 1 s |
| Classificação | **Cobertura de cor**: fração de pontos dentro da tolerância de cada cor configurada | Robusto a texto sobre o fundo, anti-aliasing e bordas; cor média falha nesses casos |
| Config | TOML com modelos imutáveis (`dataclass` congeladas) e validação estrita de chaves | Editável à mão; chave desconhecida vira erro; gravação atômica |
| Notificação | Só em **transição de estado**, com debounce e cooldown | Evita spam a cada ciclo |
| Telegram | `requests` direto na Bot API (`sendMessage`), com retry e remoção do token dos erros | Sem dependência pesada; token via variável de ambiente, fora do TOML |
| UI | `tkinter` (biblioteca padrão) para painel, seletor e overlays | Zero instalação extra |
| DPI | `SetProcessDpiAwarenessContext` no início do processo | Sem isso, coordenadas do overlay e da leitura divergem com escala 125/150 % |

## 3. Modelo de configuração (`config.toml`)

```toml
[geral]
intervalo_s        = 5.0    # período de leitura
debounce_amostras  = 3      # amostras iguais consecutivas para confirmar estado
cooldown_s         = 300.0  # não repetir a mesma transição antes disso
estado_desconhecido_notifica = false

[leitura]
modo    = "amostragem"      # amostragem (GetPixel em grade) | retangulo (grab só do rect)
grade   = [5, 5]            # pontos por região no modo amostragem

[notificador.telegram]      # opcional; sem ela, as mensagens vão para o console
chat_id = "123456789"       # o token vem da variável TELEGRAM_BOT_TOKEN
mensagem_padrao = "[{regiao}] {significado} ({cor_hex}) às {hora}"
token_env = "TELEGRAM_BOT_TOKEN"

[[regiao]]
nome = "Bomba P-101"
rect = [1240, 310, 60, 24]  # x, y, largura, altura (pixels físicos)
# modo = "retangulo"        # opcional: sobrescreve [leitura].modo nesta região

  [[regiao.regra]]
  cor            = "#FF0000"
  tolerancia     = 40.0     # distância RGB (0–441)
  cobertura_min  = 0.5
  significado    = "FALHA"
  mensagem       = "🔴 {regiao}: FALHA detectada às {hora}"
  notificar      = true

  [[regiao.regra]]
  cor            = "#00AA00"
  tolerancia     = 40.0
  cobertura_min  = 0.5
  significado    = "NORMAL"
  mensagem       = "🟢 {regiao} voltou ao NORMAL"
  notificar      = true
```

Placeholders disponíveis na mensagem: `{regiao}`, `{significado}`, `{significado_anterior}`,
`{cor_hex}`, `{cobertura}`, `{hora}`, `{data}`. Chaves desconhecidas em qualquer seção são
rejeitadas na carga, para que um nome digitado errado não passe em silêncio.

## 4. Algoritmo de detecção

```
a cada ciclo (intervalo_s):
  para cada região:
     amostra = cores dos pontos da grade (GetPixel)       # modo amostragem
               ou cores amostradas do retângulo (mss)     # modo retangulo
     para cada regra:
        dist      = distância RGB de cada ponto até a cor da regra
        cobertura = fração dos pontos com dist <= tolerancia
     vencedora = regra com maior cobertura
     leitura   = vencedora.significado se cobertura >= cobertura_min senão "DESCONHECIDO"
     máquina de estados da região recebe a leitura:
        - confirma o novo estado só após `debounce_amostras` iguais seguidas
        - se o estado confirmado mudou e passou o cooldown da transição → emite transição
     amostra descartada; ficam só (significado, cobertura, cor_dominante)
  transições → política de notificação (template da regra; fallback mensagem_padrao) → notificador
```

- A comparação é por distância euclidiana em RGB, simples e rápida.
- A primeira confirmação após iniciar não gera mensagem (evita um alerta ao ligar).
- A política pode descartar a transição quando a regra tem `notificar = false`, ou quando o
  estado é `DESCONHECIDO` e `estado_desconhecido_notifica` é `false`.
- Em nenhum momento existe um frame do monitor inteiro em memória.

## 5. Estrutura do projeto

```
OCR-Telegram/
  pyproject.toml            # uv, deps, scripts, configuração de pytest e ruff
  config.toml               # configuração de execução (fora do git)
  .env                      # TELEGRAM_BOT_TOKEN (fora do git)
  PLANO.md
  README.md
  src/vigia/
    __main__.py             # CLI: ui | run | ler | selecionar | mostrar | testar-telegram
    ambiente.py             # carregamento do .env e logging
    dominio/                # cor, geometria, amostra, regras, classificação, estado, mensagens
    leitura/                # DPI, amostragem GetPixel, retângulo via mss
    notificacao/            # Telegram, console, composto
    config/                 # modelos imutáveis e repositório TOML
    app/                    # monitor, executor, fábrica (raiz de composição)
    ui/                     # seletor, destaque, diálogo de regra, painel
  tests/                    # testes unitários; dublês de leitor, notificador e relógio
```

## 6. O que foi construído

- **Núcleo de linha de comando:** leitura por GDI e por retângulo, classificação por cobertura,
  máquina de estados com debounce e cooldown, notificação no Telegram (com retry) e no console,
  renderização segura de templates (placeholder desconhecido não derruba o ciclo) e os comandos
  `run` e `ler`.
- **Seleção e calibração pela interface:** overlay em tela cheia para marcar regiões com o mouse;
  painel que mostra, por região, a cor lida agora, o estado confirmado, o candidato em debounce e
  a cobertura de cada regra; diálogo que cria uma regra a partir das cores dominantes lidas; e o
  destaque numerado das regiões por cima da tela, para conferir o posicionamento.
- **Qualidade:** suíte com 104 testes passando sem precisar de tela (amostras sintéticas e dublês
  injetados), lint com `ruff` sem apontamentos e a guarda de arquitetura contra imagens.

## 7. Critérios de aceite

- Selecionar regiões com o mouse e persistir; reabrir e ver as mesmas.
- Cada região aceita múltiplas cores, cada uma com significado e mensagem próprios.
- Transição de cor gera **uma** mensagem; a recuperação também; sem repetição dentro do cooldown.
- Ruído de até `debounce_amostras - 1` ciclos não gera alerta.
- Testes unitários passam sem precisar de tela.
- Nenhum arquivo de imagem é criado em nenhuma operação; um teste vigia o pacote e as dependências.

## 8. Riscos e mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Ferramenta confundida com capturador de tela | Bloqueio pelo EDR, questionamento de segurança | Leitura só das regiões por amostragem; nada em disco; só texto na rede; código aberto e guarda de arquitetura; declarar ao time de segurança antes de rodar |
| CyberArk bloqueia a leitura (pixels pretos) | Inviabiliza a leitura por software | Diagnóstico "tudo preto" por região acusa o problema; alternativa por hardware (placa de captura) fica fora do escopo |
| Estação bloqueia / janela minimizada ou coberta | Monitor cego | Diagnóstico por ciclo (tudo preto, ponto fora da tela); requisito operacional de manter a janela visível |
| Janela do RDP movida ou redimensionada | Regiões apontam para o lugar errado | Comando "Mostrar regiões na tela" para conferir o posicionamento |
| Escala de DPI | Coordenadas erradas | DPI awareness no início do processo |
| Cor com texto por cima ou gradiente | Classificação instável | Cobertura em vez de cor média; debounce antes de confirmar |
| Sem internet / proxy | Mensagem perdida | Retry com backoff no envio; `HTTPS_PROXY` |
| Token vazado | Bot sequestrado | Token fora do TOML, via variável de ambiente; removido dos textos de erro no log |
