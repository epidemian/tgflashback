from bot import db


def main() -> None:
    db.init_db()
    db.seed_players()
    print("Jugadores creados/verificados.")


if __name__ == "__main__":
    main()
