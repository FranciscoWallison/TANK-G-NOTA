# 06 — Conexões e Cenários de Uso

O TANK-G é versátil — dá pra usar em casa, palco, gravação e como interface de áudio. Aqui estão os cenários mais comuns.

> 📌 **Regra de ouro:** **desligue** os equipamentos (amp/PA/interface) **antes** de plugar/desplugar qualquer cabo. Evita pop e protege seus alto-falantes.

---

## 🎧 1. Tocando em casa com fone

Cenário mais simples — só você e o pedal.

```
Guitarra ──[1/4"]──> [INPUT] TANK-G [PHONES] ──[P10/P2]──> Fone
```

| Passo | O que fazer |
|-------|-------------|
| 1 | Plugue a **guitarra** no **INPUT** (1/4") |
| 2 | Plugue o **fone** na saída **PHONES** |
| 3 | Ligue o pedal |
| 4 | Ajuste o **MASTER** baixo, suba aos poucos |
| 5 | Selecione um preset bonito (BANK + A/B/C/D) |

> Use um **IR CAB ativo** (slots 2–9) para som mais cheio no fone. Sem IR, o som fica "cru".

---

## 🔊 2. Conectado a amplificador de guitarra

### Opção A — Entrada normal do amp (input)
Útil em amps simples. Mas você está enviando a simulação de amp do TANK-G para a entrada de **outro amp**, o que pode "engordurar" o tom.

```
Guitarra ──> TANK-G [OUTPUT A/B] ──> Input do amp
```

> Dica: **desligue o IR CAB** (slot 1) e/ou **desligue o bloco AMP** (pedal D no LIVE) para evitar simulação dupla.

### Opção B — Loop de efeito / FX Return do amp
Bypassa o pré-amp do amplificador → você ouve só a saída do TANK-G amplificada.

```
Guitarra ──> TANK-G [OUTPUT] ──> FX Return do amp
```

> Esse é o jeito **mais fiel** ao som do TANK-G quando usando um amp tradicional.

---

## 🎚️ 3. Mixer / PA / sistema FRFR (palco)

O melhor cenário para ouvir o som real do TANK-G no PA.

```
Guitarra ──> TANK-G [XLR balanceada] ──[cabo XLR]──> Mixer / Caixa FRFR
```

| Vantagens da XLR balanceada |
|-----------------------------|
| Aceita cabos longos sem ruído |
| Conecta direto no canal de microfone do mixer |
| Padrão de palco profissional |

> No mixer, comece com o **gain baixo**. Os tomadas balanceadas costumam ter mais sinal do que linha não-balanceada.

---

## 📱 4. Gravação no celular

```
Guitarra ──> TANK-G [Saída de áudio (recording)] ──[cabo TRRS específico]──> celular (P2)
```

| Detalhe importante |
|--------------------|
| Você precisa do **cabo de gravação correto** (4 polos / TRRS). Cabo de fone comum (3 polos / TRS) **não funciona** — não retorna áudio. |
| O cabo costuma vir no kit ou ser vendido separado pela M-VAVE. |

Apps de gravação no celular reconhecem o pedal como entrada de microfone externa.

---

## 💻 5. Sound card USB para o PC (gravação / DAW / streaming)

O TANK-G funciona como **interface de áudio USB** quando conectado ao computador.

```
Guitarra ──> TANK-G [USB-C] ──[cabo USB]──> PC / Mac
```

### Setup

| Passo | O que fazer |
|-------|-------------|
| 1 | Conecte o **USB-C** do TANK-G no PC/Mac |
| 2 | (Windows) o sistema detecta como dispositivo de áudio classe USB — geralmente nome **"M-Vave"** ou **"TANK-G"** |
| 3 | Na sua **DAW** (Reaper, Ableton, FL Studio, GarageBand, etc.), selecione o TANK-G como entrada de áudio |
| 4 | Grave o sinal **já processado** (com amp, efeitos, IR) — DI não está disponível por essa saída |

### Latência

- Windows: instale **ASIO4ALL** se a latência via WDM/Direct estiver alta.
- Mac: o macOS reconhece nativo com baixa latência.

### Streaming / videoconferência

Você pode usar o TANK-G como entrada de áudio em apps como OBS, Zoom, Discord — basta selecionar o dispositivo como entrada de microfone.

---

## 🎚️ 6. Duas saídas em paralelo (estéreo improvisado)

O TANK-G tem **OUTPUT A** (no bloco principal) e **OUTPUT B** (no painel traseiro). Em alguns cenários você pode usar as duas:

- **OUTPUT A** → ampli / mixer 1
- **OUTPUT B** → outro destino (monitor, segunda PA, gravação)
- **XLR** → terceira via balanceada

> O sinal nas duas saídas é o **mesmo** (não é estéreo real com canais L/R independentes em todas as situações — confirme no app dependendo do firmware).

---

## 🚫 Coisas que NÃO funcionam

| Tentativa | Por que não |
|-----------|-------------|
| Fonte de pedal 9V (Boss-style) | TANK-G é **5V USB**, não 9V. Vai queimar. |
| Cabo P2/P10 estéreo no INPUT | INPUT é **mono** 1/4". Use cabo mono de instrumento. |
| Cabo de fone comum no recording out do celular | Precisa de **TRRS (4 polos)**, não TRS (3 polos). |
| Ligar IR + IR de outro pedal/plugin | "IR duplo" = som muito processado. Desligue um dos dois. |

---

> Próximo: [07 — App e Software M-EFCS](07-app-software.md)
