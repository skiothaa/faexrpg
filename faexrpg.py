import json
import os
import random
import time

import requests


class TelegramBot:
    """RPG de Telegram persistido em um arquivo JSON por jogador."""

    def __init__(self):
        token = os.environ["TELEGRAM_BOT_TOKEN"].strip()

        if not token:
            raise RuntimeError(
                "A variável de ambiente TELEGRAM_BOT_TOKEN não foi definida."
            )

        self.url_base = f"https://api.telegram.org/bot{token}"
        self.arquivo_jogadores = "jogadores.json"
        self.jogadores = self.carregar_jogadores()
        self.http = requests.Session()

    def iniciar(self):
        update_id = None

        while True:
            try:
                atualizacao = self.obter_novas_mensagens(update_id)
            except requests.RequestException as erro:
                print(f"[ERRO DE REDE] {erro}")
                time.sleep(5)
                continue
            except (ValueError, KeyError) as erro:
                print(f"[ERRO DE RESPOSTA DO TELEGRAM] {erro}")
                time.sleep(5)
                continue

            for dado in atualizacao.get("result", []):
                update_id = dado.get("update_id", update_id)

                try:
                    if "callback_query" in dado:
                        callback = dado["callback_query"]
                        mensagem = callback.get("message", {})
                        chat_id = mensagem.get("chat", {}).get("id")
                        callback_id = callback.get("id")
                        texto = str(callback.get("data", "")).strip()

                        if not chat_id:
                            continue

                        resposta, teclado = self.criar_resposta(chat_id, texto)
                        self.responder(resposta, chat_id, teclado)

                        if callback_id:
                            self.responder_callback(callback_id)

                        continue

                    mensagem = dado.get("message", {})
                    chat_id = mensagem.get("chat", {}).get("id")
                    texto = mensagem.get("text", "").strip()

                    if chat_id and texto:
                        resposta, teclado = self.criar_resposta(chat_id, texto)
                        self.responder(resposta, chat_id, teclado)

                except Exception as erro:
                    # Um update com problema não deve derrubar o bot inteiro.
                    print(f"[ERRO AO PROCESSAR UPDATE] {erro}")

    def carregar_jogadores(self):
        try:
            with open(self.arquivo_jogadores, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
                return dados if isinstance(dados, dict) else {}
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}

    def salvar_jogadores(self):
        arquivo_temporario = f"{self.arquivo_jogadores}.tmp"

        with open(arquivo_temporario, "w", encoding="utf-8") as arquivo:
            json.dump(
                self.jogadores,
                arquivo,
                ensure_ascii=False,
                indent=2,
            )

        os.replace(arquivo_temporario, self.arquivo_jogadores)

    def obter_novas_mensagens(self, update_id):
        parametros = {"timeout": 100}

        if update_id is not None:
            parametros["offset"] = update_id + 1

        resultado = self.http.get(
            f"{self.url_base}/getUpdates",
            params=parametros,
            timeout=110,
        )
        resultado.raise_for_status()
        dados = resultado.json()

        if not dados.get("ok", False):
            raise RuntimeError(f"Telegram API retornou erro: {dados}")

        return dados

    def criar_resposta(self, chat_id, texto):
        jogador = self.jogadores.get(str(chat_id))
        texto_original = str(texto).strip()
        comando = texto_original.lower()

        # /start
        if comando in ("/start", "olá", "ola", "oi"):
            if not jogador:
                return (
                    "Olá! Bem-vindo ao FAEX RPG. Escolha uma opção:",
                    self.menu_conta(),
                )

            if not jogador.get("logado", False):
                return (
                    "Você já possui uma conta. Faça login para continuar.",
                    self.menu_login(),
                )

            if not jogador.get("personagem", False):
                return (
                    "Login realizado! Primeiro, crie seu personagem e escolha a dificuldade.",
                    self.menu_sem_personagem(),
                )

            return self.status(jogador), self.menu_jogo()

        # Registrar: aceita comando e callback_data puro.
        if comando in ("/registrar", "registrar") or texto_original == "📝 Registrar":
            if jogador:
                if jogador.get("logado", False):
                    return "Você já possui uma conta.", self.menu_jogo(jogador)

                return (
                    "Você já possui uma conta. Toque em Login para entrar.",
                    self.menu_login(),
                )

            self.jogadores[str(chat_id)] = self.novo_jogador()
            self.salvar_jogadores()

            return (
                "Conta registrada! Agora faça login para entrar no mundo.",
                self.menu_login(),
            )

        # Login
        if comando in ("/login", "login") or texto_original in ("🔑 Login", "🔑 Fazer login"):
            if not jogador:
                return (
                    "Você ainda não tem conta. Toque em Registrar primeiro.",
                    self.menu_conta(),
                )

            jogador["logado"] = True
            self.salvar_jogadores()

            if not jogador.get("personagem", False):
                return (
                    "Login realizado! Primeiro, crie seu personagem e escolha a dificuldade.",
                    self.menu_sem_personagem(),
                )

            return "Login realizado! Escolha uma ação para continuar.", self.menu_jogo(jogador)

        # Comandos públicos que não exigem login.
        if comando in ("/ajuda", "ajuda") or texto_original == "📖 Ajuda":
            return self.ajuda(), self.menu_jogo(jogador) if jogador and jogador.get("logado") else self.menu_conta()

        if not jogador:
            return (
                "Digite /start e escolha Registrar para começar.",
                self.menu_conta(),
            )

        if not jogador.get("logado", False):
            return (
                "Faça login antes de jogar.",
                self.menu_login(),
            )

        # Criar personagem precisa acontecer antes das ações do jogo.
        if comando in ("/personagem", "personagem", "criar personagem") or texto_original == "🧙 Personagem":
            if jogador.get("personagem", False):
                return (
                    f"Seu personagem já está criado no modo {jogador['dificuldade']}.",
                    self.menu_jogo(jogador),
                )

            return (
                "Escolha a dificuldade do seu personagem:",
                self.menu_dificuldade(),
            )

        if comando in ("classico", "clássico", "dificil", "difícil", "hardcore"):
            return self.criar_personagem(jogador, comando)

        # Nenhuma ação de gameplay é liberada sem personagem.
        if not jogador.get("personagem", False):
            return (
                "Você precisa criar um personagem antes de jogar.",
                self.menu_sem_personagem(),
            )

        if comando in ("/status", "/inventario", "inventário", "inventario") or texto_original == "🎒 Inventário":
            return self.status(jogador), self.menu_jogo(jogador)

        if comando in ("/minerar", "minerar") or texto_original == "⛏️ Minerar":
            return self.coletar(jogador, "pedra", 1, 10), self.menu_jogo(jogador)

        if comando in ("/cortar", "cortar") or texto_original == "🪓 Cortar":
            return self.coletar(jogador, "madeira", 1, 10), self.menu_jogo(jogador)

        if comando in ("/lugares", "lugares") or texto_original == "🌎 Lugares":
            return self.lugares(jogador), self.menu_jogo(jogador)

        if comando in ("/caverna", "caverna"):
            if jogador["nivel"] < 2 or jogador["inventario"].get("picareta", 0) < 1:
                return (
                    "A Caverna exige nível 2 e uma picareta. Colete recursos e use /fabricar.",
                    self.menu_jogo(jogador),
                )

            combate = self.iniciar_combate(
                jogador,
                "Morcego da Caverna",
                30,
                8,
                15,
                recompensa={"ferro": (1, 2)},
            )
            return combate, self.menu_combate()

        if comando in ("/sair", "/explorar", "explorar") or texto_original == "🚪 Sair de casa":
            combate = self.iniciar_combate(
                jogador,
                "Slime Selvagem",
                25,
                6,
                12,
            )
            return combate, self.menu_combate()

        if comando in ("/colmeia", "colmeia") or texto_original == "🐝 Colmeia":
            if jogador["nivel"] < 10:
                return (
                    "A Colmeia exige nível 10. Continue explorando e derrotando inimigos.",
                    self.menu_jogo(jogador),
                )

            combate = self.iniciar_combate(
                jogador,
                "Vespa Rainha (BOSS)",
                100,
                15,
                80,
                boss=True,
            )
            return combate, self.menu_combate()

        if comando in ("/atacar", "atacar") or texto_original == "⚔️ Atacar":
            resposta = self.atacar(jogador)
            teclado = self.menu_combate() if jogador.get("combate") else self.menu_jogo(jogador)
            return resposta, teclado

        if comando in ("/fugir", "fugir") or texto_original == "🏃 Fugir":
            jogador["combate"] = None
            self.salvar_jogadores()

            return (
                "Você fugiu do combate e voltou para uma área segura.",
                self.menu_jogo(jogador),
            )

        if comando in ("/fabricar", "fabricar") or texto_original == "🔨 Fabricar":
            return self.fabricar(jogador), self.menu_jogo(jogador)

        if comando in ("/espada", "fabricar espada") or texto_original == "🗡️ Espada":
            return self.fabricar_espada(jogador), self.menu_jogo(jogador)

        return (
            "Não entendi. Use /ajuda para ver os comandos.",
            self.menu_jogo(jogador),
        )

    @staticmethod
    def novo_jogador():
        return {
            "logado": False,
            "personagem": False,
            "dificuldade": None,
            "nivel": 1,
            "xp": 0,
            "vida": 100,
            "combate": None,
            "inventario": {
                "madeira": 0,
                "pedra": 0,
                "ferro": 0,
                "picareta": 0,
                "espada": 0,
            },
        }

    @staticmethod
    def menu_conta():
        return [[
            {"text": "🔑 Login", "callback_data": "login"},
            {"text": "📝 Registrar", "callback_data": "registrar"},
        ]]

    @staticmethod
    def menu_login():
        return [[
            {"text": "🔑 Login", "callback_data": "login"},
        ]]

    @staticmethod
    def menu_sem_personagem():
        return [
            [{"text": "🧙 Personagem", "callback_data": "personagem"}],
            [{"text": "📖 Ajuda", "callback_data": "ajuda"}],
        ]

    @staticmethod
    def menu_jogo(jogador=None):
        return [
            [{"text": "⛏️ Minerar", "callback_data": "minerar"}, {"text": "🪓 Cortar", "callback_data": "cortar"}],
            [{"text": "🌎 Lugares", "callback_data": "lugares"}, {"text": "🔨 Fabricar", "callback_data": "fabricar"}],
            [{"text": "🎒 Inventário", "callback_data": "inventario"}, {"text": "📖 Ajuda", "callback_data": "ajuda"}],
            [{"text": "🚪 Sair de casa", "callback_data": "explorar"}, {"text": "🐝 Colmeia", "callback_data": "colmeia"}],
            [{"text": "🧙 Personagem", "callback_data": "personagem"}],
        ]

    @staticmethod
    def menu_dificuldade():
        return [[
            {"text": "🌿 Clássico", "callback_data": "classico"},
            {"text": "⚔️ Difícil", "callback_data": "dificil"},
            {"text": "💀 Hardcore", "callback_data": "hardcore"},
        ]]

    @staticmethod
    def menu_combate():
        return [[
            {"text": "⚔️ Atacar", "callback_data": "atacar"},
            {"text": "🏃 Fugir", "callback_data": "fugir"},
        ]]

    @staticmethod
    def status(jogador):
        inventario = jogador.get("inventario", {})
        itens = ", ".join(
            f"{item}: {quantidade}" for item, quantidade in inventario.items()
        )
        modo = jogador.get("dificuldade") or "não escolhido"

        return (
            f"Nível {jogador.get('nivel', 1)} | "
            f"Vida: {jogador.get('vida', 100)}/100 | "
            f"XP: {jogador.get('xp', 0)}/100\n"
            f"Modo: {modo}\n"
            f"Inventário: {itens}"
        )

    @staticmethod
    def lugares(jogador):
        caverna = (
            "✅ disponível"
            if jogador["nivel"] >= 2 and jogador["inventario"].get("picareta", 0)
            else "🔒 nível 2 + picareta"
        )
        colmeia = (
            "✅ disponível"
            if jogador["nivel"] >= 10
            else "🔒 nível 10"
        )
        return (
            "Lugares:\n"
            "• Mundo inicial: ✅\n"
            f"• Caverna: {caverna}\n"
            f"• Colmeia: {colmeia}\n"
            "Use /caverna ou /colmeia para explorar."
        )
    
    @staticmethod
    def ajuda():
        return (
            "Comandos:\n"
            "/personagem: escolhe o modo de jogo\n"
            "/explorar: sai de casa e encontra inimigos\n"
            "/atacar e /fugir: ações de combate\n"
            "/minerar: pega pedra (+10 XP)\n"
            "/cortar: pega madeira (+10 XP)\n"
            "/fabricar: cria uma picareta (3 madeira + 2 pedra)\n"
            "/espada: cria uma espada (3 ferro + 2 madeira)\n"
            "/caverna: enfrenta um morcego e pode encontrar ferro\n"
            "/colmeia: enfrenta a Vespa Rainha (nível 3)\n"
            "/inventario: mostra recursos"
        )

    def criar_personagem(self, jogador, comando):
        if jogador.get("personagem", False):
            return (
                f"Seu personagem já está criado no modo {jogador['dificuldade']}.",
                self.menu_jogo(jogador),
            )

        mapa_dificuldade = {
            "classico": "Clássico",
            "clássico": "Clássico",
            "dificil": "Difícil",
            "difícil": "Difícil",
            "hardcore": "Hardcore",
        }

        dificuldade = mapa_dificuldade[comando]

        jogador["personagem"] = True
        jogador["dificuldade"] = dificuldade
        jogador["nivel"] = 1
        jogador["xp"] = 0
        jogador["vida"] = 100
        jogador["combate"] = None

        self.salvar_jogadores()

        return (
            f"Personagem criado no modo {dificuldade}! "
            "Você chegou ao Mundo FAEX RPG.",
            self.menu_jogo(jogador),
        )

    def iniciar_combate(
        self,
        jogador,
        inimigo,
        vida,
        dano,
        xp,
        boss=False,
        recompensa=None,
    ):
        if jogador.get("combate"):
            combate = jogador["combate"]
            return (
                f"Você já está enfrentando {combate['nome']}! "
                f"Vida: {combate['vida']}/{combate['vida_max']}\n"
                "Use /atacar ou /fugir."
            )

        jogador["combate"] = {
            "nome": inimigo,
            "vida": vida,
            "vida_max": vida,
            "dano": dano,
            "xp": xp,
            "boss": boss,
            "recompensa": recompensa or {},
        }

        self.salvar_jogadores()

        tipo = "BOSS " if boss else ""
        return (
            f"{tipo}{inimigo} apareceu! Vida: {vida}\n"
            "Prepare-se para lutar. Use /atacar ou /fugir."
        )

    def atacar(self, jogador):
        combate = jogador.get("combate")

        if not combate:
            return "Não há inimigos por perto. Use /explorar, /caverna ou /colmeia."

        dano = 20 + jogador["inventario"].get("espada", 0) * 15
        combate["vida"] -= dano

        mensagem = f"Você causou {dano} de dano em {combate['nome']}!"

        if combate["vida"] <= 0:
            mensagem += (
                f"\nVocê derrotou {combate['nome']} "
                f"e ganhou {combate['xp']} XP!"
            )

            # Recompensas do inimigo.
            recompensas = combate.get("recompensa", {})
            for item, faixa in recompensas.items():
                minimo, maximo = faixa
                quantidade = random.randint(minimo, maximo)
                jogador["inventario"][item] = (
                    jogador["inventario"].get(item, 0) + quantidade
                )
                mensagem += f"\nVocê encontrou {quantidade} {item}!"

            jogador["combate"] = None
            jogador["xp"] += combate["xp"]

            niveis_ganhos = self.subir_nivel(jogador)

            if niveis_ganhos:
                mensagem += (
                    f"\nParabéns! Você alcançou o nível "
                    f"{jogador['nivel']}."
                )

            self.salvar_jogadores()

            return mensagem + f"\n{self.status(jogador)}"

        dano_recebido = random.randint(
            max(1, combate["dano"] - 3),
            combate["dano"] + 3,
        )

        jogador["vida"] = max(0, jogador["vida"] - dano_recebido)

        mensagem += (
            f"\n{combate['nome']} causou {dano_recebido} de dano. "
            f"Sua vida: {jogador['vida']}/100"
        )

        if jogador["vida"] <= 0:
            return self.morrer(jogador, mensagem)

        self.salvar_jogadores()

        return (
            mensagem
            + f"\nVida do inimigo: "
            f"{combate['vida']}/{combate['vida_max']}"
        )

    def morrer(self, jogador, mensagem):
        dificuldade = jogador.get("dificuldade")
        jogador["combate"] = None

        if dificuldade == "Hardcore":
            # A morte perde o personagem inteiro e devolve tudo ao estado inicial.
            jogador.clear()
            jogador.update(self.novo_jogador())
            jogador["logado"] = True

            mensagem += (
                "\nVocê morreu no modo Hardcore. "
                "Seu personagem foi perdido. "
                "Escolha /personagem para criar outro."
            )

        elif dificuldade == "Difícil":
            jogador["inventario"] = self.novo_jogador()["inventario"]
            jogador["vida"] = 100
            mensagem += "\nVocê morreu e perdeu seus itens no modo Difícil."

        else:
            jogador["vida"] = 100
            mensagem += (
                "\nVocê foi derrotado, mas não perdeu seus itens "
                "no modo Clássico."
            )

        self.salvar_jogadores()
        return mensagem

    @staticmethod
    def subir_nivel(jogador):
        niveis_ganhos = 0

        while jogador["xp"] >= 100:
            jogador["xp"] -= 100
            jogador["nivel"] += 1
            jogador["vida"] = 100
            niveis_ganhos += 1

        return niveis_ganhos

    def coletar(self, jogador, item, quantidade, xp, prefixo="Você encontrou"):
        jogador["inventario"][item] = (
            jogador["inventario"].get(item, 0) + quantidade
        )

        mensagem = f"{prefixo} {quantidade} {item}!"
        jogador["xp"] += xp

        niveis_ganhos = self.subir_nivel(jogador)

        if niveis_ganhos:
            mensagem += (
                f"\nParabéns! Você alcançou o nível "
                f"{jogador['nivel']} e recuperou sua vida para 100."
            )

        self.salvar_jogadores()

        return f"{mensagem}\n+{xp} XP\n{self.status(jogador)}"

    def fabricar(self, jogador):
        inventario = jogador["inventario"]

        if inventario.get("picareta", 0):
            return "Você já possui uma picareta. Explore a Caverna com /caverna."

        if inventario.get("madeira", 0) < 3 or inventario.get("pedra", 0) < 2:
            return "Para fabricar uma picareta você precisa de 3 madeira e 2 pedra."

        inventario["madeira"] -= 3
        inventario["pedra"] -= 2
        inventario["picareta"] = 1

        self.salvar_jogadores()

        return "Picareta fabricada! Agora você pode explorar a /caverna."

    def fabricar_espada(self, jogador):
        inventario = jogador["inventario"]

        if inventario.get("espada", 0):
            return "Você já possui uma espada."

        if inventario.get("ferro") < 3 or inventario.get("madeira") < 2:
            return "Para fabricar uma espada você precisa de 3 ferro e 2 madeira."

        inventario["ferro"] -= 3
        inventario["madeira"] -= 2
        inventario["espada"] = 1

        self.salvar_jogadores()

        return "Espada fabricada! Seu ataque agora causa 35 de dano."

    def responder(self, resposta, chat_id, teclado=None):
        parametros = {
            "chat_id": chat_id,
            "text": resposta,
        }

        if teclado:
            parametros["reply_markup"] = json.dumps(
                {"inline_keyboard": teclado},
                ensure_ascii=False,
            )

        try:
            resultado = self.http.get(
                f"{self.url_base}/sendMessage",
                params=parametros,
                timeout=20,
            )
            resultado.raise_for_status()
        except requests.RequestException as erro:
            print(f"[ERRO AO ENVIAR MENSAGEM] {erro}")

    def responder_callback(self, callback_id):
        try:
            resultado = self.http.get(
                f"{self.url_base}/answerCallbackQuery",
                params={"callback_query_id": callback_id},
                timeout=20,
            )
            resultado.raise_for_status()
        except requests.RequestException as erro:
            print(f"[ERRO NO CALLBACK] {erro}")


if __name__ == "__main__":
    TelegramBot().iniciar()
