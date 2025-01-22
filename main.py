from flask import Flask, render_template, request, send_file
from flask_socketio import SocketIO
import dotenv
from os import getenv
from gamemanager import GameManager, GameManagerError, MalformedRequestException, PageNotFoundException
from responsegen import ResponseGenerator
from eventtype import EventType as E
from waitress import serve
from wiki import WikipediaAPI

dotenv.load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = getenv("SECRET_KEY", "secret")
app.config["TEMPLATES_AUTO_RELOAD"] = getenv("TEMPLATE_AUTO_RELOAD", False)
socketio = SocketIO(app)

game_manager = GameManager()
response_generator = ResponseGenerator(game_manager, socketio)
wikipedia = WikipediaAPI()

def e(e: E):
    return e.value

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    return send_file("static/favicon.ico")

@socketio.on(e(E.CLIENT_CONNECT))
def client_connect():
    game_manager.create_player(request.sid)
    print(request.sid + " connected")

@socketio.on(e(E.CLIENT_DISCONNECT))
def client_disconnect():
    room = game_manager.remove_player(request.sid)
    if room is not None:
        response_generator.emit_room_update(room)
    print(request.sid + " disconnected")

@socketio.on(e(E.TRY_JOIN_ROOM))
def try_join_room(data):
    try:
        game_manager.join_room(
            game_manager.get_player(request.sid),
            game_manager.get_room(data["room"]),
            data["code"]
        )
        response_generator.emit(E.JOIN_ROOM_RESPONSE, response_generator.room_info, room=data["room"], player=request.sid)
        response_generator.emit_room_update(data["room"])
    except GameManagerError as e:
        response_generator.emit_error_response(E.JOIN_ROOM_RESPONSE, e)

@socketio.on(e(E.TRY_CREATE_ROOM))
def try_create_room(data):
    try:
        room = game_manager.create_room(
            data["room"],
            wikipedia,
            data["code"]
        )
        game_manager.join_room(
            game_manager.get_player(request.sid),
            room,
            data["code"],
            ignore_incorrect=True
        )
        response_generator.emit(
            E.JOIN_ROOM_RESPONSE, 
            response_generator.room_info, 
            room=data["room"],
            player=request.sid
        )
    except GameManagerError as e:
        response_generator.emit_error_response(E.JOIN_ROOM_RESPONSE, e)

@socketio.on(e(E.TRY_LEAVE_ROOM))
def leave_room():
    try:
        player = game_manager.get_player(request.sid)
        room = player.room.name
        player.room.remove_player(player)
        response_generator.emit(E.LEAVE_ROOM_RESPONSE, response_generator.success)
        response_generator.emit_room_update(room)
    except GameManagerError as e:
        response_generator.emit_error_response(E.LEAVE_ROOM_RESPONSE, e)

@socketio.on(e(E.RETURN_TO_ROOM_SETTINGS))
def return_to_room_settings():
    try:
        player = game_manager.get_player(request.sid)
        room = player.room.name
        player.ready = True
        player.room.waiting_for_reset = True
        response_generator.emit_room_update(room)

    except GameManagerError as e:
        response_generator.emit_error_response(E.LEAVE_ROOM_RESPONSE, e)

@socketio.on(e(E.TRY_CHANGE_USERNAME))
def change_username(data):
    try:
        player = game_manager.get_player(request.sid)
        game_manager.change_username(player.room, player, data["username"])
        response_generator.emit(E.CHANGE_USERNAME_RESPONSE, response_generator.success, request.sid, username=player.name)
        response_generator.emit_room_update(player.room.name)
        print("Emitted name change room update")
    except GameManagerError as e:
        print("Bad username")
        response_generator.emit_error_response(E.CHANGE_USERNAME_RESPONSE, e)

@socketio.on(e(E.SEARCH_PAGES))
def search_pages(data):
    try:
        
        if not data["element"] in ("start_article", "end_article"):
            raise MalformedRequestException("Searching pages")
        
        player = game_manager.get_player(request.sid)
        game_manager.validate_owns_room(player)

        page = wikipedia.search_user_page_or_none(data["query"])

        if page == None:
            response_generator.emit_error_response(E.SEARCH_PAGES, PageNotFoundException("Searching for page"))
        
        player.room.settings.set_member(data["element"], page)
        response_generator.emit_room_update(player.room.name)
        
    except GameManagerError as e:
        response_generator.emit_error_response(E.SEARCH_PAGES, e)

@socketio.on(e(E.TRY_START_GAME))
def start_game():
    try:
        
        player = game_manager.get_player(request.sid)
        game_manager.validate_owns_room(player)
        player.room.settings.mode.start().handle(response_generator, player.room, wikipedia, player)
    except GameManagerError as e:
        response_generator.emit_error_response(E.START_GAME_RESPONSE, e)

@socketio.on(e(E.SEND_CHAT_MESSAGE))
def send_chat_message(data):
    try:
        player = game_manager.get_player(request.sid)
        response_generator.emit(E.SEND_CHAT_MESSAGE, response_generator.chat_message, player.room.name, sender=player.name, message=data["text"])
    except GameManagerError as e:
        response_generator.emit_error_response(E.SEND_CHAT_MESSAGE, e)

@socketio.on(e(E.GAME_MODE_EVENT))
def game_mode_event(data):
    try:
        player = game_manager.get_player(request.sid)
        print(data)
        player.room.settings.mode.user_event(data["event"], data).handle(response_generator, player.room, wikipedia, player, data)
    except GameManagerError as e:
        response_generator.emit_error_response(E.GAME_MODE_EVENT, e)

if __name__ == "__main__":
    socketio.run(app, debug=getenv("DEBUG", False), host="0.0.0.0")