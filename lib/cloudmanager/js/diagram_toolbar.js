//toolbar
function show_toolbar(toolbar, sidebar, editor) {

    // Workaround for Internet Explorer ignoring certain CSS directives
    if (mxClient.IS_QUIRKS) {
        document.body.style.overflow = 'hidden';
        new mxDivResizer(toolbar);
        new mxDivResizer(sidebar);
    }

    // Creates a new DIV that is used as a toolbar and adds toolbar buttons.
    var spacer = document.createElement('div');
    spacer.style.display = 'inline';
    spacer.style.padding = '8px';
    addToolbarButton(editor, toolbar, 'save', 'Save', 'images/diagram/save.png');
    toolbar.appendChild(spacer.cloneNode(true));

    addToolbarButton(editor, toolbar, 'undo', '', 'images/diagram/undo.png');
    addToolbarButton(editor, toolbar, 'redo', '', 'images/diagram/redo.png');
    toolbar.appendChild(spacer.cloneNode(true));

    addToolbarButton(editor, toolbar, 'delete', '', 'images/diagram/delete.png');
    toolbar.appendChild(spacer.cloneNode(true));

    // addSidebarIcon(graph, sidebar, 	table, 'https://jgraph.github.io/mxgraph/javascript/examples/images/icons48/table.png');
}

function addToolbarButton(editor, toolbar, action, label, image, isTransparent) {
    if (image != null) {
        var img = document.createElement('img');
        img.setAttribute('src', image);
        img.style.width = action === 'save' ? '100px' : '35px';
        img.style.height = '35px';
        img.style.verticalAlign = 'middle';
        img.style.marginRight = '2px';
        img.style.cursor = 'pointer';
        let path = image.split('/');
        let fn = path.pop().split('.');
        img.onmouseover = function () {
            let hov = path.join('/') + '/' + fn[0] + '_hover.' + fn[1];
            img.setAttribute('src', hov);
        };
        img.onmouseout = function () {
            img.setAttribute('src', image);
        }

    }
    mxEvent.addListener(img, 'click', function (evt) {
        if (action === 'new_shape') {
            new_shape(editor);
        }
        else if (action === 'save') {
            save_new(editor);
        }
        else {
            editor.execute(action);
        }
    });
    mxUtils.write(img, label);
    toolbar.appendChild(img);
};

//overwrite for show file sidebar
function new_shape(editor) {
    var side = document.getElementById('sidebarContainer');
    side.style.display = 'block';
    show_sidebar(side, editor);
};

function save_new(editor) {
    var new_t = Object();
    new_t['function'] = document.getElementById('title').innerText;
    var info = editor.graph.getModel().cells;
    var input = [];
    var output = [];
    var body = [];
    for (var r in info) {
        if (info[r].id.startsWith('input')) {
            input.push(info[r]);
        }
        else if (info[r].id.startsWith('body')) {
            body.push(info[r])
        }
        else if (info[r].id.startsWith('output')) {
            output.push(info[r])
        }
    }
    new_t['input'] = [];
    for (var i in input) {
        let label = $(input[i].value.getAttribute('label'));
        if (label.length > 0) {
            new_t['input'].push({
                'var': label.attr('id'),
                'description': label[2].innerHTML
            });
        }
    }

    new_t['body'] = [];
    for (var b in body) {
        let args;
        let id = Number(body[b].id.split(' ')[1]);
        let func = $(body[b].value.getAttribute('label'));
        let params = {};
        if (body[b].children) {
            for (var ch_b in body[b].children) {
                let child = body[b].children[ch_b];
                if (child.type === 'var_in') {
                    for (var e in child.edges) {
                        // if ('input'.includes(child.edges[e].target.block_name)) {
                        params = {'item_id': {'type': child.type}};
                        params.item_id.value = $(child.edges[e].target.value.getAttribute('label')).attr('id');
                        // }
                    }
                }
                else if (child.type === 'const') {
                    let parent_id = child.parent.id.split(' ')[1];
                    var ch = Object.keys(t.body[parent_id].params)[0];
                    for (var e in child.edges) {
                        if ('const'.includes(child.edges[e].target.block_name)) {
                            params[ch] = {
                                'type': child.type,
                                'value': $(child.edges[e].target.value.getAttribute('label')).attr('id')
                            };
                        }
                    }

                }
                else if (child.type === 'in_const' || child.type === 'in_var_in' || child.type === 'in_block_out') {
                    for (var e in child.edges) {
                        let v = child.type.split('_').slice(1,);
                        let val = child.type.includes(v.join('_')) ? $(child.edges[e].target.value.getAttribute('label')).attr('id') : Number(child.edges[e].target.parent.id.split(' ')[1]);
                        if (v.join('_') === 'block_out') {
                            v.push(child.edges[e].target.name);
                            val = Number(child.edges[e].target.parent.id.split(' ')[1]);
                        }
                        // let val = child.type.includes(v.join('_')) ? $(child.edges[e].target.value.getAttribute('label')).attr('id') : Number(child.edges[e].target.parent.id.split(' ')[1]);
                        if ($(child.value.getAttribute('label')).attr('id') === 'item_id') {
                            params = {'item_id': {'type': v.join('_')}};
                            params.item_id.value = val;
                        }
                        else {
                            let tName = $(child.value.getAttribute('label')).attr('id');
                            params[tName] = {'type': v.join('_')};
                            params[tName].value = val;
                        }
                    }
                }
                else if (child.type === 'args') {
                    args = [];
                    for (var e in child.edges) {
                        if ('block_out, in_block_out'.includes(child.edges[e].target.type)) {
                            args.push({
                                'type': 'block_out',
                                'value': Number(child.edges[e].target.parent.id.split(' ')[1])
                            });
                        }
                        else if ('input, const'.includes(child.edges[e].target.block_name)) {
                            args.push({
                                'type': child.edges[e].target.block_name === 'input' ? 'var_in' : 'const',
                                'value': $(child.edges[e].target.value.getAttribute('label')).attr('id')
                            });
                        }
                    }
                }
                if (args) {
                    params.args = args;
                }
            }
        }
        new_t.body.push({
            'id': id,
            'function': func.attr('id'),
            'params': params,
        });
    }

    new_t['output'] = [];
    for (var o in output) {
        let label = $(output[o].value.getAttribute('label'));
        if (label.length > 0) {
            let val;
            let name;
            for (var e in output[o].edges) {
                val = Number(output[o].edges[e].target.parent.id.split(' ')[1]);
                name = output[o].edges[e].target.name;
            }
            new_t['output'].push({
                'var': label.attr('id'),
                'value': val,
                'description': label[2].innerHTML,
                'name': name
            });
        }
    }

    console.log('new_t', new_t)
    // if (new_t) {
    //     $.ajax('/result', {
    //         method: "POST",
    //         contentType: "application/json",
    //         data: JSON.stringify(new_t),
    //         success: function (res) {
    //             location.href = '/result'
    //         },
    //         error: function () {
    //             alert('Try later')
    //         }
    //     })
    // }
}
