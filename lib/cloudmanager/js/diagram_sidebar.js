var global_vertex = [];
//sidebar
function show_sidebar(side, editor) {
    global_vertex = [];
    var tbContainer = document.createElement('div');
    tbContainer.style.position = 'absolute';
    // tbContainer.style.width = '24px';
    tbContainer.style.padding = '2px';
    tbContainer.style.left = '10px';
    tbContainer.style.top = '10px';
    tbContainer.style.bottom = '0px';

    side.appendChild(tbContainer);
    // Creates new sidebar without event processing
    var sidebar = new mxToolbar(tbContainer);
    sidebar.enabled = false;

    var addVertex = function (type) {
        let types = editor.graph.stylesheet.styles;
        if (Object.keys(types).includes(type)) {
            let w = ['input', 'output'].includes(type) ? 140 : 80;
            let h = ['input', 'output'].includes(type) ? 70 : 80;
            let name = ['input', 'output'].includes(type) ? block_name({
                'var': 'Test ' + type,
                'description': 'test test'
            }, type) : block_name("?");
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
        } else {
            // console.log(type.name + ': ', type.var_in);
            let w = 150;
            let h = 170;
            let name = block_name({
                var: type.name,
                description: type.description
            }, type.name);
            var vertex = new mxCell(name, new mxGeometry(0, 0, w, h), 'body');
            vertex.setId('body');
            vertex.setVertex(true);
            if(Object.keys(type).includes('var_in')) {
                for(let i in type.var_in) {
                    let inp = editor.graph.insertVertex(vertex, null, block_name(type.var_in[i].var), 10, 40*i + 90, 50, 30, 'body_child');
                    inp.name = type.var_in[i].var;
                    if(type.var_in[i].var === 'args') {
                        inp.type = 'args';
                    } else if(['var_in'/*, 'lvar_id', 'sensor_id', 'unit_id', 'item_id'*/].includes(type.var_in[i].var)) {
                        inp.type = 'var_in';
                    } else {
                        inp.type = 'in_block_out';
                    }
                }
            }
            if(Object.keys(type).includes('var_out')) {
                if(type.var_out.length == 0) {
                    let out = editor.graph.insertVertex(vertex, null, block_name('out'), 90, 90, 50, 30, 'body_child');
                    out.name = 'out';
                    out['type'] = 'out';
                } else {
                    for(let i in type.var_out) {
                        let out = editor.graph.insertVertex(vertex, null, block_name(type.var_out[i].var), 90, 40*i + 90, 50, 30, 'body_child');
                        out.name = type.var_out[i].var;
                        out['type'] = 'out';
                    }
                }
            }
            global_vertex[type.name] = vertex;
            let icon = ('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(sidebar_icon(type.name)));
            var img = addSidebarItem(editor, ft_groups[type.group], vertex, icon, type);
            img.enabled = true;

            editor.graph.getSelectionModel().addListener(mxEvent.CHANGE, function () {
                var tmp = editor.graph.isSelectionEmpty();
                mxUtils.setOpacity(img, (tmp) ? 100 : 20);
                img.enabled = tmp;
            });
        }
    };

    var addGroups = function(type) {
        if(typeof type == 'object' && !Object.keys(ft_groups).includes(type.group)) {
            var groupContainer = document.createElement('div');
            groupContainer.id = 'group_' + type.group;
            groupContainer.classList = 'group_sidebar collapse';
            var groupHeader = document.createElement('div');
            groupHeader.setAttribute('data-toggle', 'collapse');
            groupHeader.setAttribute('data-target', '#' + $.escapeSelector(groupContainer.id));
            groupHeader.setAttribute('aria-expanded', false);
            groupHeader.classList = 'group_sidebar_header collapsed';
            groupHeader.innerHTML = type.group;
            tbContainer.appendChild(groupHeader);
            tbContainer.appendChild(groupContainer);
            ft_groups[type.group] = new mxToolbar(groupContainer);
            ft_groups[type.group].enabled = false;
        }
    }

    var ft_groups = {};
    var ft = ['input', 'output', 'constanta'/*'body'*/];
    $call(manage_controllers['current_controller'], 'list_macro_functions', null, function(res) {
        var data = res.data;
        ft = ft.concat(data);
        console.log(ft);
        for (let f in ft) {
            addGroups(ft[f]);
            addVertex(ft[f]);
        }
        startView();
    }, function() {
        VanillaToasts.create({
            type: 'error',
            text: 'Server error. Unable to get macro function list.',
            timeout: 5000,
        });
    });
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
        var fName = title;
        if(typeof(title) === 'object') {
            fName = title.name;
        }
        for (let c in ts) {
            if (ts[c].id.split(' ')[0] === fName) {
                res.push(ts[c]);
            }
        }
        let r;
        if (res) {
            if (['input', 'output'].includes(fName)) {
                var max_y = 0;
                for(let i in res) {
                    if(res[i].geometry.y > max_y) {
                        r = res[i];
                        max_y = r.geometry.y;
                    }
                }
            }
            // else {
            //     let u = ['value, state', 'LT, GT', 'AND'];
            //     let group = 0;
            //     for (let t in u) {
            //         if (u[t].includes($(vertex.getAttribute('label')).attr('id'))) {
            //             group = t;
            //             break
            //         }
            //     }
            //     for (let rb = res.length; rb--;) {
            //         if (u[group].includes($(res[rb].getAttribute('label')).attr('id'))) {
            //             r = res[rb];
            //             break;
            //         }
            //     }
            // }
        }
        x = r ? r.geometry.x : x - 20;
        y = r ? r.geometry.y + 200 : y - 20;

        vertex.geometry.x = x;
        vertex.geometry.y = y;
        var idName = '';
        if(vertex.style === 'constanta') {
            vertex.block_name = 'const';
            x = x < 200 ? 200 : x;
        } else if(['input', 'output'].includes(vertex.style)) {
            vertex.block_name = vertex.style;
        } else {
            vertex.block_name = 'body';
            x = x < 400 ? 400 : x;
            var outs = [];
            var min_out;
            for (let c in ts) {
                if (ts[c].id.split(' ')[0] === 'output') {
                    outs.push(ts[c]);
                    if(!min_out || ts[c].geometry.x < min_out) {
                        min_out = ts[c].geometry.x;
                    }
                }
            }
            if(x + 300 > min_out) {
                for (let c in outs) {
                    outs[c].geometry.x = x + 300;
                }
                editor.refresh();
            }
        }
        res = 0;
        for (let c in ts) {
            if (ts[c].id.split(' ')[0] === vertex.block_name && +ts[c].id.split(' ')[1] > res) {
                res = +ts[c].id.split(' ')[1];
            }
        }
        vertex.id = vertex.block_name + ' ' + (res + 1);
        console.log(vertex.id);
        editor.addCell(vertex);
        if('input, output'.includes(vertex.block_name)) {
            t[vertex.block_name].push({var: fName, description: title.description})
        } else if(vertex.block_name === 'body') {
            t[vertex.block_name].push({id: res + 1, function: fName, params: []});
            if(title.var_in.length) {
                for(let i in title.var_in) {
                    t[vertex.block_name][t[vertex.block_name].length - 1].params[title.var_in[i].var] = '';
                }
            }
        }
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

    mxUtils.makeDraggable(img, editor.graph, funct, null, -20, -20);
    return img;
}

function sidebar_icon(type) {
    var img;
    if (['input', 'output'].includes(type)) {
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
    else if(type == 'constanta') {
        img = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">\n' +
            '    <defs>\n' +
            '        <style>\n' +
            '            .cls-1{font-size:20px;fill:#79c3f8;font-family:MyriadPro-Regular,Myriad Pro;}\n' +
            '        </style>\n' +
            '    </defs>\n' +
            '    <title>const</title>\n' +
            '    <g id="Layer_2" data-name="Layer 2">\n' +
            '        <g id="Layer_6" data-name="Layer 6">\n' +
            '            <ellipse cx="50" cy="50" rx="49" ry="49" fill="white" stroke="#faaf3b" stroke-width="2" />\n' +
            '            <text class="cls-1" transform="translate(12 55)">' + type + '</text>\n' +
            '        </g>\n' +
            '    </g>\n' +
            '</svg>';
    }
    else {
        let fun = 'value';
        img = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 204.76 263.49">\n' +
            '    <defs>\n' +
            '        <style>\n' +
            '            .cls-1{fill:none;stroke:#79c3f8;stroke-miterlimit:10;stroke-width:4px;}.cls-2{font-size:' + (65 - type.length*2.7) + 'px;fill:#79c3f8;font-family:MyriadPro-Regular,\n' +
            '            Myriad Pro;}\n' +
            '        </style>\n' +
            '    </defs>\n' +
            '    <title>input-output</title>\n' +
            '    <g id="Layer_2" data-name="Layer 2">\n' +
            '        <g id="Layer_6" data-name="Layer 6">\n' +
            '            <rect class="cls-1" x="-27.36" y="31.36" width="259.49"\n' +
            '                  height="200.76" rx="29.61" ry="29.61"\n' +
            '                  transform="translate(-29.36 234.12) rotate(-90)"/>\n' +
            '            <text class="cls-2" transform="translate(24.86 151.26)">' + type + '</text>\n' +
            '        </g>\n' +
            '    </g>\n' +
            '</svg>';
    }
    return img;
}
