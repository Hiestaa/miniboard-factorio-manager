function WSCon() {
    var self = this;

    self.socket = new WebSocket('ws://' + location.hostname + ':' + initData.port + '/websocket')
    self.handlers = {}

    self.socket.onopen = function() {
    };
    self.socket.onmessage = function (evt) {
        message = JSON.parse(evt.data);
        self.handlers[message.handlerKey].onMessage(message);
    };

    // register a new handler under this key. The handler should define the
    // function `onMessage` that will be called each time a message should
    // go to it.
    // the function returns a function that can be called to send a message
    // from this handler.
    self.register = function (handlerKey, handler) {
        self.handlers[handlerKey] = handler;
        return function (message) {
            message.handlerKey = handlerKey;
            self.socket.send(JSON.stringify(message));
        };
    };
}

function EchoClient() {
    var self = this;

    self.send = wsCon.register('echo', self);

    self.onMessage = function (message) {
        alert(message)
    }

    self.send({content: 'Hello, world!'})
}

function SystemUsage() {
    var self = this;

    self.send = wsCon.register('system-usage', self);

    self.onMessage = function (message) {
        $('#system-usage').html('CPU: ' + message.CPU + '% ; MEM: ' + message.MEM + '%')
        self.scheduleRequest();
    }

    self.scheduleRequest = function () {
        setTimeout(function () {
            self.send({
                'detailed': false
            });
        }, 5000);
    }

    setTimeout(self.scheduleRequest(), 200);
}

window.wsCon = new WSCon();

new SystemUsage();
