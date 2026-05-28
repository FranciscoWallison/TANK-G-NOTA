# 07 — App e Software M-EFCS

O software oficial chama **M-EFCS**. Existem 2 versões:

| Versão | Plataforma | Conexão |
|--------|-----------|---------|
| **M-EFCS Desktop** | Windows / macOS | **USB-C** |
| **M-EFCS Mobile** | Android / iOS | **Bluetooth** |

> Site oficial: <https://www.m-vave.com/appdownload>

---

## 📲 Versão Mobile (Android / iOS)

### Download
- **Android**: Play Store → busca **"M-EFCS"** ou **"M-Vave"**
- **iOS**: App Store → busca **"M-EFCS"** ou **"M-Vave"**
- Fallback (não recomendado): QR Code no manual ou APK do site

> ⚠️ **Sempre prefira loja oficial.** O site M-VAVE tem problemas de HTTPS — APK direto do site = risco de man-in-the-middle.

### Permissões necessárias

| Plataforma | Permissões | Por quê |
|------------|-----------|---------|
| **Android** | **Bluetooth** + **Localização** | Android exige localização ativa para BLE descobrir dispositivos |
| **iOS** | **Bluetooth** | iOS pede só Bluetooth |

> Se o pedal "não aparece" no app no Android, a causa #1 é **localização desligada**.

### Primeiro pareamento

1. Liga o TANK-G
2. Segura **B+C por 3s** → BT do pedal ativa (LED **piscando**)
3. Abre o app M-EFCS
4. Toca em **"+"** ou **"Connect / Pair Device"**
5. Seleciona **TANK-G** na lista
6. LED do BT no pedal fica **fixo** ✅

### O que dá pra fazer no app

| Funcionalidade | Detalhe |
|----------------|---------|
| **Editar presets** | Mexer em todos os parâmetros visualmente |
| **Trocar presets** | Selecionar BANK + slot direto na tela |
| **Compartilhar preset** | Exportar e enviar para outros usuários |
| **Importar / exportar** | Backup de presets (arquivo) |
| **Personalizar cores** | Definir a cor de cada luz de pedal por preset |
| **Importar IRs** | Carregar `.wav` próprios nos slots 2–9 |
| **Restaurar fábrica** | Reset (alguns firmwares — confirme) |

---

## 💻 Versão Desktop (Windows / Mac)

### Download
<https://www.m-vave.com/appdownload>

### Instalação

| Sistema | Passos |
|---------|--------|
| **Windows** | Baixar `.zip` → extrair → rodar instalador `.exe`. Pode pedir para instalar driver USB (autorizar). |
| **macOS** | Baixar `.dmg` → arrastar app para Applications. macOS pode pedir permissão em **Privacidade e Segurança**. |

### Primeira conexão

1. Liga o TANK-G
2. Plugue o **USB-C** no PC/Mac
3. Abre o **M-EFCS**
4. O software detecta o pedal automaticamente (geralmente "Connected" aparece em algum lugar)

### O que dá pra fazer no desktop (extra em relação ao mobile)

| Funcionalidade | Por que o desktop é melhor pra isso |
|----------------|--------------------------------------|
| **Editar 36 presets em lote** | Vê tudo na tela grande |
| **Importar IRs em massa** | Drag-and-drop de vários `.wav` |
| **Backup completo** | Exporta arquivo único com todos os 36 presets |
| **Atualizar firmware** | Fica mais estável via USB do que BT |
| **Restaurar fábrica** | Reset confiável |

---

## 🔄 Atualização de firmware

Firmware = software interno do pedal. Atualizações trazem novos efeitos, correções e às vezes novos amps/IRs.

### Como atualizar (recomendado: via desktop)

1. Conecte o TANK-G no PC via **USB-C**
2. Abra o **M-EFCS Desktop**
3. Vá em **Firmware Update** (ou similar — nome varia)
4. O software detecta a versão atual e oferece a nova se disponível
5. Confirme e **NÃO desligue** o pedal nem desconecte o USB durante a atualização ⚠️
6. Ao final, o pedal reinicia sozinho

> 🚨 **Nunca interrompa** uma atualização de firmware. Pedal pode "brickar" (parar de ligar). Se acontecer, há modo de recuperação — procure o suporte M-VAVE.

---

## 💾 Backup e restauração

### Antes de qualquer experimento, FAÇA BACKUP:

| Plataforma | Como |
|-----------|------|
| **Mobile** | Menu → Export Presets → salvar arquivo no celular |
| **Desktop** | File → Backup / Export → salvar `.bin` ou `.json` |

### Restaurar
Use o mesmo menu, mas **Import** e selecione o arquivo salvo.

> Recomendo fazer um backup **agora**, antes de começar a editar qualquer coisa. Os presets de fábrica são uma boa base e é chato perdê-los.

---

## 🐛 Problemas comuns

| Sintoma | Causa provável | Solução |
|---------|---------------|---------|
| Pedal **não aparece no app mobile** | Localização desligada (Android) | Ative localização + BT |
| App **conecta e cai** | Sinal BT fraco | Aproxime celular do pedal, remova obstáculos |
| Desktop **não reconhece** o pedal | Cabo USB ruim (cabo só de carga) | Use **cabo USB de dados**, não só de carga |
| Som **distorcido demais** após import | IR com volume alto | Reduza GAIN/MASTER ou re-normalize o `.wav` |
| Firmware "trava" | Atualização interrompida | Contate suporte M-VAVE para modo recovery |

---

> Próximo: [08 — Guia prático](08-guia-pratico.md)
