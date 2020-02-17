//sidebar
function show_sidebar(side, editor) {
    var tbContainer = document.createElement('div');
    tbContainer.style.position = 'absolute';
    tbContainer.style.width = '24px';
    tbContainer.style.padding = '2px';
    tbContainer.style.left = '10px';
    tbContainer.style.top = '10px';
    tbContainer.style.width = '24px';
    tbContainer.style.bottom = '0px';

    side.appendChild(tbContainer);
    // Creates new sidebar without event processing
    var sidebar = new mxToolbar(tbContainer);
    sidebar.enabled = false;

    var addVertex = function (type) {
        let types = editor.graph.stylesheet.styles;
        if (Object.keys(types).includes(type)) {
            let w = 'input, output'.includes(type) ? 140 : 150;
            let h = 'input, output'.includes(type) ? 70 : 170;
            let name = 'input, output'.includes(type) ? block_name({
                'var': 'Test ' + type,
                'description': 'test test'
            }, type) : block_name({"function": "state"}, type);
            var vertex = new mxCell(name, new mxGeometry(0, 0, w, h), type);
            vertex.setVertex(true);
            let icon = ('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(sidebar_icon(type)));
            var img = addSidebarItem(editor, sidebar, vertex, icon, type);
            img.enabled = true;

            editor.graph.getSelectionModel().addListener(mxEvent.CHANGE, function () {
                var tmp = editor.graph.isSelectionEmpty();
                mxUtils.setOpacity(img, (tmp) ? 100 : 20);
                img.enabled = tmp;
            });
        }
    };

    var ft = ['input', 'output', 'body'];
    for (let f in ft) {
        addVertex(ft[f]);
    }
}

function addSidebarItem(editor, sidebar, prototype, image, title) {
    // Function that is executed when the image is dropped on
    // the graph. The cell argument points to the cell under
    // the mousepointer if there is one.
    var funct = function (editor, evt, cell, x, y) {
        let ts = editor.getModel().cells;
        editor.stopEditing(false);
        var vertex = editor.getModel().cloneCell(prototype);
        var res = [];
        for (let c in ts) {
            if (ts[c].id.split(' ')[0] === title) {
                res.push(ts[c]);
            }
        }
        let r;
        if (res) {
            if ('input, output'.includes(title)) {
                r = res.slice(-1)[0];
            }
            else {
                let u = ['value, state', 'LT, GT', 'AND'];
                let group = 0;
                for (let t in u) {
                    if (u[t].includes($(vertex.getAttribute('label')).attr('id'))) {
                        group = t;
                        break
                    }
                }
                for (let rb = res.length; rb--;) {
                    if (u[group].includes($(res[rb].getAttribute('label')).attr('id'))) {
                        r = res[rb];
                        break;
                    }
                }
            }
        }
        x = r ? r.geometry.x : x;
        y = r ? ('input, output'.includes(title) ? r.geometry.y + 400 : r.geometry.y + 200) : y;

        vertex.geometry.x = x;
        vertex.geometry.y = y;
        vertex.block_name = vertex.style;
        vertex.id = title + ' ' + (res.length + 1);
        editor.addCell(vertex);
    };
    // Creates the image which is used as the drag icon (preview)
    var img = sidebar.addMode(title, image, function (evt, cell) {
        var pt = this.graph.getPointForEvent(evt);
        funct(editor.graph, evt, cell, pt.x, pt.y);
    });

    // Disables dragging if element is disabled. This is a workaround
    // for wrong event order in IE. Following is a dummy listener that
    // is invoked as the last listener in IE.
    mxEvent.addListener(img, 'click', function (evt) {
        // do nothing
    });

    // This listener is always called first before any other listener
    // in all browsers.
    mxEvent.addListener(img, 'mousedown', function (evt) {
        if (img.enabled == false) {
            mxEvent.consume(evt);
        }
    });

    mxUtils.makeDraggable(img, editor.graph, funct);
    return img;
}

function sidebar_icon(type) {
    var img;
    if ('input, output'.includes(type)) {
        let stroke = type === 'input' ? '#0094db' : '#A070C4';
        let title = type === 'input' ? 'var in' : 'out';
        img = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 289.53 174.01">\n' +
            '    <defs>\n' +
            '        <style>\n' +
            '            .cls-1{fill:none;stroke:' + stroke +';stroke-linecap:round;stroke-linejoin:round;stroke-width:4px;}.cls-2{font-size:61.57px;fill:#0094db;font-family:MyriadPro-Regular,\n' +
            '            Myriad Pro;}\n' +
            '        </style>\n' +
            '    </defs>\n' +
            '    <title>body</title>\n' +
            '    <g id="Layer_2" data-name="Layer 2">\n' +
            '        <g id="Layer_6" data-name="Layer 6">\n' +
            '            <rect class="cls-1" x="2" y="2" width="285.53" height="170.01"\n' +
            '                  rx="85.01" ry="85.01"/>\n' +
            '            <text class="cls-2" transform="translate(67.24 108.08)">' + title + '</text>\n' +
            '        </g>\n' +
            '    </g>\n' +
            '</svg>';
    }
    else {
        let fun = 'value';
        img = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 204.76 263.49">\n' +
            '    <defs>\n' +
            '        <style>\n' +
            '            .cls-1{fill:none;stroke:#79c3f8;stroke-miterlimit:10;stroke-width:4px;}.cls-2{font-size:61.57px;fill:#79c3f8;font-family:MyriadPro-Regular,\n' +
            '            Myriad Pro;}\n' +
            '        </style>\n' +
            '    </defs>\n' +
            '    <title>input-output</title>\n' +
            '    <g id="Layer_2" data-name="Layer 2">\n' +
            '        <g id="Layer_6" data-name="Layer 6">\n' +
            '            <rect class="cls-1" x="-27.36" y="31.36" width="259.49"\n' +
            '                  height="200.76" rx="29.61" ry="29.61"\n' +
            '                  transform="translate(-29.36 234.12) rotate(-90)"/>\n' +
            '            <text class="cls-2" transform="translate(24.86 151.26)">' + fun + '</text>\n' +
            '        </g>\n' +
            '    </g>\n' +
            '</svg>';
    }
    return img;
}
