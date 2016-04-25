$(function () {
    function isPositiveInteger(str) {
        return /^\+?(0|[1-9]\d*)$/.test(str);
    }
    function render(template, replace, options) {
        /*
        In the given template (as a string), the tags '{{<tag-id>}}'
        For each tag id found, it will look in replace. If the tag
        does exist as key, it will replace it by the corresp. value.
        */
        var res = template.slice();
        for (var tagid in replace) {
            // the 'g' flag does not work in webkit?
            res = res.replace(
                new RegExp('{{' + tagid + '}}', 'gm'),
                replace[tagid], 'gm');
        };
        return res;
    }
    function preloadPictures(pictureUrls, callback) {
        var i,
            j,
            loaded = 0;

        if (pictureUrls.length == 0)
            return callback();
        for (i = 0, j = pictureUrls.length; i < j; i++) {
            (function (img, src) {
                img.onload = function () {
                    if (++loaded == pictureUrls.length && callback) {
                        callback();
                    }
                };

                // Use the following callback methods to debug
                // in case of an unexpected behavior.
                img.onerror = function () {};
                img.onabort = function () {};

                img.src = src;
            } (new Image(), pictureUrls[i]));
        };
    }
    function spinLoading(stop) {
        if (stop)
            $('body > #loading-overlay').css('display', 'none');
        else
            $('body > #loading-overlay').css('display', 'table');
    }

    function colorMapping(type, value) {
        if (type == 'resolution') {
            if (value[0] < 1280 && value[1] < 720)
                return '#FF0000'
            else if (value[0] < 1920 && value[1] < 1080)
                return "#FFF200"
            else
                return "#00FF00"
        }
        if (type == 'duration') {
            var min_time = 200.0;  // 3min20
            var max_time = 1200.0;  // 20min
            var max_color = 255.0;
            var r = (value - min_time) * max_color / (max_time - min_time)
            var g = max_color - (value - min_time) * max_color / (max_time - min_time)
            r = Math.max(0, Math.min(max_color, r));
            g = Math.max(0, Math.min(max_color, g));
            r = parseInt(r).toString(16);
            g = parseInt(g).toString(16);
            if (r.length < 2)
                r = '0' + r;
            if (g.length < 2)
                g = '0' + g;
            var res = '#' + r + g + '00';
            return res;
        }
    };
    window.render = render;
    window.preloadPictures = preloadPictures;
    window.spinLoading = spinLoading;
    window.isPositiveInteger = isPositiveInteger;
    window.colorMapping = colorMapping;

    $('#close-spinner').click(function () {
        spinLoading('stop');
    })
});
