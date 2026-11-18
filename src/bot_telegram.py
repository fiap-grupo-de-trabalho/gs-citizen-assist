import os

from sistema import carregar_base, iniciar_telegram

if os.environ.get("TELEGRAM_BOT_TOKEN", "").strip() == "":
    print("Defina a variável de ambiente TELEGRAM_BOT_TOKEN para iniciar o bot.")
elif os.environ.get("ANTHROPIC_API_KEY", "").strip() == "":
    print("Defina a variável de ambiente ANTHROPIC_API_KEY: o bot conversa usando a IA.")
else:
    base = carregar_base()
    if len(base) == 0:
        print("O bot não pode funcionar sem uma base de conhecimento válida.")
    else:
        iniciar_telegram(base)
