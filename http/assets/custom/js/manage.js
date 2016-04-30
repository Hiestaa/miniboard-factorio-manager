template = '\
<tr>\
    <td>{{name}}</td>\
    <td><b>{{saveObj.name}}</b> ({{saveObj.date}}, {{saveObj.size}})</td>\
    <td>{{ip}}:{{port}}</td>\
    <td class="status">\
        {{#if isRunning}}\
            <div class="uk-badge uk-badge-success">{{status}}</div></td>\
        {{else}}\
            <div class="uk-badge uk-badge-danger">{{status}}</div></td>\
        {{/if}}\
    <td id="controls">\
        {{#if isRunning}}\
            <button class="uk-button uk-button-danger" id="kill">Kill</button>\
        {{else}}\
            {{# if startAvailable }}\
                <button class="uk-button uk-button-success" id="start">Start</button>\
            {{/if}}\
            <button class="uk-button uk-button-primary" id="edit">Edit</button>\
            <button class="uk-button uk-button-danger" id="delete">Delete</button>\
        {{/if}}\
    </td>\
</tr>\
'
editorTemplate = '\
<tr>\
    <td><input type="text" id="name" value="{{name}}"></td>\
    <td><select id="saves">\
        {{#each saves}}\
            <option value="{{this.name}}">{{this.name}} ({{this.date}}, {{this.size}})</option>\
        {{/each}}\
    <select></td>\
    <td>{{ip}}: <select id="ports">\
        {{#each ports}}\
            <option value="{{this}}">{{this}}</option>\
        {{/each}}\
    </td>\
    <td><div class="uk-badge uk-badge-warning uk-badge-notification">?</div></td>\
    <td>\
        <button class="uk-button uk-button-primary" id="submit">Submit</button>\
    </td>\
</tr>\
'
errorTemplate = '<tr><td colspan="5">Error</td></tr>'

function InstanceLogs($container) {
    var self = this;

    self.$container = $container;

    self.clear = function () {
        self.$container.html('');
    }

    self.log = function (message) {
        if (message.indexOf('[ERROR]') == 0)
            message = '<span class="error">' + message + '</span>'
        self.$container.append(message + '<br>');
    }
}

// auto-renders when created unless `options.$el` is specified
function Instance(data, $container, onDelete, onEdit, onStart, onKill, options) {
    var self = this;

    self.serialize = function (data) {
        return {
            name: data.name,
            save: data.save,
            saveObj: data.saveObj,
            ip: initData.ip,
            port: data.port,
            status: data.status,
            isRunning: data.status == 'running',
            startAvailable: data.startAvailable
        };
    }

    self.template = Handlebars.compile(template)
    self.options = options || {}
    // either save the $el in which it should render, or render it automatically
    // to create the $el if not provided.
    self.$el = self.options.$el || $(self.template(self.serialize(data))).appendTo($container);

    self.data = data
    self.onDelete = onDelete
    self.onEdit = onEdit
    self.onStart = onStart
    self.onKill = onKill
    self.editor = false;

    self.events = function () {
        self.$el.find('#delete').click(function () {
            self.onDelete(self.data._id);
        });
        self.$el.find('#edit').click(function () {
            self.onEdit(self.data._id);
        });
        self.$el.find('#start').click(function () {
            self.onStart(self.data._id);
        });
        self.$el.find('#kill').click(function () {
            self.onKill(self.data._id);
        });
    }
    self.events();

    self.render = function (data) {
        if (data)
            self.data = data
        // replace element's content (which is a 'tr') with newly
        // rendered's 'tr' content
        self.$el.html(
            $(self.template(self.serialize(self.data))).html())

        self.events()
    }

    self.delete = function () {
        self.$el.remove();
    }

    self.isRunning = function () {
        return self.data.status == 'running';
    }

    self.setStartAvailable = function () {
        self.data.startAvailable = true;
        self.render()
    }
    self.setStartUnvailable = function () {
        self.data.startAvailable = false
        self.render()
    }

    self.loading = function () {
        self.$el.find('#controls').html('<i title="Loading, please wait..." class="uk-icon uk-icon-close"></i>');
    }
}

// does not autorender when created
// if `options.$el` is given, the instance editor will be rendered within the
// given element. Should be a direct child of the container.
function InstanceEditor($container, saves, onSubmit, options) {
    var self = this;

    self.$container = $container;
    self.saves = saves;
    self.onSubmit = onSubmit;
    self.options = options || {};

    self.$el = self.options.$el || null;
    self.template = Handlebars.compile(editorTemplate);
    self.errorTemplate = Handlebars.compile(errorTemplate);

    self.editedId = null;
    self.editor = true;

    self.serialize = function (data, removePorts) {
        var filteredPorts = function (portsToFilter) {
            var ports = [];
            if (portsToFilter.length == 0)
                return initData.factorioPorts;

            for (var i = 0 ; i < initData.factorioPorts.length; i++) {
                if (portsToFilter.indexOf(initData.factorioPorts[i].toString()) == -1)
                    ports.push(initData.factorioPorts[i]);
            };
            return ports;
        };
        removePorts = removePorts || []

        data = data || {}
        return {
            name: data.name || '',
            saves: self.saves,
            ip: initData.ip,
            ports: filteredPorts(removePorts)
        }
    }

    // if data is given, this is the instance data to be edited
    // removePorts is the list of ports that shouldn't be shown (because used)
    self.renderBottom = function (data, removePorts) {
        data = data || {}
        self.editedId = data._id;


        if (self.$el)
            self.$el.remove();
        self.$el = $(self.template(self.serialize(data, removePorts)))
            .appendTo(self.$container);

        if (data.port)
            self.$el.find('#ports').val(data.port)
        if (data.save)
            self.$el.find('#saves').val(data.save)

        self.$el.find('#submit').click(self.prepareSubmit);
    }

    // if data is given, this is the instance data to be edited
    // removePorts is the list of ports that shouldn't be shown (because used)
    self.renderInPlace = function (data, removePorts) {
        data = data || {}
        self.editedId = data._id;


        self.$el.html(
            $(self.template(self.serialize(data, removePorts))).html());

        if (data.port)
            self.$el.find('#ports').val(data.port)
        if (data.save)
            self.$el.find('#saves').val(data.save)

        self.$el.find('#submit').click(self.prepareSubmit);
    }

    if (self.options.$el)
        self.render = self.renderInPlace
    else
        self.render = self.renderBottom

    self.prepareSubmit = function () {
        if (!self.$el.find('#name').val().trim())
            return self.$el.find('#name').addClass('uk-form-danger');

        data = {
            name: self.$el.find('#name').val(),
            port: self.$el.find('#ports').val(),
            save: self.$el.find('#saves').val(),
        };
        if (self.editedId)
            data._id = self.editedId;
        self.onSubmit(data);
    }

    self.isRunning = function () {
        return false;
    }

    self.loading = function () {
        self.$el.find('#controls').html(
            '<i title="Loading, please wait..." class="uk-icon uk-icon-close"></i>');
    }
}

function Manage () {
    var self = this;

    self.send = wsCon.register('manage', self);

    self.$container = $('#list-content');

    self.instances = {}
    self.creator = null;

    self.savesList = [];
    self.savesIndex = {}

    self.logger = new InstanceLogs($('#logs'));

    self.countRunningInstances = function () {
        var count = 0
        for (var inst in self.instances) {
            if (self.instances[inst].isRunning())
                count += 1;
        }
        return count
    }

    self.onLoad = function (message, freezeEditors) {
        var count = self.countRunningInstances()
        for (var i = message.instances.length - 1; i >= 0; i--) {
            var data = message.instances[i];
            data.saveObj = self.savesIndex[data.save];
            data.startAvailable = count == 0
            if (self.instances[data._id]) {
                if (!self.instances[data._id].editor)
                    self.instances[data._id].render(data);
                else if (!freezeEditors)
                    self.instances[data._id].render(data);
            }
            else
                self.instances[data._id] = new Instance(
                    data, self.$container,
                    self.onDeleteInstance, self.onEditInstance,
                    self.onStartInstance, self.onKillInstance);
        }
        var count = self.countRunningInstances()
        for (var inst in self.instances) {
            if (!self.instances[inst].editor) {
                if (count > 0)
                    self.instances[inst].setStartUnvailable()
                else
                    self.instances[inst].setStartAvailable()
            }
        }
    }

    self.getUsedPorts = function () {
        var usedPorts = [];
        for (var _id in self.instances)
            if (self.instances[_id].data)
                usedPorts.push(self.instances[_id].data.port);
        return usedPorts
    }

    self.indexSaves = function (saves) {
        var index = {};
        for (var i = 0; i < saves.length; i++) {
            index[saves[i].name] = saves[i];
        }
        return index;
    }

    self.onMessage = function (message) {
        switch (message.action) {
            case 'load':
                self.onLoad(message);
                if (self.creator)
                    self.creator.render(null, self.getUsedPorts());
                break;
            case 'listsaves':
                self.savesList = message.saves;
                self.savesIndex = self.indexSaves(self.savesList);
                if (!self.creator)
                    self.creator = new InstanceEditor(
                        self.$container,
                        message.saves,
                        self.onSaveInstance);
                self.fetchList();  // need the saves to fetch the list of instances
                break;
            case 'save':
                self.onLoad(message);
                if (self.creator)
                    self.creator.render(null, self.getUsedPorts());
                break;
            case 'delete':
                self.instances[message._id].delete();
                if (self.creator)
                    self.creator.render(null, self.getUsedPorts());
                delete self.instances[message._id];
                break;
            case 'start':
            case 'kill':
                self.onLoad(message, true);
                break;
            case 'log':
                self.logger.log(message.message);
                break;
        }
    }

    self.onReady = function () {
        self.$container.html('');
        self.instances = {};
        self.fetchSaves();
    }

    self.onEditInstance = function (_id) {
        var data = self.instances[_id].data;
        var $el = self.instances[_id].$el;

        self.instances[_id] = new InstanceEditor(
            self.$container, self.savesList, function (data) {
                var count = self.countRunningInstances
                data.saveObj = self.savesIndex[data.save];
                data.startAvailable = count == 0;
                self.instances[_id] = new Instance(
                    data, self.$container, self.onDeleteInstance,
                    self.onEditInstance,
                    self.onStartInstance, self.onKillInstance, {$el: $el});
                self.onSaveInstance(data);
            }, {$el: $el});
        self.instances[_id].render(data, self.getUsedPorts());
    }

    self.onStartInstance = function (_id) {
        self.instances[_id].loading()
        self.send({
            'action': 'start',
            '_id': _id
        })
        self.logger.clear();
    }

    self.onKillInstance = function (_id) {
        self.instances[_id].loading()
        self.send({
            'action': 'kill',
            '_id': _id
        })
    }

    self.onSaveInstance = function (data) {
        if (data._id)
            self.instances[data._id].loading()
        else
            self.creator.loading();
        self.send({
            'action': 'save',
            'data': data
        });
    }

    self.onDeleteInstance = function (_id) {
        self.instances[_id].loading()
        self.send({
            'action': 'delete',
            '_id': _id
        });
    }

    self.fetchSaves = function () {
        self.send({
            'action': 'listsaves',
        })
    }

    self.fetchList = function () {
        self.send({
            'action': 'load',
            '_id': '*'
        });
    }

    self.fetchInstance = function (id) {
        self.send({
            'action': 'load',
            '_id': id
        });
    }

}

$(function () {
    new Manage();
})