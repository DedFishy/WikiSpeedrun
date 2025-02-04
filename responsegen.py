import gamemanager
from flask_socketio import SocketIO
from eventtype import EventType
from flask import request
from typing import Callable

class ResponseGenerator:
    def __init__(self, gamemanager: gamemanager.GameManager, socketio: SocketIO):
        self.gamemanager = gamemanager
        self.socketio = socketio

    def emit(self, event: EventType|gamemanager.GameModeResponse|str, generator: Callable, target: str = None, **args):

        if target == None:
            target = request.sid

        if type(event) in (EventType, gamemanager.GameModeResponse):
            event = event.value
            print("Resolved event: " + event)

        self.socketio.emit(
            event,
            generator(**args),
            to=target
        )


    def emit_room_update(self, room: str, player: str = None):
        self.socketio.emit(
            EventType.ROOM_UPDATE.value,
            self.room_info(room, player),
            to=player if player is not None else room
        )

    def emit_error_response(self, event: EventType, error: gamemanager.GameManagerError):

        self.socketio.emit(
            event.value,
            self.error(error),
            to=request.sid
        )
        

    def _get_player_object(self, player: gamemanager.Player|str) -> gamemanager.Player:
        if type(player) == gamemanager.Player: return player
        elif type(player) == str: return self.gamemanager.get_player(player)
        else: return None
    
    def _get_room_object(self, room: gamemanager.Room|str) -> gamemanager.Room:
        if type(room) == gamemanager.Room: return room
        elif type(room) == str: return self.gamemanager.get_room(room)
        else: return None

    def _create_player_list(self, players: list[gamemanager.Player]):
        return [player.name for player in players]

    def room_info(self, room: gamemanager.Room|str, player: gamemanager.Player|str = None, status: str = "success"):

        room = self._get_room_object(room)
        player = self._get_player_object(player)

        response = {}
        response["status"] = status
        response["name"] = room.name
        response["code"] = room.code
        response["requires_code"] = room.requires_code
        response["players"] = self._create_player_list(room.players)
        response["owner"] = room.owner.name
        response["mode"] = room.settings.mode.name
        response["start_article"] = room.settings.get_member_or("start_article").serialize()
        response["end_article"] = room.settings.get_member_or("end_article").serialize()
        response["waiting_for_players"] = room.evaluate_waiting_for_reset()
        

        if room.state == gamemanager.RoomState.WAITING and not response["waiting_for_players"]:
            room.state = gamemanager.RoomState.IN_ROOM_SETTINGS

        response["state"] = room.state.value
        
        if player:
            response["username"] = player.name
        
        return response
    
    def change_scene(self, room: gamemanager.Room|str, scene: str, status: str = "success", **scene_data):
        room = self._get_room_object(room)

        response = {}
        response["status"] = status
        response["scene"] = scene
        response["status"] = status

        response.update(scene_data)
        
        return response
    
    def waiting_room(self, message, status: str = "success"):

        response = {}
        response["message"] = message
        response["status"] = status

        return response
    
    def nav_page(self, page_id: str, status: str = "success"):
        response = {}
        response["status"] = status
        response["page_id"] = page_id
        response["status"] = status

        return response
    
    def start(self, scene: str, start_title: str = None, status: str = "success"):
        response = {}
        response["scene"] = scene
        response["start_title"] = start_title
        response["status"] = status
        return response
    
    def chat_message(self, sender: str, message: str, status: str = "success"):
        response = {}
        response["sender"] = sender
        response["message"] = message
        response["status"] = status

        return response

    def error(self, error: gamemanager.GameManagerError, status: str = "failure"):
        response = {}
        response["error"] = error.client_error
        response["status"] = status
        return response
    
    def success(self, **args):
        response = {"status": "success"}
        for arg in args.keys():
            response[arg] = args[arg]
        return response
    
    def eval_correct_state(self, room: gamemanager.Room, state: gamemanager.RoomState):
        if room.state != state:
            raise gamemanager.GameManagerError("Evaluating game state")
    