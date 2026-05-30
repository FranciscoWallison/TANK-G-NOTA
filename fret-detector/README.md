# 🎸 Fret Detector

Detector de nota + corda/casa + **afinador visual** em tempo real usando o **TANK-G** (ou qualquer entrada de áudio) como input.

> 🎛️ **Studio** (`studio.py`): app único com menu — dispositivo, afinador, treino, velocidade, monitor pelo fone e o jogo, tudo numa janela. **Comece por aqui.**
> 🎯 **Tuner**: afinador visual GUI (Tkinter) — nota grande, agulha de cents, cores.
> 📡 **v1**: detecta a **nota** e mostra **todas** as casas possíveis (até 6).
> 🧠 **v2**: após **calibrar a sua guitarra** (~5 min), tenta adivinhar **a corda+casa exata** que você está tocando, com **modo aprendizado** (você corrige, ele aprende).

---

## 🎛️ TANK-G Studio (app unificado)

```powershell
python studio.py                 # auto-detecta o TANK-G
python studio.py --device 2 --gain 40
```

Menu com: **Dispositivo** (identifica o TANK-G + escolhe o fone), **Afinador**, **Treino** (calibração **guiada** corda × casa × 3 dinâmicas + validação livre: nota + corda + casa + **solta/pressionada**), **Monitor** (reproduz a guitarra no fone do PC — full-duplex), **Velocidade** (easy/normal/hard), **Metrônomo** (BPM/acento + pulse visual; toca no jogo com **pré-contagem 3-2-1** alinhada ao beat 0) e **Jogar música** (valida nota + solta/pressionada). **ESC** volta ao menu. Config salva em `settings.json`.

| Peça | Arquivo |
|------|---------|
| App + estado + navegação | `studio.py` |
| Telas (Menu/Device/Tuner/Train) | `screens.py` |
| Helpers de UI Pygame | `ui.py` |
| Monitor pelo fone (full-duplex) | `audio_engine.py` |

---

## ⚡ Quick start

```powershell
# 1. (uma vez só) instalar dependências
pip install -r requirements.txt

# 2. listar dispositivos pra descobrir o ID do TANK-G
python list_devices.py

# 3. rodar — auto-detecta TANK-G
python fret_detector.py
```

Toca uma nota na guitarra e o terminal mostra:

```
╔══════════════════════════════════════════════════════════╗
║  Nota: E4     329.63 Hz   ✓    +2¢   afinação: standard  ║
╠══════════════════════════════════════════════════════════╣
║  1ª (E4)   solta  |●·······················|             ║
║  2ª (B3)  casa  5 |·····●··················|             ║
║  3ª (G3)  casa  9 |·········●··············|             ║
║  4ª (D3)  casa 14 |··············●·········|             ║
║  5ª (A2)  casa 19 |···················●····|             ║
╚══════════════════════════════════════════════════════════╝
```

---

## 🎛️ Opções

```powershell
python fret_detector.py --help
```

| Flag | Default | Exemplo |
|------|---------|---------|
| `--device N` | auto | `--device 5` (força ID específico) |
| `--tuning NOME` | `standard` | `--tuning drop-b` (pra Slipknot) |
| `--list` | — | lista afinações suportadas |

### Afinações suportadas

| Nome | Cordas (6ª → 1ª) | Usada por |
|------|------------------|-----------|
| `standard` | E2 A2 D3 G3 B3 E4 | maioria das músicas |
| `drop-d` | D2 A2 D3 G3 B3 E4 | grunge, rock alternativo |
| `drop-c` | C2 G2 C3 F3 A3 D4 | nu-metal mais leve |
| `drop-b` | B1 F#2 B2 E3 G#3 C#4 | **Slipknot — Duality** ⭐ |
| `drop-a` | A1 E2 A2 D3 F#3 B3 | hardcore moderno |
| `eb` | D#2 G#2 C#3 F#3 A#3 D#4 | Slash, Hendrix, Pantera |

---

## 🔌 Conectando o TANK-G

1. Conecte o pedal no PC via **USB-C de dados** (não cabo só de carga)
2. Ligue o pedal
3. Rode `python list_devices.py` — deve aparecer algo como:
   ```
   ID  CHs  Nome
   --  ---  ----
   5   1    Microphone (USB-Audio)   ← TANK-G
   ```
4. Rode `python fret_detector.py` — auto-detecta `USB-Audio`

> Se quiser **monitorar pelo fone do PC** enquanto roda o detector, abra o M-EFCS e ative **Loopback**.

---

## 🧠 Como funciona (resumo técnico)

| Componente | Algoritmo / Lib |
|------------|----------------|
| Captura de áudio | `sounddevice` (WASAPI/WDM-KS no Windows) |
| Janela | 2048 samples @ 44.1kHz = ~46ms |
| Hop | 1024 samples = processa 43 vezes/s |
| Pitch detection | **YIN** (implementação compacta em numpy) |
| Nota | conversão freq → MIDI → nome (A4 = 440Hz = MIDI 69) |
| Posições | varre as 6 cordas, calcula casa = `midi_alvo - midi_corda_solta` |

**Latência total estimada**: ~70 ms (46 ms janela + ~20 ms callback + render).

---

## ⚠️ Limitações da v1

| Limitação | Por quê | Roadmap |
|-----------|---------|---------|
| **Só 1 nota por vez** | Acordes confundem YIN | v2: pitch polifônico (FFT + peaks) |
| **Não sabe qual casa "de verdade"** | Áudio mono não tem info de corda | v2: timbre + heurística (corda mais usada) |
| **Pode errar oitava** | YIN às vezes detecta sub-harmônico | v1.1: filtro de outliers + suavização |
| **Latência ~70ms** | Buffer grande pra precisão | v1.1: buffer menor + janela Hanning |
| **Sem GUI** | Terminal | v3: app Tkinter/PyQt com diagrama visual |

---

## 🐛 Problemas?

| Sintoma | Tente |
|---------|-------|
| `TANK-G não encontrado` | Conferir USB conectado e pedal ligado → rodar `list_devices.py` |
| `OSError: Invalid device` | `--device N` com ID errado → checar `list_devices.py` |
| Não detecta nota | Subir volume MASTER do pedal; afastar do amp |
| Detecta nota errada (oitava) | Tente knob de GAIN mais baixo (menos saturação ajuda YIN) |
| Várias notas piscando | Você tá tocando acorde — v1 é só mono |

---

---

## 🎯 Afinador visual (GUI)

```powershell
python tuner.py --device 2 --gain 20
```

Janela Tkinter com:

- **Nota gigante** detectada (E, A, D, G, B, F#, etc.)
- **Frequência em Hz** abaixo
- **Régua de cents** (−50 a +50) com agulha colorida:
  - 🟢 verde dentro de ±5¢ (afinado)
  - 🟡 amarelo até ±15¢ (perto)
  - 🔴 vermelho >±15¢ (longe)
- **↑ subir / ↓ descer** com o quanto falta
- **Seletor de afinação alvo** (auto, standard, Eb, Drop D, Drop B, Drop A, Drop C)

### Modos do alvo

- **auto** (default) — mostra a nota cromática mais próxima. Use pra ver o que está saindo.
- **standard / eb / drop-X** — força como alvo as **6 cordas** dessa afinação. O afinador escolhe automaticamente qual corda você está afinando (a mais próxima da freq detectada). Útil pra afinar corda a corda sem se confundir com semitons vizinhos.

> Exemplo: você quer afinar pra **Eb**, toca a 6ª corda. O sistema vê 80Hz → mais próximo de Eb2 (77.78Hz) → mostra "Eb2" + cents. Aperta a tarraxa até o verde acender.

---

## 🧠 v2 — Detecção de corda + casa (com calibração)

A v2 usa **features de timbre** (centroide espectral, inarmonicidade, razões de harmônicos…)
para tentar adivinhar **qual corda específica** você está tocando. Como o áudio é mono,
isso só funciona depois de **calibrar a sua guitarra** — o sistema aprende como cada corda
soa no seu setup específico.

### Fluxo v2

```powershell
# 1. (uma vez) calibrar — vai pedir pra você tocar cada (corda, casa)
python calibrate.py --device 2 --gain 20 --tuning standard

# 2. usar com classificação
python fret_detector.py --device 2 --gain 20 --classify
```

### Calibração (~5 minutos)

Você vai tocar **2 amostras por posição** em **4 casas (0, 5, 7, 12)** por corda = **48 amostras**.
O script guia: mostra que corda+casa tocar, espera 1.5s capturando, valida que a nota detectada
bate com o esperado.

**Dicas pra calibração funcionar bem:**

- ✅ Use o pedal com **som limpo** — desative distorção (BYPASS no M-EFCS) durante a calibração
- ✅ Palhete **firme e consistente** — palhetada de pé, deixa soar
- ✅ Posição mais centrada possível na corda (mid-pickup)
- ⚠️ Recalibre se trocar de guitarra, captador, ou cordas

**Flags úteis:**

| Flag | Default | Exemplo |
|------|---------|---------|
| `--frets` | `0,5,7,12` | `--frets 0,3,5,7,12,17` (mais resolução) |
| `--samples` | `2` | `--samples 3` (mais robusto, leva mais tempo) |
| `--resume` | — | retoma sem apagar calibração anterior |
| `--output` | `calibration.json` | caminho de saída |

### Modo aprendizado (em runtime)

Depois de carregar `--classify`, você vê algo como:

```
╔══════════════════════════════════════════════════════════╗
║  🎸  Corda 4 (D)  casa 7  → A3   conf 82.4% ✓            ║
║      220.00 Hz    +0¢   afinação: standard               ║
╠══════════════════════════════════════════════════════════╣
║  Alternativas:                                            ║
║    Corda 3 (G ) casa  2 → 11.0%                          ║
║    Corda 5 (A ) casa 12 →  4.1%                          ║
║    Corda 6 (E ) casa 17 →  2.5%                          ║
╠══════════════════════════════════════════════════════════╣
║  [e] errou  [u] desfaz última correção  [q] sair         ║
╚══════════════════════════════════════════════════════════╝
```

**Teclas:**
- **`e`** — Errou. Sistema desce pra próxima do ranking e **grava como exemplo** (aprende com você).
- **`u`** — Desfaz última correção (caso tenha apertado `e` por engano).
- **`q`** — Sair.

As correções ficam em `corrections.json` e são carregadas em sessões futuras.

### Precisão esperada

| Cenário | Precisão (corda correta no top-1) |
|---------|----------------------------------|
| Sem calibração (heurística pura) | ~55% |
| Após calibração inicial | ~75–85% (varia por guitarra) |
| Após +20 correções na mesma guitarra | ~85–92% |

> Nota é praticamente perfeito (~98%). A dificuldade é só **qual corda** — fisicamente
> ambíguo no áudio mono.

---

---

## 🎮 Jogo (Guitar Hero com guitarra real)

`game.py` — notas caem em 6 lanes (uma por corda); toque a nota na guitarra quando ela cruza a linha de acerto. Valida a **nota** (pitch); a corda/casa é dica.

```powershell
python game.py --device 2 --gain 40 --chart escala_mi   # com guitarra
python game.py --mock --chart escala_mi                 # ESPAÇO = tocar (sem guitarra)
python game.py --difficulty hard                        # easy / normal / hard
python game.py --list                                   # músicas embutidas
```

| Peça | Arquivo |
|------|---------|
| Jogo Pygame (loop, queda, julgamento, HUD) | `game.py` |
| Captura + pitch + **onset** (detecção de ataque) | `audio_engine.py` |
| Músicas/sequências | `charts.py` |

- **Onset detection**: só o *ataque* (pluck) dispara um acerto — nota sustentada não conta várias vezes.
- **Julgamento**: Perfect (≤70 ms) / Good (≤150 ms) / Miss; `--audio-offset-ms` compensa latência.

---

## 📍 Roadmap

- [x] **v1** — Detecção de nota + lista de posições possíveis ✅
- [x] **v2** — Calibração + classificador + modo aprendizado ✅
- [x] **v3** — Jogo Guitar Hero (onset + julgamento de timing) ✅
- [x] **v4** — App unificado TANK-G Studio (menu + monitor pelo fone) ✅
- [x] **v6** — Metrônomo (motor + tela + no jogo) com **pré-contagem 3-2-1** e **pulse visual** ✅
- [x] **v5** — Features v2 (8, c/ sustain) + calibração guiada + validação solta/pressionada ✅
- [ ] Trilha/metrônomo tocando junto no jogo
- [ ] Editor de chart / importar MIDI/tablatura
- [ ] Polifonia (acordes)
- [ ] GUI Tkinter com diagrama do braço
