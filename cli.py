"""
cli.py — interactive command-line chat against the unified Agent.

Usage:
    python cli.py
"""

from controller import Agent


def main() -> None:
    print("Business Automation Agent — digita 'exit' per uscire.\n")
    agent = Agent(session_id="cli")

    while True:
        try:
            user_input = input("Tu> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nArrivederci.")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "esci"):
            print("Arrivederci.")
            break

        try:
            reply = agent.handle(user_input)
            print(f"Agente> {reply}\n")
        except Exception as e:
            print(f"[cli] Errore: {e}\n")


if __name__ == "__main__":
    main()
