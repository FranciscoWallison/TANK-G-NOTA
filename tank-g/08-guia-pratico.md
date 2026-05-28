# 08 — Guia Prático (Workflow)

Passo a passo das tarefas mais comuns no TANK-G. Pode usar como **checklist** ao vivo ou em casa.

---

## 🟢 Tarefa 1 — Setup inicial (primeira vez ligando)

1. **Carregue a bateria** primeiro: USB-C 5V/2A por 4 horas até o LED de carga ficar 🔵 azul
2. Plugue **guitarra** no INPUT e **fone** na saída PHONES
3. **MASTER** no mínimo (girado totalmente para a esquerda)
4. Pressione o **botão de power** atrás
5. Tela mostra um número de banco (ex.: `1`)
6. Pise em **A** → carrega o preset 1A
7. Suba o **MASTER** lentamente até um nível confortável
8. Pronto — você está em modo PRESET, tocando o 1A 🎸

---

## 🟢 Tarefa 2 — Navegar pelos 36 presets

```
[BANK-] / [BANK+]  →  display pisca número do banco
                       (não trocou ainda!)
        ↓
[A] [B] [C] [D]   →  carrega o preset daquele slot
```

**Exemplo prático:** quero o preset **5C**

1. Pise em **BANK+** até o display piscar `5`
2. Pise em **C** → carrega o preset 5C ✅

> Se o display pisca e você não confirma com A/B/C/D, em alguns segundos ele volta ao banco anterior.

---

## 🟢 Tarefa 3 — Editar um preset em tempo real

1. Carregue o preset que quer mudar (ex.: 3B)
2. Pise em **B + C** (tap) → entra em **modo LIVE**
3. Veja as luzes dos knobs:
   - Acesas = módulo ativo
   - Piscando = ativo mas valor real ≠ posição visual
   - Apagadas = módulo desligado
4. Gire qualquer knob → som muda em tempo real
5. Quando estiver feliz com o som → siga para a Tarefa 4 (salvar)

---

## 🟢 Tarefa 4 — Salvar um preset editado

Estando em **modo LIVE** com o som que quer:

| Cenário | Passos |
|---------|--------|
| **Sobrescrever o preset atual** | Segure o footswitch (A/B/C/D) do **slot atual** até piscar rápido ✅ |
| **Salvar em outro slot** | Primeiro pise em BANK-/BANK+ para escolher o banco → depois **segure** o A/B/C/D de destino |

> Confirmação visual: o footswitch **pisca rapidamente** = salvo.
> ⚠️ O preset anterior daquele slot é **substituído**.

---

## 🟢 Tarefa 5 — Criar um preset do zero

1. Modo **LIVE** (B+C)
2. **Desligue todos os módulos**: pise em A, B, C, D até **todos** os LEDs apagarem
3. Agora ligue só os módulos que quer:
   - Pedal **D** = AMP (provavelmente quer ligado)
   - Pedal **C** = MOD (opcional)
   - Pedal **B** = DELAY (opcional)
   - Pedal **A** = REVERB (opcional)
4. Para cada bloco ativo, **gire os knobs** até o som ficar bom
5. Escolha o **AMP TYPE** girando o knob TYPE
6. Escolha o **IR CAB** girando o knob IR CAB (evite slot 1, que é OFF)
7. **Salve** (Tarefa 4)

> Comece simples: AMP + IR CAB + um pouco de REVERB. Adicione MOD/DELAY só depois.

---

## 🟢 Tarefa 6 — Afinar a guitarra

1. Segure **B + C por 2 segundos** → entra no TUNER
2. A luz do MASTER **apaga** e a saída fica silenciada
3. Toque uma corda solta
4. Olhe o display (nome da nota) e as luzes (régua de afinação):
   - 🟢 verde central = afinado
   - 🔴 esquerda = grave demais
   - 🔴 direita = aguda demais
5. Pise em **B + C** (tap) para sair do TUNER

---

## 🟢 Tarefa 7 — Conectar ao celular (app M-EFCS)

1. **Instale** o M-EFCS pela Play Store / App Store
2. No celular: ative **Bluetooth** + (Android) **Localização**
3. No TANK-G: segure **B+C por 3s** → LED BT pisca
4. Abra o app → **+** ou **"Connect"** → selecione TANK-G
5. LED BT no pedal fica **fixo** = conectado ✅
6. Já pode editar presets na tela

---

## 🟢 Tarefa 8 — Usar o TANK-G como interface USB no PC

1. Conecte o **USB-C** no PC (use cabo de **dados**, não só de carga)
2. Windows / Mac reconhece como dispositivo de áudio (geralmente "M-Vave" ou "TANK-G")
3. Na DAW (Reaper, Ableton, etc.):
   - **Audio Device** → selecione TANK-G
   - **Input** → canal mono do TANK-G
4. Crie uma faixa de áudio → grave normalmente
5. O sinal gravado já vem **com amp + efeitos + IR** processados

> Para gravar **DI limpo** (guitarra crua) e re-amp depois, o TANK-G não tem essa saída separada nesta categoria de produto. Se precisar de DI, grave em paralelo (split cable antes de entrar no TANK-G).

---

## 🟢 Tarefa 9 — Importar um IR personalizado

1. Encontre um IR `.wav` (Celestion oficiais, ML Sound Lab, OwnHammer, etc.)
2. Conecte o pedal ao **M-EFCS Desktop** via USB
3. Menu **IR Management** (ou similar)
4. Selecione um **slot de destino** (2–9 — slot 1 é OFF e não pode ser usado)
5. **Importe** o arquivo `.wav`
6. ⚠️ Confirme a sobrescrita do IR anterior
7. No pedal, gire o knob **IR CAB** até a posição correspondente para usar

> Mantenha o **volume do IR** balanceado — IRs muito altos saturam a saída.

---

## 🟢 Tarefa 10 — Backup completo

**Antes de qualquer experimento maior, faça isso:**

| Via | Passos |
|-----|--------|
| **Desktop** | M-EFCS → File → Export / Backup → salvar em local seguro |
| **Mobile** | M-EFCS → Menu → Export Presets → enviar pra cloud / e-mail |

> Faça isso pelo menos **uma vez** quando o pedal vem da fábrica — preserva os presets originais.

---

## 🟢 Tarefa 11 — Fluxo de show ao vivo (sugestão)

### Antes de subir ao palco
- [ ] Bateria carregada (>80%)
- [ ] Backup recente dos presets
- [ ] Testar XLR no PA
- [ ] Afinar (Tuner)
- [ ] **Modo PRESET** (não LIVE — evita knobs causarem mudança acidental)

### Durante o show
- Foco no **modo PRESET** + footswitches A/B/C/D para trocar de som
- Combo **B+C (2s)** para afinar entre músicas (saída silencia automático)
- Evite mexer em knobs físicos no meio da música — você não escuta efeito (modo PRESET) e atrapalha o setlist

### Cuidados
- Cabo XLR firme no mixer
- Não pisar no cabo USB (se estiver usando alimentação externa)
- Bateria **L piscando** = troca pra alimentação USB JÁ

---

## 🟢 Tarefa 12 — Reset / restaurar configurações de fábrica

Se algo der errado:

| Via | Como |
|-----|------|
| **M-EFCS Desktop** | Menu → Factory Reset / Restore Default |
| **No pedal** (alguns firmwares) | Procure combo específico no manual da sua revisão de firmware |

> ⚠️ Reset apaga **TODOS os 36 presets e IRs importados**. Faça backup antes.

---

> Próximo: [09 — Atalhos / Cheat sheet](09-atalhos.md)
