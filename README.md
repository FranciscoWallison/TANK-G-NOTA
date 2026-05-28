# 🎸 TANK-G-NOTA

Ferramentas em Python para **afinar** e **detectar nota / corda / casa** em tempo real usando o pedal multiefeitos **M-VAVE TANK-G** (ou qualquer interface de áudio) como entrada.

> Detecta o que você toca pelo áudio — **qual nota**, e com calibração, **qual corda e casa** específica no braço. Inclui um afinador visual.

---

## 🖼️ Interface

### Afinador visual (`tuner.py`)

| Afinado (verde) | Precisa ajustar (amarelo) |
|:---:|:---:|
| ![Afinador — afinado](docs/img/tuner_afinado.png) | ![Afinador — descer](docs/img/tuner_descer.png) |

Agulha de cents com faixas verde (±5¢) / amarelo (±15¢) / vermelho, nota em destaque e indicação de subir/descer.

### Detector de corda + casa (`fret_detector.py --classify`)

```
╔══════════════════════════════════════════════════════════╗
║  🎸  Corda 2 (B3 ) solta    → B3    conf  82.9%    ✓      ║
║       247.64 Hz      +5¢   afinação: standard            ║
╠══════════════════════════════════════════════════════════╣
║  Alternativas:                                            ║
║    Corda 3 (G3 ) casa  4  →   8.1%                        ║
║    Corda 4 (D3 ) casa  9  →   2.8%                        ║
╠══════════════════════════════════════════════════════════╣
║  [e] errou  [u] desfaz última correção  [q] sair         ║
╚══════════════════════════════════════════════════════════╝
```

> As imagens acima são ilustrações da interface renderizadas por [`docs/generate_mockup.py`](docs/generate_mockup.py), fiéis ao layout de `tuner.py`.

---

## ✨ Funcionalidades principais

| Ferramenta | Arquivo | O que faz |
|-----------|---------|-----------|
| 🎯 **Afinador visual** | `fret-detector/tuner.py` | GUI com nota grande, agulha de cents e cores (verde/amarelo/vermelho). Suporta standard, Eb, Drop D/C/B/A. |
| 📡 **Detector de nota** | `fret-detector/fret_detector.py` | Detecta a nota tocada e lista **todas** as posições possíveis no braço. |
| 🧠 **Classificador corda+casa** | `fret-detector/fret_detector.py --classify` | Após calibrar, adivinha **a corda e casa exata** pelo timbre. Modo aprendizado embutido. |
| 🎙️ **Calibração** | `fret-detector/calibrate.py` | Aprende o timbre da SUA guitarra (~5 min) pra melhorar a detecção de corda. |
| 🔧 **Utilitários** | `list_devices.py`, `level_monitor.py` | Descobrir o ID do dispositivo e debugar nível de sinal. |

Documentação completa do pedal (painéis, efeitos, app, firmware) em [`tank-g/`](tank-g/).

---

## 📦 Requisitos

- **Python 3.10+**
- **numpy** e **sounddevice** (`pip install -r fret-detector/requirements.txt`)
- Uma entrada de áudio (o TANK-G via USB-C, ou qualquer interface/microfone)

> Testado no Windows 11 com o TANK-G como sound card USB.

---

## 🚀 Instalação

```bash
git clone https://github.com/FranciscoWallison/TANK-G-NOTA.git
cd TANK-G-NOTA/fret-detector
pip install -r requirements.txt
```

---

## 🎯 Uso

### 1. Descobrir o dispositivo de entrada

```bash
python list_devices.py
```
Anote o ID do seu TANK-G (aparece como `Microphone (USB-Audio)`).

### 2. Afinador visual

```bash
python tuner.py --device 2 --gain 20
```
- Toca uma corda → vê a nota, os cents e a agulha colorida.
- Troca a afinação alvo no dropdown (auto / standard / eb / drop-d…).
- `--smoothing off|low|medium|high` ajusta a estabilidade da leitura.

### 3. Detector de nota (sem calibração)

```bash
python fret_detector.py --device 2 --gain 20 --tuning standard
```
Mostra a nota + todas as casas onde ela poderia ser tocada.

### 4. Classificador de corda+casa (com calibração)

```bash
# 1) calibrar a sua guitarra (uma vez) — som limpo, palhetada firme
python calibrate.py --device 2 --gain 40 --tuning standard

# 2) usar
python fret_detector.py --device 2 --gain 40 --tuning standard --classify
```
No modo `--classify`:
- **`e`** — errou: desce pro próximo do ranking e **aprende** com você
- **`u`** — desfaz a última correção
- **`q`** — sair

> Dica: sinal do TANK-G via USB é fraco — use `--gain 20` a `60`. Veja o nível com `python level_monitor.py --device N`.

---

## 🗂️ Estrutura

```
TANK-G-NOTA/
├── fret-detector/          ← as ferramentas (código Python)
│   ├── tuner.py            ← afinador visual (GUI Tkinter)
│   ├── fret_detector.py    ← detector + classificador
│   ├── calibrate.py        ← calibração da guitarra
│   ├── features.py         ← extração de timbre (FFT)
│   ├── classifier.py       ← k-NN + aprendizado online
│   ├── list_devices.py     ← lista dispositivos de áudio
│   ├── level_monitor.py    ← debug de nível de sinal
│   ├── requirements.txt
│   └── README.md           ← detalhes de cada ferramenta
│
└── tank-g/                 ← documentação do pedal M-VAVE TANK-G
    ├── README.md           ← índice
    ├── 01-especificacoes.md … 10-instalacao-local.md
```

---

## 🧠 Como funciona (resumo técnico)

| Etapa | Técnica |
|-------|---------|
| Captura de áudio | `sounddevice` (WASAPI/WDM-KS no Windows) |
| Detecção de pitch | **YIN** (numpy puro) com **correção de oitava** pra cordas graves |
| Nota | freq → MIDI → nome (A4 = 440 Hz) |
| Features de timbre | centroide espectral, rolloff, ZCR, inarmonicidade, razões de harmônicos |
| Classificação corda+casa | k-NN sobre features calibradas + **viés de ergonomia** (penaliza casas altas) |
| Aprendizado | correções do usuário salvas e reaplicadas (peso 2×) |

---

## ⚠️ Limitações

- **Monofônico** — uma nota por vez (acordes ainda não).
- **Corda exata é ambígua** no áudio mono — precisão de corda fica em ~75-85% após calibração (a **nota** é ~98%).
- Calibração é **por guitarra** — trocar de captador/cordas pede recalibrar.
- Sinal do TANK-G via USB é fraco; depende do `--gain`.

---

## 🛣️ Roadmap

- [x] Afinador visual
- [x] Detector de nota + posições
- [x] Classificador corda+casa com calibração e aprendizado
- [x] Correção de oitava + viés de ergonomia
- [ ] Suavização temporal no detector (mediana + histerese)
- [ ] GUI com diagrama do braço
- [ ] Polifonia (acordes)
- [ ] Modo "tocar junto" (valida tablatura)

---

## 📄 Licença

Código sob licença **MIT** — veja [LICENSE](LICENSE). Use, modifique e distribua livremente.

## 📜 Aviso

Este repositório contém **apenas código próprio e documentação**. Os aplicativos da M-VAVE (M-EFCS, atualizador de firmware) e manuais em PDF são **propriedade da Cuvave/M-VAVE** e **não** estão incluídos aqui (veja `.gitignore`). Baixe-os pelos canais oficiais: <https://www.m-vave.com>.

Projeto pessoal/educacional, sem afiliação com a M-VAVE.
