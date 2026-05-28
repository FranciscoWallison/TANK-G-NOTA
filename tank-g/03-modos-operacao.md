# 03 — Modos de Operação (PRESET vs LIVE)

O TANK-G tem **dois modos** de operação. Entender isso é a coisa mais importante do pedal — todo o workflow gira em torno disso.

> **Padrão ao ligar:** o pedal entra em **modo PRESET**.
> **Para alternar:** pise nos pedais **B + C juntos** (tap rápido).

---

## 🎯 Modo PRESET (padrão)

Modo de **execução**. Você toca presets prontos sem mexer em parâmetros.

### Estrutura: 9 BANKs × 4 presets = **36 presets**

```
BANK 1 → [A] [B] [C] [D]
BANK 2 → [A] [B] [C] [D]
BANK 3 → [A] [B] [C] [D]
...
BANK 9 → [A] [B] [C] [D]
```

### Como navegar

1. **Trocar de banco:** pise em **BANK-** ou **BANK+**
   → O display pisca o número do banco escolhido (ainda não trocou)
2. **Confirmar e selecionar preset:** pise em **A / B / C / D**
   → O preset é carregado e o LED do footswitch correspondente fica **aceso**

### O que indica o que está rolando

| Indicador | Significado |
|-----------|-------------|
| LED do footswitch aceso | Preset selecionado |
| Luzes dos knobs (algumas acesas) | Efeitos ativos naquele preset |
| Luz do knob acesa | Efeito **ligado** |
| Luz do knob apagada | Efeito **desligado** |
| **Nenhum** footswitch aceso + nenhum knob aceso (só MASTER) | **BYPASS total** |

### ⚠️ Limitação importante do modo PRESET

> No modo PRESET **você NÃO consegue ajustar parâmetros em tempo real com os botões físicos.**
>
> Para mudar tom durante a execução, entre no modo LIVE — ou use o app/software para editar.

---

## 🎛️ Modo LIVE (edição em tempo real)

Modo de **edição** e **improviso** sobre os parâmetros. Use quando quiser:

- Ajustar tom enquanto toca
- Criar uma cadeia de efeitos do zero
- Salvar uma nova configuração em algum slot

### Como entrar
Pise em **B + C juntos** (tap rápido) a partir do modo PRESET.

### Como funcionam os footswitches no modo LIVE

| Pedal | Liga/desliga o módulo |
|-------|----------------------|
| **A** | REVERB |
| **B** | DELAY |
| **C** | MOD |
| **D** | AMP |

### Comportamento dos knobs (3 estados das luzes)

| Estado da luz | O que significa |
|---------------|-----------------|
| 🌑 **Apagada** | Efeito daquele knob **desligado** |
| 🟢 **Acesa fixa** | Efeito ligado **e** o som = posição visual do knob (WYSIWYG) |
| ✨ **Piscando** | Efeito ligado, **mas** o som ≠ posição visual (você herdou o valor de um preset). Assim que mexer no knob, o valor real "salta" para a posição visual e a luz fica fixa. |

### Comportamento dos footswitches no modo LIVE (2 estados)

| Estado do LED | Significado |
|---------------|-------------|
| 🌑 **Apagado** | Módulo desse pedal **desligado** |
| ✨ **Piscando** | Módulo desse pedal **ligado** |

### Fluxo para criar uma cadeia de efeitos do zero

1. Entre em **modo LIVE** (B+C)
2. **Desligue todos os módulos** manualmente (pise em A, B, C, D até todos os LEDs apagarem)
3. **Ligue só os módulos que você quer** na cadeia
4. **Ajuste os knobs** desses módulos (luz pisca → fica fixa quando você "captura" o valor real)
5. **Salve** (veja abaixo)

---

## 💾 Salvar um preset

Estando em **modo LIVE** com o som que você quer:

1. (opcional) Pise em **BANK- / BANK+** para escolher o banco de destino
2. **Segure** o footswitch **A / B / C / D** do slot onde quer salvar
3. O footswitch **pisca rapidamente** = **salvo com sucesso** ✅

> Você está sobrescrevendo o preset daquele slot. Se quiser não perder o original, use o app M-EFCS para fazer backup antes.

---

## 🔁 Resumo visual do fluxo

```
[Ligou o pedal]
       ↓
  [Modo PRESET]  ←─── tap B+C ───→  [Modo LIVE]
       ↓                                 ↓
 Navega/escolhe                  Edita/improvisa
  BANK + A/B/C/D                    knobs ao vivo
                                         ↓
                                  Segura A/B/C/D
                                  → salva no slot
```

---

> Próximo: [04 — Efeitos (módulos)](04-efeitos.md)
