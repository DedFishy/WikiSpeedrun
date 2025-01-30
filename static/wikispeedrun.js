/* Constant Elements */
const gameArea = document.getElementById("game-area");
const loadingText = document.getElementById("loading-text");
const notification = document.getElementById("notification");
const roomIDInput = document.getElementById("room-id");
const roomCodeInput = document.getElementById("room-code");
const roomName = document.getElementById("room-name");
const roomCodeSettings = document.getElementById("room-code-setting");
const roomSettingsPlayerList = document.getElementById("room-settings-player-list");

const chatMessageInput = document.getElementById("chat-message");
const chatMessageDisplay = document.getElementById("chat-message-area");

const startPageSearch = document.getElementById("start-page-input");
const endPageSearch = document.getElementById("end-page-input");

const pageRender = document.getElementById("page-render");

const winnerName = document.getElementById("winner-name");
const victoryStatPagePath = document.getElementById("page-path");

const urlBar = document.getElementById("url-bar");

/* Misc Constants */
const notificationTimeout = 5000;
const connectTimeout = 10000;
const youText = "YOU 👉"
const ownerText = "OWNER 👉"
const url = "https://en.wikipedia.org/wiki/"
const disallowedModifiers = [
    "User",
    "Wikipedia",
    "WP",
    "Project",
    "File",
    "MediaWiki",
    "Template",
    "Help",
    "Draft",
    "TimedText",
    "Module",
    "MOS",
    "Topic",
    "Education Program",
    "Book",
    "Gadget",
    "Gadget definition"
]

/* Element Callbacks */
chatMessageInput.addEventListener("keypress", function(event) {
    if (event.key == "Enter") {
        event.preventDefault();
        sendChatMessage();
    }
});

/* Misc Utils */
function linkPostProcess(targetElement, targetFunction) {
    var links = targetElement.getElementsByTagName("a");
    for (let element of links) {
        splitLink = element.href.replace(url, "").split(":");
        namespace = "(Main)";
        if (splitLink.length > 1) {
            namespace = splitLink[0]
        }
        console.log(element.href);
        console.log(namespace)
        // Inclusion/exclusion parameters
        if (
            element.href.includes(url) &&
            !disallowedModifiers.includes(namespace) &&
            !element.href.includes("#")
        ) {
            console.log("Included")
            element.targetPage = decodeURIComponent(element.href.replace(url, ""));
            element.onclick = targetFunction;
            element.href = "#";
        } else {
            console.log("Excluded")
            element.href = "#";
            element.onclick = (event) => {
                event.preventDefault();
                if (namespace) {
                    sendNotification("That isn't an information page (it's a " + namespace + " link)")
                } else {
                    sendNotification("That link is outside of Wikipedia");
                }
            }
        }
    }
}


/* Misc Runtime Variables */
var hadConnectedToServer = false;
var currentNotificationTimeout = null;
var currentConnectionTimeout = null;
var sceneBeforeLoading = null;

/* Player Definition */
var localPlayer = {
    name: null,
    room: null
}

/* Room Definitions */
var roomData = {
    startPage: null,
    endPage: null,
}

/* Scene Definitions */
const scenes = {
    loading: "loading-dialog",
    room: "room-dialog",
    roomSettings: "room-settings",
    wikiWindow: "wiki-window",
    victory: "victory-dialog",
    connectFailed: "connect-failed"
}

/* Socket Initialization */
const socket = io({
    closeOnBeforeunload: true
});
socket.on('connect', function() {
    setScene("room");
    if (hadConnectedToServer) sendNotification("Reconnected to the server");
    socket.emit("client_connect");
    hadConnectedToServer = true;
});
socket.on('disconnect', function() {
    console.log("Disconnected from server");
    setLoading("Disconnected! Reconnecting to the server...");
    setLoadTimeout();
});

/* UI Functions */
function setLoadTimeout() {
    currentConnectionTimeout = setTimeout(() => {setScene("connectFailed");}, connectTimeout)
}
function setScene(scene) {
    gameArea.className = scenes[scene];
    if (scene != "connectFailed" && currentConnectionTimeout != null) {
        try {
            clearTimeout(currentConnectionTimeout);
        } catch (error) {
            console.log("Couldn't clear timeout: " + error)
        }
        
    }
}
function setLoading(text) {
    sceneBeforeLoading = gameArea.className;
    loadingText.innerText = text;
    setScene("loading");
}
function setNotLoading() {
    gameArea.className = sceneBeforeLoading;
}
function sendNotification(text) {
    notification.innerText = text;
    notification.className = "showing";
    if (currentNotificationTimeout != null) {
        try {
            clearTimeout(currentNotificationTimeout);
        } catch (error) {
            console.log("Couldn't clear timeout: " + error)
        }
        
    }
    currentNotificationTimeout = setTimeout(() => notification.className = "", notificationTimeout);
}
function updateUsername(username) {
    socket.emit("try_change_username", {"username": username});
}
function searchStartPage() {
    searchPage(startPageSearch.value, "start_article");
}
function searchEndPage() {
    searchPage(endPageSearch.value, "end_article");
}
function searchPage(query, element) {
    socket.emit("search_pages", {"query": query, "element": element});
}
function startGame() {
    socket.emit("try_start_game");
    setLoading("Starting game...");
}
function navigateBack() {
    navigateToPageByDirection("back");
}
function navigateForward() {
    navigateToPageByDirection("forward");
}
function loadPage(content) {
    console.log("Rendering new page");
    var doc = pageRender.contentWindow.document;
    doc.write(content.replaceAll("&#183;", "•"));

    
    
    let link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = "/static/wiki-inject.css";
    doc.head.appendChild(link);


    linkPostProcess(doc.body, linkNavigationEvent)

    setScene("wikiWindow");
}

/* Room Creation Events */
function createRoom() {
    setLoading("Creating room...");
    socket.emit("try_create_room", {"room": roomIDInput.value, "code": roomCodeInput.value})
}
function joinRoom() {
    setLoading("Joining room...");
    socket.emit("try_join_room", {"room": roomIDInput.value, "code": roomCodeInput.value});
}

/* Misc Room Callbacks */
function leaveRoom() {
    socket.emit("leave_room");
}
function returnToRoomSettings() {
    setLoading("Waiting for other players...")
    socket.emit("return_to_room_settings");
}

/* Misc Utils */
function createPlayerListElement(player, isPlayer, isOwner) {
    let element = document.createElement("div");
    element.className = "player-list-item";
    let playerName = null;
    if (isPlayer || isOwner) {
        let youIndicator = document.createElement("div");
        youIndicator.className = "player-you-indicator";
        youIndicator.innerText = isPlayer ? youText: ownerText;
        element.appendChild(youIndicator);
    }
    if (isPlayer) {
        playerName = document.createElement("input");
        playerName.placeholder = "Name"
        playerName.value = player;
        playerName.onchange = () => {
            updateUsername(playerName.value);
        }
    } else {
        playerName = document.createElement("div");
        playerName.innerText = player;
    }
    
    playerName.className = "player-list-item-name";
    
    element.appendChild(playerName);
    return element;
}

/* Misc Callbacks */
function addChatMessage(sender, text) {

    let isScrolledToBottom = chatMessageDisplay.scrollTop == (chatMessageDisplay.scrollHeight - chatMessageDisplay.offsetHeight);

    let messageElement = document.createElement("div");
    messageElement.classList.add("message-container");

    let senderEl = document.createElement("div");
    senderEl.classList.add("message-sender");
    senderEl.innerText = sender;

    let textEl = document.createElement("div");
    textEl.classList.add("message-text");
    textEl.innerText = text;

    messageElement.appendChild(senderEl);
    messageElement.appendChild(textEl);

    chatMessageDisplay.appendChild(messageElement);

    if (isScrolledToBottom)
        messageElement.scrollIntoView();
}
function sendChatMessage() {
    let message = chatMessageInput.value;
    if (message.length >= 1) {
        socket.emit("send_chat_message", {"text": message});
        chatMessageInput.value = "";
    }
}

function clearChatMessages() {
    chatMessageDisplay.innerHTML = "";
}
function linkNavigationEvent(event) {
    event.preventDefault();
    navigateToPageById(event.currentTarget.targetPage);
    
}
function navigateToPageById(page_id) {
    console.log(page_id)
    socket.emit("game_mode_event", {"event": "navpage", "page_id": page_id})
    setLoading("Loading page...")
}
function navigateToPageByDirection(direction) {
    socket.emit("game_mode_event", {"event": "navpage", "direction": direction})
    setLoading("Loading page...")
}
function updateRoomSettings(data) {
    roomSettingsPlayerList.innerHTML = "";

    if (localPlayer.name == data["owner"]) {
        startPageSearch.disabled = false;
        endPageSearch.disabled = false;
    } else {
        startPageSearch.disabled = true;
        endPageSearch.disabled = true;
    }

    data["players"].forEach(player => {
        roomSettingsPlayerList.appendChild(createPlayerListElement(player, player==localPlayer.name, player==data["owner"]))
    });
    console.log(data["start_article"]);
    console.log(data["end_article"]);

    start_title = data["start_article"]["title"];
    if (start_title != "") {
        startPageSearch.value = start_title;
        startPageSearch.classList.remove("invalid-input");
        roomData.startPage = start_title;
    } else {
        startPageSearch.classList.add("invalid-input");
    }

    end_title = data["end_article"]["title"];
    if (end_title != "") {
        endPageSearch.value = end_title;
        endPageSearch.classList.remove("invalid-input");
        roomData.endPage = end_title;
    } else {
        endPageSearch.classList.add("invalid-input");
    }

    if (!data["waiting_for_players"]) {
        setScene("roomSettings");
        roomData.waitingForPlayers = false;
    }
    
    
}

function connectToRoom(data) {
    if (data["status"] == "success") {
        localPlayer.name = data["username"]
        localPlayer.room = data["name"]
        roomCodeSettings.value = data["code"];
        roomName.innerText = localPlayer.room;
        setScene("roomSettings");
        startPageSearch.value = "";
        endPageSearch.value = "";
        clearChatMessages();
        updateRoomSettings(data);
        
    } else {
        setScene("room");
        sendNotification(data["error"]);
    }
}

function showRequestError(data) {
    sendNotification(data["error"]);
}

function listenForErrorableEvent(event, successCallback, failureCallback) {
    socket.on(event, function(data) {
        if (data["status"] == "failure") {
            showRequestError(data);
            failureCallback(data);
        } else {
            successCallback(data);
        }
    });
}
function absorbErrorableEvent(event) {
    listenForErrorableEvent(event, absorbEvent, absorbEvent);
}
const absorbEvent = (data) => {}

//TODO: Make global localRoom variable

/* Socket Recieve Events */
socket.on("join_room", function(data) {
    connectToRoom(data);
})

socket.on("create_room", function(data) {
    connectToRoom(data);
})
socket.on("room_update", function(data) {
    updateRoomSettings(data);
})
socket.on("start", function(data) {
    console.log("Recieved start call with data " + data);
    console.log(data);
    setScene(data["scene"]);
    
    loadPageFromData(data["start_title"]);
    setLoading("Loading start page...");
})
socket.on("navpage", function(data) {

    if (data["status"] == "success") {
        loadPageFromData(data["page_id"])
    } else {
        sendNotification("Couldn't load that page");
        navigateBack();
    }
})
function loadPageFromData(page_id) {
    urlBar.innerText = "";
    pageRender.src = "about:blank";
    
    getPageHTML(page_id).then(
        (content) => {
            if (content["success"]) {
                urlBar.innerText = content.title;
                loadPage(content.html);
            } else {
                navigateBack();
            }
        }
    );
}

socket.on("victory_race", function(data) {
    victoryStatPagePath.innerHTML = "";
    winnerName.innerText = data["winner_name"];
    console.log(data["page_path"])
    data["page_path"].push(roomData.endPage);
    data["page_path"].forEach((page, i, arr) => {
        let pathChip = document.createElement("div");
        pathChip.className = "path-chip";
        pathChip.innerText = page;
        victoryStatPagePath.appendChild(pathChip);
    })
    setScene(data["scene"]);
})
socket.on("change_user_scene", function(data) {
    setScene(data["scene"]);
})
socket.on("change_all_scenes", function(data) {
    setScene(data["scene"]);
})

socket.on("force_disconnect", function(data) {
document.body.innerHTML = "You have been banned from using this service. Have a nice day!";
})

listenForErrorableEvent("change_username", function(data) {
        localPlayer.name = data["username"];
        sendNotification("Changed username");
});

listenForErrorableEvent("search_pages", absorbEvent, (data) => {
    sendNotification("Couldn't find that page");
});

listenForErrorableEvent("start_game_response", absorbEvent, (data) => {
    setScene("roomSettings");
});

listenForErrorableEvent("send_chat_message", function(data) {
    addChatMessage(data["sender"], data["message"])
}, showRequestError)

/* Starting methods */
setLoadTimeout();