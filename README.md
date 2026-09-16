<img width="1506" height="704" alt="image" src="https://github.com/user-attachments/assets/c47f94ac-7f9b-49aa-87c2-20b9e67e4e6d" />

# FAEX RPG - Bot Jogável do Telegram

Um jogo de RPG interativo para o Telegram baseado em turnos, com persistência de dados de jogadores em arquivos JSON locais. O bot suporta múltiplos sistemas de dificuldades, coleta de recursos, fabricação de ferramentas/armas e combates contra monstros e chefes.

## 🛠️ Pré-requisitos

Antes de iniciar, certifique-se de ter instalado em sua máquina:
* **Python 3.10** ou superior
* Biblioteca **Requests** (`pip install requests`)
* Um token válido de bot do Telegram (criado via `@BotFather`)

## 🚀 Como Executar o Projeto

1. Abra o seu terminal (PowerShell) na pasta raiz do projeto.
2. Defina a variável de ambiente com o token do seu bot rodando o comando:
   ```powershell
   $env:TELEGRAM_BOT_TOKEN = "SEUTOKEN"
   ```
3. Inicie o bot executando o arquivo principal:
   ```bash
   python faexrpg.py
   ```

---

## 🎮 Funcionalidades do Jogo

### 🛡️ Modos de Dificuldade
Ao criar um personagem, o jogador escolhe entre três modos que ditam a penalidade de morte:
* **🌿 Clássico:** Não perde itens ou progresso ao morrer.
* **⚔️ Difícil:** Perde todos os itens do inventário após a derrota.
* **💀 Hardcore:** Perda permanente. O personagem é totalmente resetado ao estado inicial.

### ⛏️ Sistema de Recursos e Crafting
Os jogadores coletam materiais básicos para criar itens utilitários:
* **Mineração e Coleta:** Permite coletar `madeira` e `pedra` para ganhar XP.
* **Picareta:** Fabricada com 3 madeiras e 2 pedras. Libera o acesso à área da Caverna.
* **Espada:** Fabricada com 3 ferros e 2 madeiras. Adiciona +15 de dano base aos ataques.

### 🌎 Exploração e Combate
O progresso é dividido por áreas desbloqueadas conforme o nível do jogador:
* **Mundo Inicial:** Acessível para enfrentar *Slime Selvagem*.
* **Caverna (Nível 2 + Picareta):** Onde reside o *Morcego da Caverna*, única fonte para dropar `ferro`.
* **Colmeia (Nível 10):** Área avançada para desafiar o chefe *Vespa Rainha (BOSS)*.

---

## 📖 Comandos Disponíveis

Os comandos podem ser digitados diretamente no chat ou acionados via botões Inline no Telegram:

| Comando | Descrição |
| :--- | :--- |
| `/start` | Inicia a interação com o bot, cria contas e exibe menus |
| `/ajuda` | Lista todos os comandos e dinâmicas básicas do RPG |
| `/status` | Exibe o nível atual, barra de vida, experiência e itens carregados |
| `/cortar` / `/minerar` | Coleta materiais básicos e concede +10 de XP |
| `/fabricar` / `/espada` | Constrói ferramentas que liberam áreas ou aumentam o poder de ataque |
| `/explorar` | Sai em busca de monstros comuns na área inicial |
| `/atacar` / `/fugir` | Controla as ações imediatas dentro de um combate ativo |
| `/sair` | Desconecta temporariamente a sessão do jogador |

---

## 💾 Persistência de Dados

Todos os estados dos personagens, registros de login e inventários são armazenados de forma assíncrona e segura no arquivo local `jogadores.json`. O sistema utiliza gravações em arquivos temporários (`.tmp`) antes da substituição definitiva (`os.replace`) para mitigar riscos de corrupção de dados causados por desligamentos repentinos do script.
