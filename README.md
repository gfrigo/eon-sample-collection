# eon-sample-collection

Sistema de captura de amostras (Raspberry Pi 4 + webcam Logitech C920s + LCD 16x2 + botões).

## Modos de operação

Ao iniciar (`python main.py`), depois de escolher o usuário, o LCD pede para
escolher o modo:

- **Manual** — fluxo original. O operador aperta um dos botões (Bom/Ruim/Péssimo)
  *antes* de capturar a foto, classificando manualmente a amostra. Usado para
  coletar dados rotulados de treino.
- **IA Auto** — o operador aperta apenas o botão central (OK) para capturar.
  A foto é classificada automaticamente pelo modelo `model.tflite` (treinado em
  `eon-aab-ml-train`), e o tier (bom/ruim/pessimo) + confiança são enviados
  junto com a amostra.

Navegação na tela de seleção (usuário e modo): botão 1 = anterior, botão 2 = OK,
botão 3 = próximo.

### Trocar usuário ou modo durante o uso

Com o sistema em espera (idle):

- Segurar o **botão 1** por 3s → volta à tela de seleção de **usuário**.
- Segurar o **botão 3** por 3s → volta à tela de seleção de **modo**
  (Manual / IA Auto).

Toques curtos nesses botões continuam funcionando normalmente no modo Manual
(botão 1 = tier Bom, botão 3 = tier Péssimo).

## Modelo de IA (modo "IA Auto")

O modo IA Auto requer o arquivo `models/model.tflite` (gerado pelo pipeline de
`eon-aab-ml-train` e publicado no GitHub Releases do repositório de treino).

Para baixar a versão mais recente:

```bash
python scripts/download_model.py --repo usuario/eon-aab-ml-train
```

Isso salva `models/model.tflite` e `models/model.version`. Se o arquivo não
existir, o sistema cai automaticamente para o modo Manual.

### Dependências de inferência

A inferência usa `ai-edge-litert` (poucos MB), não a biblioteca `tensorflow`
completa. É o sucessor mantido do antigo `tflite-runtime` e suporta os ops
gerados pelas versões atuais do TensorFlow.
