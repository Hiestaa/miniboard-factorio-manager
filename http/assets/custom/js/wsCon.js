function WSCon() {
    var self = this;

    self.handlers = {};
    self.socket = null;
    self.connect = function () {
        self.socket = new WebSocket('ws://' + location.hostname + ':' + initData.port + '/websocket')

        self.socket.onopen = function() {
            console.log("Connection opened, notifying handlers.")
            for (var handlerKey in self.handlers) {
                self.handlers[handlerKey].onReady()
            }
        };
        self.socket.onmessage = function (evt) {
            message = JSON.parse(evt.data);
            self.handlers[message.handlerKey].onMessage(message);
        };
        self.socket.onclose = function (evt) {
            console.error("Unexpected close - reopening connection.")
            self.connect();
        }
    }
    self.connect();
    // register a new handler under this key. The handler should define the
    // function `onMessage` that will be called each time a message should
    // go to it. It should also define `onReady` which will be called once
    // the connection with server is established.
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

function ErrorHandler() {
    var self = this;

    self.send = wsCon.register('error', self);

    self.onMessage = function (message) {
        UIkit.notify("<i class='uk-icon-close'></i> " + message.message, {
            status: 'danger'
        });
    }

    self.onReady = function () {};
}

function EchoClient() {
    var self = this;

    self.send = wsCon.register('echo', self);

    self.onMessage = function (message) {
        alert(message)
    }

    self.onReady = function () {
        self.send({content: 'Hello, world!'})
    }
}

function SystemUsage() {
    var self = this;

    self.send = wsCon.register('system-usage', self);

    self.onMessage = function (message) {
        $('#system-usage').html('CPU: ' + message.CPU + '% ; MEM: ' + message.MEM + '%')
        self.scheduleRequest();
    }
    self.reqTimeout = null;
    self.scheduleRequest = function () {
        self.reqTimeout = setTimeout(function () {
            self.send({
                'detailed': false
            });
        }, 5000);
    }

    self.onReady = function () {
        if (self.reqTimeout)
            clearTimeout(self.reqTimeout);
        self.send({
            'detailed': false
        });
    }
}

window.wsCon = new WSCon();

$(function () {
    new ErrorHandler();
    new SystemUsage();
});
