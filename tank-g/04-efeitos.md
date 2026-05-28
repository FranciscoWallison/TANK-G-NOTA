# 04 — Efeitos (Módulos)

> ⚠️ Para ouvir o efeito de mexer nos knobs, você precisa estar em **modo LIVE** (B+C). No modo PRESET os knobs físicos não alteram nada em tempo real.

A cadeia de sinal (ordem fixa do TANK-G) é aproximadamente:

```
Guitarra → NOISE GATE → AMP (+ EQ) → MOD → DELAY → REVERB → IR CAB → MASTER → Saída
```

---

## 1️⃣ NOISE GATE

Suprime ruído de fundo / chiado quando você não está tocando.

| Controle | Efeito |
|----------|--------|
| **Knob NOISE GATE** | Define o **threshold** — quanto mais à direita, mais agressivo (corta sinais mais altos). |
| **Totalmente à esquerda** | Gate **desligado**. |

> Comece com pouco. Gate alto demais corta a sustain das notas longas.

---

## 2️⃣ AMP — 9 pré-amplificadores

Selecionados pelo knob **TYPE** (9 posições). Os nomes abaixo são as inspirações sonoras; marcas/modelos pertencem aos respectivos donos.

> 📷 Veja a imagem de referência da lista no manual original (FIG-5). A documentação não reproduz a lista exata aqui — confirme no display do app ou no manual físico. Tipicamente cobre limpos americanos, clean fender-style, brit clean, brit crunch, hi-gain modernos e variações de "stack".

### Controles do bloco AMP

| Knob | Função |
|------|--------|
| **TYPE** | Seleciona o modelo de pré (1 dos 9) |
| **GAIN** | Quantidade de ganho/distorção do estágio de pré |
| **TREBLE** | Agudos |
| **MIDDLE** | Médios |
| **BASS** | Graves |
| **VOLUME** | Volume do canal do amp (estágio interno, **não** é o master) |

> Para sons mais "limpos", reduza o GAIN. Para sons mais "pesados", aumente GAIN e ajuste MIDDLE para definir o caráter (médios scoop = metal, médios destacados = rock clássico).

---

## 3️⃣ MOD — Modulação (3 tipos)

Selecionados pelo knob **MOD FX**, que tem **3 zonas**:

| Zona do knob | Tipo de MOD | O knob ajusta |
|--------------|-------------|---------------|
| 1ª (esquerda) | **CHORUS** | parâmetro **MIX** |
| 2ª (meio)     | **PHASER** | parâmetro **DEPTH** |
| 3ª (direita)  | **TREMOLO** | parâmetro **MIX** |
| Entre zonas   | **MOD desligado** (luzes apagam) | — |

| Knob | Função |
|------|--------|
| **MOD FX** | Seleciona tipo + ajusta um parâmetro daquele tipo |
| **MOD SPEED** | Velocidade da modulação (mesma para todos os 3 tipos) |

> Cuidado: para ligar/desligar o MOD você pode (a) girar MOD FX para entre zonas no LIVE, ou (b) usar o **pedal C** no modo LIVE.

---

## 4️⃣ DELAY (3 tipos)

Selecionados pelo knob **DLY MIX**, em **3 zonas**:

| Zona | Tipo de DELAY |
|------|---------------|
| 1ª (esquerda) | **ANALOG** (warm, repetições escurecendo) |
| 2ª (meio)     | **TAPE** (modulado, flutuação típica de fita) |
| 3ª (direita)  | **DUAL** (dois delays em paralelo) |
| Entre zonas   | **DELAY desligado** |

| Knob | Função |
|------|--------|
| **DLY MIX** | Seleciona tipo + ajusta **wet/dry** (proporção do efeito) |
| **DLY TIME** | Velocidade das repetições (tempo entre ecos) |

> Liga/desliga rápido com **pedal B** no modo LIVE.

---

## 5️⃣ REVERB (3 tipos)

Selecionados pelo knob **RVB DECAY**, em **3 zonas**:

| Zona | Tipo de REVERB |
|------|----------------|
| 1ª (esquerda) | **ROOM** (sala, curto e natural) |
| 2ª (meio)     | **SPRING** (mola, vintage de amp) |
| 3ª (direita)  | **CLOUD** (grande, ambient/atmosférico) |
| Entre zonas   | **REVERB desligado** |

| Knob | Função |
|------|--------|
| **RVB DECAY** | Seleciona tipo + ajusta **duração** do reverb |
| **RVB MIX** | Wet/dry (quanto de reverb no sinal final) |

> Liga/desliga rápido com **pedal A** no modo LIVE.

---

## 6️⃣ IR CAB — Simulação de gabinete

IR (Impulse Response) reproduz o caráter sonoro de um **gabinete + microfone + sala**. **Sem IR a saída soa "crua"**, especialmente em fone/PA.

| Posição do knob IR CAB | Significado |
|------------------------|-------------|
| 1ª (slot 1) | **IR desligado** (sinal direto, sem gabinete) |
| 2ª a 9ª (slots 2–9) | **8 IRs carregados** no pedal |

### Importando IRs personalizados

Você pode **substituir** os IRs dos slots 2–9 com IRs próprios via:

- **App M-EFCS** (Android/iOS, via Bluetooth)
- **Software M-EFCS** para PC (Windows/Mac, via USB)

> Ao importar um IR, o IR anterior daquele slot é **sobrescrito**. Faça backup antes se quiser preservar.

Formato típico aceito: `.wav` (geralmente 44.1 ou 48 kHz, mono). Confirme no app a especificação exata.

---

## 🎚️ MASTER

- **Volume final** da saída (após toda a cadeia).
- Luz fica **acesa o tempo todo**, só **apaga** quando o **TUNER** está ligado.
- **Não está atrelado a preset** — é um controle global.

---

## 📝 Notas finais

- Todos os módulos podem ser ligados/desligados independentemente no modo LIVE.
- A **ordem dos módulos** na cadeia é fixa (não dá pra mover REVERB antes do AMP, por exemplo).
- Se quiser apenas reverb sem amp, **desligue o bloco AMP** (pedal D no LIVE).

---

> Próximo: [05 — Afinador e Bluetooth](05-afinador-bluetooth.md)
