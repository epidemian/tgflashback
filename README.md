# Bot de Flashback

Bot de Telegram que detecta los mensajes de puntaje del juego semanal
[Flashback](https://www.nytimes.com/) de NYT en un grupo, los guarda en
SQLite, y expone comandos para ver la tabla de posiciones y las semanas
pendientes de cada jugador.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Para leer puntajes de capturas de pantalla también hace falta el binario de
Tesseract instalado en el sistema (no alcanza con el paquete de Python):

```bash
sudo apt install tesseract-ocr
```

`.env`:

```
TELEGRAM_TOKEN=...          # token de @BotFather
ADMIN_TELEGRAM_ID=...       # tu user id numérico (hablale a @userinfobot)
TARGET_CHAT_ID=...          # opcional: chat donde avisar los sábados 9am (ver /chatid)
DB_PATH=flashback.db        # opcional
```

Si el grupo tiene "Group Privacy" activado en BotFather, desactivalo con
`/setprivacy` → Disable para que el bot pueda leer los mensajes de puntaje
(no solo los comandos que se le dirigen directamente).

## Cargar datos

```bash
python seed_players.py     # crea los 5 jugadores (Se, Mb, Na, Ra, ²H)
python migrate_xlsx.py     # importa el historial de Chanchullo Flashback.xlsx
```

## Correr el bot

```bash
python -m bot.main
```

## Comandos

- Pegar el mensaje que comparte el juego de Flashback → el bot detecta fecha
  y puntaje y lo guarda para quien lo mandó (tiene que estar vinculado, ver
  abajo).
- Mandar una captura de pantalla del resultado ("You scored X of Y points")
  → el bot lee el puntaje por OCR. La captura no incluye la fecha (siempre
  dice "this week's Flashback"), así que el bot ofrece un selector con las
  semanas pendientes del jugador (más la semana actual) para elegir a cuál
  corresponde. Si la imagen no parece una captura de Flashback, el bot no
  responde nada.
- `/soy <código>` — vincula tu usuario de Telegram a tu código de jugador.
- `/vincular <código>` (respondiendo al mensaje de la persona, solo admin) —
  vincula a otra persona manualmente. Pensado para el alta inicial de los 5
  jugadores.
- `/tabla [año]` — gráfico con la evolución semanal de puntajes de cada
  jugador, más la tabla de posiciones (suma, promedio, semanas jugadas,
  victorias) como pie de foto.
- `/pendientes [código]` — semanas que le faltan a ese jugador, con el link
  para jugarlas.
- `/chatid` — id del chat actual, para configurar `TARGET_CHAT_ID`.
- `/ayuda` — resumen de comandos.

## Aviso semanal

Si `TARGET_CHAT_ID` está configurado, todos los sábados a las 9am (hora
Argentina) el bot manda un mensaje con el link a la nueva edición. Ojo: la
URL de NYT usa la fecha del día anterior (viernes) a la del puzzle.
