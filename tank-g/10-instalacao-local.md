# 10 — Instalação Local (apps já extraídos)

Os apps oficiais do TANK-G já foram **extraídos** para a pasta [`../apps/`](../apps/). Tudo é **portátil** — não instala nada no Windows, basta rodar o `.exe`.

> Veja também: [apps/README.md](../apps/README.md) — guia rápido dos `.exe`s.

---

## 📦 O que tem instalado

| App | Quando usar | Como rodar |
|-----|-------------|------------|
| **M-EFCS** | Editar presets, importar IRs, configurar tudo | `f:\projetos\rock\apps\M-EFCS\m_efcs.exe` |
| **M-UPGRADE-NTFS_TANK-G** | Atualizar firmware do pedal | `f:\projetos\rock\apps\M-UPGRADE-NTFS_TANK-G\M-UPGRADE-NTFS.exe` |
| ~~M-VAVE 1.1~~ | App antigo (legado) — pode ignorar | `f:\projetos\rock\apps\M-VAVE-1.1-installer\M-VAVE_1.1_install.exe` |

---

## ▶️ Rodar o M-EFCS (uso normal)

### Via Explorer
Vá em `f:\projetos\rock\apps\M-EFCS\` → duplo clique em **`m_efcs.exe`**.

### Via PowerShell
```powershell
& "f:\projetos\rock\apps\M-EFCS\m_efcs.exe"
```

### Primeira execução
1. Windows pode mostrar **SmartScreen** ("O Windows protegeu o computador...")
   → Clique em **"Mais informações"** → **"Executar assim mesmo"**
2. O app abre — interface tipo Flutter (visual moderno)
3. Para conectar o pedal:
   - **Via USB-C** (PC): plugue o cabo e o app deve detectar
   - **Via Bluetooth**: ative BT no pedal (segurar B+C por 3s), depois conectar no app

---

## ▶️ Atualizar firmware do TANK-G

### Pré-requisitos
- Pedal **ligado** e **carregado** (≥50% de bateria — não pode descarregar no meio)
- Cabo **USB-C de dados** (não cabo só de carga)
- Computador Windows com a pasta `M-UPGRADE-NTFS_TANK-G` extraída

### Passo a passo
1. Conecte o **TANK-G** no PC via **USB-C**
2. Abra o updater:
   ```powershell
   & "f:\projetos\rock\apps\M-UPGRADE-NTFS_TANK-G\M-UPGRADE-NTFS.exe"
   ```
3. O app detecta o pedal e mostra a versão atual
4. Se houver firmware novo, ele oferece atualizar
5. **NÃO desligue / desconecte** durante o processo ⚠️
6. Aguarde a mensagem de sucesso — o pedal reinicia sozinho

### Se der errado
- Logs ficam em `f:\projetos\rock\apps\M-UPGRADE-NTFS_TANK-G\LOG\`
- Há um log de exemplo: `ota_upgrade_20260312.log`
- Em caso de **brick** (pedal não liga após update), contate suporte M-VAVE (precisa de modo recovery)

---

## 🎯 Criar atalhos no Desktop (opcional)

Cole no PowerShell:

```powershell
$ws = New-Object -ComObject WScript.Shell
$desktop = [Environment]::GetFolderPath("Desktop")

# Atalho M-EFCS
$s1 = $ws.CreateShortcut("$desktop\M-EFCS (TANK-G).lnk")
$s1.TargetPath = "f:\projetos\rock\apps\M-EFCS\m_efcs.exe"
$s1.WorkingDirectory = "f:\projetos\rock\apps\M-EFCS"
$s1.Save()

# Atalho Firmware Updater
$s2 = $ws.CreateShortcut("$desktop\TANK-G Firmware Updater.lnk")
$s2.TargetPath = "f:\projetos\rock\apps\M-UPGRADE-NTFS_TANK-G\M-UPGRADE-NTFS.exe"
$s2.WorkingDirectory = "f:\projetos\rock\apps\M-UPGRADE-NTFS_TANK-G"
$s2.Save()

Write-Host "Atalhos criados no Desktop"
```

---

## 🧬 Confirmação: M-EFCS suporta TANK-G

A pasta interna do app inclui:

```
apps/M-EFCS/data/flutter_assets/lib/resources/bin/
├── tankG/          ← seu pedal ✅
├── blackbox/       ← predecessor (TANK-G antigo)
├── tankPro/        ← upgrade (KPT PRO)
├── tankB/
├── tankMini/
├── mk20/  mk300/  sp100/  sk17/  ke1/  hush/  ← outros produtos M-VAVE
```

Cada uma dessas pastas tem:
- `*_ampCab.bin` — IRs de gabinete
- `*_preset.bin` — presets de fábrica
- Algumas: `*_drum.bin` / `*_midiDrum.bin` — backing tracks de bateria

---

## 📄 Outros arquivos da raiz

| Arquivo | O que é | Onde ler |
|---------|---------|----------|
| `M-VAVE-WARRANTY.pdf` | Garantia de **1 ano** (a partir da compra) | [Resumo na seção abaixo](#-garantia-resumo) |
| `ANN.pdf` | Manual do produto **ANN** (outro pedal/produto M-VAVE) | Não é do TANK-G — pular |
| `ANNlabV2.0.zip` | Plugin VST3 / AU do produto **ANN** | Não é do TANK-G — pular |

---

## 📝 Garantia (resumo)

- **Cobertura:** 1 ano a partir da data de compra
- **Quem cobre:** comprador **original** de revendedor autorizado
- **Necessário:** nota fiscal / recibo (serial number é opcional mas ajuda)
- **Onde acionar:** primeiro fale com o **revendedor** onde você comprou
- **NÃO cobre:**
  - Desgaste normal, riscos, manchas, descoloração
  - Danos por uso indevido, quedas, líquidos, temperaturas extremas
  - Bateria (é peça consumível)
  - Modificações não autorizadas
  - Compras em revendedor não autorizado

Contato M-VAVE (China): Tel +86 0756-7795520
Site: <https://www.m-vave.com>

---

> 🔙 Voltar ao [índice principal](README.md)
