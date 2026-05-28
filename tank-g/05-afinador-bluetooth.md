# 05 — Afinador (Tuner) e Bluetooth (BT)

Ambos são acionados pelo **mesmo combo** (B+C), só muda o **tempo segurando**.

| Combo | Tempo | Ação |
|-------|-------|------|
| B + C | **tap** | Alterna PRESET ↔ LIVE |
| B + C | **2 segundos** | Liga/desliga **TUNER** |
| B + C | **3 segundos** | Liga/desliga **Bluetooth** |

---

## 🎼 Afinador (TUNER)

### Como ligar
Segure **B + C** por **2 segundos**.

### O que acontece quando o TUNER está ligado

- **Saída de áudio é silenciada** (mute) — você não escuta a guitarra
- A luz do knob **MASTER apaga** (sinal visual de que está em modo TUNER)
- O **display mostra o nome da nota** detectada
- Para sustenidos: aparece um **pontinho no canto inferior direito** do display
  - Ex.: `C` com pontinho = **C#** (Dó sustenido)
  - Não existem nomes em bemol; o sistema usa **só sustenidos**

### Como ler o tom (afinação)

As luzes dos knobs acima do display funcionam como uma **régua visual**:

| Indicação | Significado |
|-----------|-------------|
| 🟢 Luz **verde central** acesa | Afinado ✅ |
| 🔴 Luzes **vermelhas à esquerda** | Corda está **abaixo** do tom (afrouxar não, **apertar**) |
| 🔴 Luzes **vermelhas à direita** | Corda está **acima** do tom (afrouxar) |

### Como sair
Pise novamente em **B + C** (tap rápido).

> Dica: use o tuner ANTES de cada show. O TANK-G silencia a saída automaticamente, então não tem perigo de afinar com som indo pro PA.

---

## 📶 Bluetooth (BT)

O TANK-G usa Bluetooth para:

- **Tocar áudio** de música do celular via o próprio pedal (jam playback)
- **Editar presets** no celular através do app M-EFCS

### Como ligar/desligar
Segure **B + C** por **3 segundos**.

### Indicador BT (LED dedicado no painel)

| Estado | Significado |
|--------|-------------|
| 🌑 **Apagado** | Bluetooth **desligado** |
| ✨ **Piscando** | BT ligado, **aguardando conexão** |
| 🟢 **Aceso fixo** | BT **conectado** |

### Pareando com o celular

1. Abra o **Bluetooth** do celular
2. **No TANK-G**, segure B+C por 3s para ativar o BT
3. Confirme que o LED **está piscando** (modo descoberta)
4. No celular, procure o dispositivo (geralmente aparece como `TANK-G` ou `M-VAVE`)
5. Conecte. O LED do TANK-G deve ficar **fixo** ✅

### Pareando dentro do app M-EFCS

1. Instale o **M-EFCS** (Play Store / App Store)
2. Ative o **Bluetooth E a Localização** do celular (Android exige localização ligada para BLE)
3. Abra o app → **+** ou **"Connect Device"**
4. Selecione o TANK-G na lista
5. Aguarde o pareamento

> Detalhes do app no documento [07-app-software.md](07-app-software.md).

### Limitações e dicas

- O BT do TANK-G **não é Bluetooth de áudio padrão tipo fone** — ele é principalmente para o app de controle e playback dedicado.
- Se quiser **tocar junto** com música do celular, alguns firmwares permitem stream de áudio via BT direto pela saída do pedal (confirme na sua versão).
- Mantenha o celular **perto** (até ~10m, sem paredes grossas).

---

> Próximo: [06 — Conexões](06-conexoes.md)
