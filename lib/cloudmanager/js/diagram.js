function main(container, toolbar, sidebar) {
    if (!mxClient.isBrowserSupported()) {
        mxUtils.error('Browser is not supported!', 200, false);
    }
    else {
        $('.diagram_editor .eva_sfa_popup_header').html(t.function.toUpperCase());
        // mxConnectionHandler.prototype.connectImage = new mxImage('/static/img/connector.gif', 16, 16);


        var editor = new mxEditor();
        editor.setGraphContainer(container);
        var graph = editor.graph;
        show_toolbar(toolbar, sidebar, editor);
        graph.dropEnabled = true;
        // Enables new connections in the graph
        graph.setConnectable(true);
        graph.setMultigraph(false);

        //scrolling
        mxGraph.prototype.scrollCellToVisible = function (cell, center) {
        };
        //add style
        mxClient.link('stylesheet', 'css/diagram.css');
        // Stops editing on enter or escape keypress
        var rubberband = new mxRubberband(graph);

        //If you want the graph to be read-only
        // graph.setEnabled(false);

        //disable move edge
        graph.setAllowDanglingEdges(false);
        graph.setDisconnectOnMove(false);

        // get mouse click event
        // graph.addListener(mxEvent.CLICK, function (sender, evt) {
        // });

        //custom hover for blocks
        function updateStyle(state, hover) {
            if (hover) {
                if (state.cell.block_name === 'body') {
                    graph.setConnectable(false);
                }
                else {
                    graph.setConnectable(true);
                }
            }
            let strokeWidth = !state.style.strokeWidth ? '1' : state.style.strokeWidth;
            let strokeHover = state.cell.isVertex() ? '7' : '4';
            (hover && 'input, output, const'.includes(state.cell.block_name)) ? addOverlays(graph, state.cell) : graph.removeCellOverlay(state.cell);
            // Sets style for hover
            state.style[mxConstants.STYLE_STROKEWIDTH] = (hover) ? strokeHover : strokeWidth;
            state.style[mxConstants.STYLE_FONTSTYLE] = (hover) ? mxConstants.FONT_BOLD : '0';
        }

        // Changes fill color on mouseover
        graph.addMouseListener(
            {
                currentState: null,
                previousStyle: null,
                mouseDown: function (sender, me) {
                    if (this.currentState != null) {
                        this.dragLeave(me.getEvent(), this.currentState);
                        this.currentState = null;
                    }
                },
                mouseMove: function (sender, me) {
                    if (this.currentState != null && me.getState() == this.currentState) {
                        return;
                    }
                    var tmp = graph.view.getState(me.getCell());
                    // Ignores everything but vertices
                    if (graph.isMouseDown || (tmp != null && !tmp.cell))
                    // (tmp != null && !graph.getModel().isVertex(tmp.cell)))
                    {
                        tmp = null;
                    }
                    if (tmp != this.currentState) {
                        if (this.currentState != null) {
                            this.dragLeave(me.getEvent(), this.currentState);
                        }
                        this.currentState = tmp;
                        if (this.currentState != null) {
                            this.dragEnter(me.getEvent(), this.currentState);
                        }
                    }
                },
                mouseUp: function (sender, me) {
                },
                dragEnter: function (evt, state) {
                    if (state != null) {
                        this.previousStyle = state.style;
                        state.style = mxUtils.clone(state.style);
                        updateStyle(state, true);
                        state.shape.apply(state);
                        state.shape.redraw();

                        if (state.text != null) {
                            state.text.apply(state);
                            state.text.redraw();
                        }
                    }
                },
                dragLeave: function (evt, state) {
                    if (state.shape != null) {
                        state.style = this.previousStyle;
                        updateStyle(state, false);
                        state.shape.apply(state);
                        state.shape.redraw();

                        if (state.text != null) {
                            state.text.apply(state);
                            state.text.redraw();
                        }
                    }
                }
            });

        graph.setDropEnabled(false);

        var keyHandler = new mxKeyHandler(graph);
        keyHandler.bindKey(46, function (evt) {
            editor.execute('delete');
        });

        keyHandler.bindControlKey(90, function (evt) {
            editor.execute('undo');
        });

        keyHandler.bindControlKey(89, function (evt) {
            editor.execute('redo');
        });

        keyHandler.bindControlKey(83, function (evt) {
            save_new(editor);
        });


        // keyHandler.getFunction = function (evt) {
        //     console.log('evt', evt)
        // };

        mxGraphHandler.prototype.previewColor = 'green';


        mxGraphHandlergetBoundingBox = mxGraphHandler.prototype.getBoundingBox;
        mxGraphHandler.prototype.getPreviewBounds = function (cells) {
            console.log('cells', arguments)
            var pos = this.bounds;
            if(this.cell.block_name === 'body') {
                let outs = [];
                let min_out = pos.x + 400;
                let all_cells = this.graph.getModel().cells;
                for(let o in all_cells) {
                    if(all_cells[o].block_name == 'output') {
                        outs.push(all_cells[o]);
                        if(min_out > all_cells[o].geometry.x) {
                            min_out = all_cells[o].geometry.x;
                        }
                    }
                }
                if(pos.x + 300 > min_out) {
                    for (let o in outs) {
                        outs[o].geometry.x = pos.x + 300;
                    }
                    editor.graph.refresh();
                }
            }
            return mxGraphHandlergetBoundingBox.apply(this, arguments)
        }

        // mxGraphHandlercreatePreviewShape = mxGraphHandler.prototype.createPreviewShape;
        // mxGraphHandler.prototype.createPreviewShape = function (bounds) {
        //     var shape = this.cells[0].clone();
        //     shape.isDashed = true;

            // if (this.htmlPreview) {
            //     shape.dialect = mxConstants.DIALECT_STRICTHTML;
            //     shape.init(this.graph.container);
            // }
            // else {
            //     // Makes sure to use either VML or SVG shapes in order to implement
            //     // event-transparency on the background area of the rectangle since
            //     // HTML shapes do not let mouseevents through even when transparent
            //     shape.dialect = (this.graph.dialect != mxConstants.DIALECT_SVG) ?
            //         mxConstants.DIALECT_VML : mxConstants.DIALECT_SVG;
            //     shape.init(this.graph.getView().getOverlayPane());
            //     shape.pointerEvents = true;
            //     shape = this.cells[0]
            //     console.log('shape', shape)
            //     console.log('cell', this.graph.getView())
            //
            //     // Workaround for artifacts on iOS
            //     if (mxClient.IS_IOS) {
            //         shape.getSvgScreenOffset = function () {
            //             return 0;
            //         };
            //     }
            // }

            // console.log('shape 1', shape)
            // return shape
            // return mxGraphHandlercreatePreviewShape.apply(this, arguments)
        // };

        graph.convertValueToString = function (cell) {
            if (mxUtils.isNode(cell.value)) {
                return cell.getAttribute('label', '')
            }
        };

        //change label value
        var graphCellLabelChanged = graph.cellLabelChanged;
        graph.cellLabelChanged = function (cell, newValue, autoSize) {
            // Cloned for correct undo/redo
            var elt = cell.value ? cell.value.cloneNode(true) : '';
            let newname = block_name(newValue, cell.block_name ? cell.block_name : cell.type);
            elt.setAttribute('label', newname);
            newValue = elt;
            graphCellLabelChanged.apply(this, arguments);
        };

        //autoresize vertex
        graph.setAutoSizeCells(true);
        graph.setCellsResizable(false);


        graph.htmlLabels = true;

        //disable doubleclick
        graph.dblClick = function (evt, cell) {
        };

        //change vertex selection color
        mxVertexHandler.prototype.getSelectionColor = function () {
            return '#b92c28';
        };
        mxVertexHandler.prototype.getSelectionStrokeWidth = function () {
            return '4';
        };

        mxConstants.CURSOR_CONNECT = 'crosshair';
        mxConstants.HIGHLIGHT_COLOR = null;

        //style for input
        var style = new Object();
        style[mxConstants.STYLE_SHAPE] = mxConstants.SHAPE_RECTANGLE;
        style[mxConstants.STYLE_ROUNDED] = '1';
        style[mxConstants.STYLE_CURVED] = '1';
        style[mxConstants.STYLE_ARCSIZE] = '50';
        style[mxConstants.STYLE_ABSOLUTE_ARCSIZE] = '1';
        style[mxConstants.STYLE_FONTCOLOR] = '#0B5484';
        style[mxConstants.STYLE_FONTSIZE] = '14';
        style[mxConstants.STYLE_STROKECOLOR] = '#0094DB';
        style[mxConstants.STYLE_STROKEWIDTH] = '4';
        style[mxConstants.STYLE_FILLCOLOR] = 'white';
        style[mxConstants.STYLE_MOVABLE] = '1';
        graph.getStylesheet().putCellStyle('input', style);

        //style for output
        var style = new Object();
        style[mxConstants.STYLE_SHAPE] = mxConstants.SHAPE_RECTANGLE;
        style[mxConstants.STYLE_ROUNDED] = '1';
        style[mxConstants.STYLE_CURVED] = '1';
        style[mxConstants.STYLE_ARCSIZE] = '50';
        style[mxConstants.STYLE_ABSOLUTE_ARCSIZE] = '1';
        style[mxConstants.STYLE_FONTCOLOR] = '#0B5484';
        style[mxConstants.STYLE_FONTSIZE] = '14';
        style[mxConstants.STYLE_STROKECOLOR] = '#A070C4';
        style[mxConstants.STYLE_STROKEWIDTH] = '4';
        style[mxConstants.STYLE_FILLCOLOR] = 'white';
        style[mxConstants.STYLE_MOVABLE] = '1';
        graph.getStylesheet().putCellStyle('output', style);

        //style for body
        var style = new Object();
        style[mxConstants.STYLE_SHAPE] = mxConstants.SHAPE_RECTANGLE;
        style[mxConstants.STYLE_VERTICAL_ALIGN] = mxConstants.ALIGN_TOP;
        style[mxConstants.STYLE_ROUNDED] = '1';
        style[mxConstants.STYLE_CURVED] = '1';
        style[mxConstants.STYLE_ARCSIZE] = '8';
        style[mxConstants.STYLE_SPACING_TOP] = '10';
        style[mxConstants.STYLE_FILLCOLOR] = 'white';
        style[mxConstants.STYLE_FONTCOLOR] = '#0B5484';
        style[mxConstants.STYLE_STROKEWIDTH] = '4';
        style[mxConstants.STYLE_FOLDABLE] = '0';
        style[mxConstants.STYLE_STROKECOLOR] = '#79C3F8';
        graph.getStylesheet().putCellStyle('body', style);

        //style for child
        var style = new Object();
        style[mxConstants.STYLE_SHAPE] = mxConstants.SHAPE_RECTANGLE;
        style[mxConstants.STYLE_VERTICAL_ALIGN] = mxConstants.ALIGN_MIDDLE;
        style[mxConstants.STYLE_ROUNDED] = '1';
        style[mxConstants.STYLE_CURVED] = '1';
        style[mxConstants.STYLE_ARCSIZE] = '20';
        style[mxConstants.STYLE_FILLCOLOR] = '#1A76D7';
        style[mxConstants.STYLE_FONTCOLOR] = '#EEE';
        style[mxConstants.STYLE_FONTSIZE] = '13';
        style[mxConstants.STYLE_FOLDABLE] = '0';
        style[mxConstants.STYLE_EDITABLE] = '0';
        style[mxConstants.STYLE_MOVABLE] = '0';
        graph.getStylesheet().putCellStyle('body_child', style);

        //style for constants
        var style = new Object();
        style[mxConstants.STYLE_SHAPE] = mxConstants.SHAPE_ELLIPSE;
        style[mxConstants.STYLE_FONTSIZE] = '14';
        style[mxConstants.STYLE_FONTCOLOR] = '#FF721E';
        style[mxConstants.STYLE_FILLCOLOR] = 'white';
        style[mxConstants.STYLE_STROKEWIDTH] = '4';
        style[mxConstants.STYLE_STROKECOLOR] = '#FAAF3B';
        graph.getStylesheet().putCellStyle('constanta', style);

        //style for edge
        var style = new Object();
        style[mxConstants.STYLE_EDGE] = mxEdgeStyle.EntityRelation;
        style[mxConstants.STYLE_DASHED] = '0';
        style[mxConstants.STYLE_MOVABLE] = '1';
        style[mxConstants.STYLE_STARTARROW] = mxConstants.ARROW_CLASSIC;
        style[mxConstants.STYLE_ENDARROW] = mxConstants.ARROW_DIAMOND;
        style[mxConstants.STYLE_STROKEWIDTH] = '2';
        style[mxConstants.EDGE_SELECTION_STROKEWIDTH] = '1';
        style[mxConstants.STYLE_STROKECOLOR] = '#0094DB';
        graph.getStylesheet().putCellStyle('body_input', style);

        var style = new Object();
        style[mxConstants.STYLE_EDGE] = mxEdgeStyle.SideToSide;
        style[mxConstants.STYLE_DASHED] = '1';
        style[mxConstants.STYLE_MOVABLE] = '1';
        style[mxConstants.STYLE_STARTARROW] = mxConstants.ARROW_CLASSIC;
        style[mxConstants.STYLE_ENDARROW] = mxConstants.ARROW_DIAMOND;
        style[mxConstants.STYLE_STROKEWIDTH] = '2';
        style[mxConstants.STYLE_STROKECOLOR] = '#FF721E';
        graph.getStylesheet().putCellStyle('constanta_input', style);

        var style = new Object();
        style[mxConstants.STYLE_EDGE] = mxEdgeStyle.SideToSide;
        style[mxConstants.STYLE_DASHED] = '1';
        style[mxConstants.STYLE_MOVABLE] = '1';
        style[mxConstants.STYLE_STARTARROW] = mxConstants.ARROW_CLASSIC;
        style[mxConstants.STYLE_ENDARROW] = mxConstants.ARROW_DIAMOND;
        style[mxConstants.STYLE_STROKEWIDTH] = '2';
        style[mxConstants.STYLE_STROKECOLOR] = '#1A76D7';
        graph.getStylesheet().putCellStyle('body_ch', style);

        var style = new Object();
        style[mxConstants.STYLE_EDGE] = mxEdgeStyle.EntityRelation;
        style[mxConstants.STYLE_DASHED] = '0';
        style[mxConstants.STYLE_MOVABLE] = '1';
        style[mxConstants.STYLE_STARTARROW] = mxConstants.ARROW_CLASSIC;
        style[mxConstants.STYLE_ENDARROW] = mxConstants.ARROW_DIAMOND;
        style[mxConstants.STYLE_STROKEWIDTH] = '2';
        style[mxConstants.STYLE_STROKECOLOR] = '#00E368';
        graph.getStylesheet().putCellStyle('body_output', style);

        // ----------------- control for new connections ---------------------- //
        graph.connectionHandler.addListener(mxEvent.CONNECT, function (sender, evt) {
            var edge = evt.getProperty('cell');
            if (edge.source.block_name === 'input' || edge.target.block_name === 'input') {
                edge.style = 'body_input';
            }
            else if (edge.source.block_name === 'output' || edge.target.block_name === 'output') {
                edge.style = 'body_output';
            }
            else if (edge.source.block_name === 'const' || edge.target.block_name === 'const') {
                edge.style = 'constanta_input';
            }
            else {
                edge.style = 'body_ch';
            }
        });

        var connectionHandlerConnect = mxConnectionHandler.prototype.connect;
        mxConnectionHandler.prototype.connect = function (source, target, evt, dropTarget, style) {
            if (['input', 'const'].includes(source.block_name) || target.block_name === 'output') {
                source = [target, target = source][0];
            }
            console.log('global s', source)
            console.log('global t', target)
            if (source.block_name === 'input' && target.block_name === 'const') {
                return false;
            }

            if (target.block_name === 'input') {
                if (source.block_name === 'const' || source.block_name === 'output' || source.block_name === 'input' ||
                    (source.type && source.type.includes('out'))) {
                    return false;
                }
                if (source.type === 'in_const') {
                    source.type = 'in_var_in';
                    source.value = block_name('item_id');
                    graph.getModel().remove(source.edges[0]);
                }
                else if (source.block_name !== 'body') {
                    if (source.type !== 'args') {
                        source.type = 'var_in';
                        if (source.edges) {
                            graph.getModel().remove(source.edges[0]);
                        }
                    }
                }
            }
            if (source.block_name === 'body') {
                if ('input, const'.includes(target.block_name)) {
                    let type = target.block_name === 'input' ? 'var_in' : 'const';
                    for (var c = 0; c < Object.keys(source.children).length; c++) {
                        if (!source.children[c].edges && 'var_in'.includes(source.children[c].type)) {
                            source = source.children[c];
                            source.type = type;
                            break;
                        }
                        else if (source.children[c].type === 'args') {
                            source = source.children[c];
                            break;
                        }
                        else {
                            if (source.children[0].type !== 'out' && source.children[0].edges) {
                                graph.getModel().remove(source.children[0].edges[0]);
                                source = source.children[0];
                                console.log('source', source)
                                source.type = type;
                                break;
                            }
                            /************?????????????*************/
                            // else {
                            //     console.log('source', source)
                            //     let var_in = graph.insertVertex(source, null, block_name('item_id'), 10, 90, 50, 30, 'body_child');
                            //     var_in.type = 'in_var_in';
                            //     source = var_in;
                            //     break;
                            // }
                            /***********??????????????*************/
                        }
                    }
                }
            }
            if (target.block_name === 'body' && !source.block_name) {
                if (source.type && source.parent.id !== target.id) {

                    if (source.type === 'out') {
                        let ch = target.children;
                        for (var c = 0; c < Object.keys(ch).length; c++) {
                            if (!ch[c].edges && ch[c].type.includes('in')) {
                                target = ch[c];
                                break;
                            }
                            else if (ch[c].type === 'args') {
                                target = ch[c];
                                break;
                            }
                            else {
                                let t = [];
                                target.children.map(f => {
                                    if (f.type.includes('in') || f.type.includes('const')) t.push(f)
                                });
                                if (t.length > 0 && t[0].edges) {
                                    graph.getModel().remove(t[0].edges[0]);
                                }
                                /***********??????????????*************/
                                // else {
                                //     t[0] = graph.insertVertex(target, null, block_name('item_id'), 10, 90, 50, 30, 'body_child');
                                //     t[0].type = 'in_block_out'
                                // }
                                /***********??????????????*************/
                                target = t[0];
                                break;
                                target.type = 'in_block_out';
                            }
                        }
                        source = [target, target = source][0];
                    }

                    if ('var_in, const, in_const, args'.includes(source.type) ||
                        (source.type === 'in_block_out' && target.type !== 'out')) {
                        if (source.edges && source.type !== 'args') {
                            graph.getModel().remove(source.edges[0])
                        }
                        if(!target.type) {
                            let ch = target.children;
                            for (var c = 0; c < Object.keys(ch).length; c++) {
                                if (ch[c].type && ch[c].type === 'out') {
                                    target = ch[c];
                                    break;
                                }
                                /***********??????????????*************/
                                // else if (!ch[c].type || ch[c].type !== 'out') {
                                //     let tar = graph.insertVertex(target, null, block_name('out'), 100, 90, 50, 30, 'body_child');
                                //     target = tar;
                                //     break;
                                // }
                                /***********??????????????*************/
                            }
                        }
                        if (source.type !== 'args') {
                            source.type = 'in_block_out';
                        }
                        target.type = 'out';
                    }
                }
            }
            if (source.type) {
                if (source.parent.id === target.id) {
                    return false;
                }
                if (target.type) {
                    //todo check args, in_block_out children of body
                    let t = [];
                    if ('out, args'.includes(source.type)) {
                        source = [target, target = source][0];
                    }
                    if (source.edges) {
                        source.edges.map(f => {
                            if (+f.source.id === +target.id) t.push(+f.source.id)
                        });
                    }
                    if (source.type === target.type || t.length > 0 || source.parent.id === target.parent.id ||
                        ['in_block_out', 'in', 'var_in', 'const', 'in_const', 'args'].includes(source.type) && 
                        ['in_block_out', 'in', 'var_in', 'const', 'in_const', 'args'].includes(target.type)) {
                        return false;
                    }
                    if ('args'.includes(target.type)) {
                        if ('in, var_in, const, in_const'.includes(source.type)) {
                            source.type = 'out';
                            source.value = block_name('out');
                            if (source.edges) {
                                graph.getModel().remove(source.edges[0]);
                            }
                        }
                        if (source.type === 'out') {
                            if (target.type !== 'args') {
                                graph.getModel().remove(target.edges[0])
                            }
                            source = [target, target = source][0];
                        }
                    }
                    if ('var_in, const, in_const'.includes(source.type) || 
                        source.type === 'in_block_out' && target.type !== 'args') {
                        if (target.edges && target.type !== 'out') {
                            graph.getModel().remove(target.edges[0])
                        }
                        if (source.edges) {
                            graph.getModel().remove(source.edges[0])
                        }
                        /***********??????????????*************/
                        // source.type = 'in_block_out';
                        // target.type = 'out';
                        // target.geometry.x = 90;
                        // graph.cellLabelChanged(target, 'out');
                        /***********??????????????*************/
                    }
                }
                if (target.block_name === 'const') {
                    // if (source.type.includes('out')) {
                    if (source.type === 'out') {
                        return false;
                    }
                    else if (source.type.includes('in') || source.type.includes('const')) {
                        source.type = 'const';
                        if (source.edges) {
                            graph.getModel().remove(source.edges[0]);
                        }
                    }
                }
            }
            if (source.block_name === 'output') {
                console.log('output', source)
                // if (target.block_name === 'const' || target.block_name === 'output' || (target.type && !target.type.includes('out'))) {
                if (target.block_name === 'const' || target.block_name === 'output' || (target.type && target.type !== 'out')) {
                    return false;
                }
                if (target.block_name === 'body') {
                    for (var c = 0; c < Object.keys(target.children).length; c++) {
                        if (target.children[c].type.includes('out')) {
                            target = target.children[c];
                            break;
                        }
                    }
                }
                if (source.edges) {
                    graph.getModel().remove(source.edges[0]);
                }
            }
            return connectionHandlerConnect.apply(this, arguments);
        };

        graph.getModel().beginUpdate();

        var parent = graph.getDefaultParent();

        var x = 100;
        var y = 100;

        var g_el_in = [];
        var g_el_body = [];
        var g_el_out = [];

        try {
            //input
            for (var i = 0; i < t.input.length; i++) {
                var id = 'input ' + i;
                var name = block_name(t.input[i], 'input');
                g_el_in[i] = graph.insertVertex(parent, id, name, x, (i === 0 ? y : y + i * 200), 140, 70, 'input');
                g_el_in[i].block_name = 'input';
            }
            //body
            //value & state
            var body_content = [];
            body_content[0] = [];
            body_content[1] = [];
            body_content[2] = [];
            var b_x = 400;
            var b_y;
            var b_y_t = 100;
            var b_y_a = 100;
            for (var nb = 0; nb < t.body.length; nb++) {
                var id = 'body ' + nb;
                var name = block_name(t.body[nb], 'body');
                if ('value, state'.includes(t.body[nb].function)) {
                    b_y = nb === 0 ? 100 : b_y + 200;
                }
                else if ('LT, GT'.includes(t.body[nb].function)) {
                    b_x = 700;
                    b_y = b_y_t;
                    b_y_t += 200;
                }
                else if ('AND'.includes(t.body[nb].function)) {
                    b_x = 1000;
                    b_y = b_y_a;
                    b_y_a += 200;
                }
                g_el_body[nb] = graph.insertVertex(parent, id, name, b_x, b_y, 150, 170, 'body;');
                g_el_body[nb].block_name = 'body';
            }
            //body's edges
            for (var b in g_el_body) {
                var x = isKeyExist(t.body[b].params, 'item_id');
                if (x) {
                    if (t.body[b].params.item_id.type === 'var_in') {
                        body_content[0].push(t.body[b].id);
                        let inp = graph.insertVertex(g_el_body[b], null, block_name(Object.keys(t.body[b].params)[0]), 10, 90, 50, 30, 'body_child');
                        inp['type'] = 'var_in';
                        for (var i in g_el_in) {
                            var l = $(g_el_in[i].getAttribute('label'));
                            if (t.body[b].params.item_id.value === l.attr('id')) {
                                graph.insertEdge(parent, null, '', inp, g_el_in[i], 'body_input');
                            }
                        }
                    }
                    else if (t.body[b].params.item_id.type === 'const') {
                        body_content[0].push(t.body[b].id);
                        let inp = graph.insertVertex(g_el_body[b], null, block_name(Object.keys(t.body[b].params)), 10, 90, 50, 30, 'body_child');
                        inp['type'] = 'const';
                        if (t.body[b].params.item_id.value) {
                            let x = g_el_body[b].geometry.x;
                            let y = g_el_body[b].geometry.y;
                            let constanta = graph.insertVertex(parent, null, block_name(t.body[b].params.item_id.value), x - 150, y, 100, 100, 'constanta');
                            constanta.block_name = 'const';
                            graph.insertEdge(parent, null, '', inp, constanta, 'constanta_input');
                        }
                    }
                    else if (t.body[b].params.item_id.type === 'block_out') {
                        body_content[0].push(t.body[b].id);
                        let inp = graph.insertVertex(g_el_body[b], null, block_name(Object.keys(t.body[b].params)[0]), 10, 90, 50, 30, 'body_child');
                        inp['type'] = 'in_block_out';
                        for (var i in g_el_body) {
                            var l = g_el_body[i].id.split(' ');
                            if (t.body[b].params.item_id.value === Number(l[1])) {
                                // let point_out = [];
                                // for (let p in g_el_body[i].children) {
                                //     if (g_el_body[i].children[p].type === 'out') {
                                //         point_out.push(g_el_body[i].children[p]);
                                //     }
                                // }
                                // if (point_out.length === 0) {
                                let out = graph.insertVertex(g_el_body[i], null, block_name('out'), 90, 90, 50, 30, 'body_child');
                                out['type'] = 'out';
                                // point_out.push(out)
                                // }
                                graph.insertEdge(parent, null, '', inp, out, 'body_ch');
                            }
                        }
                    }
                }
                if (isKeyExist(t.body[b].params, 'args') || isKeyExist(t.body[b].params, 'IN')) {
                    var u = -1;
                    if (isKeyExist(t.body[b].params, 'args')) {
                        var args_values = [];
                        var inp_value = [];
                        var inp_const = []
                        for (var n = 0; n < t.body[b].params.args.length; n++) {
                            if (t.body[b].params.args[n].type === 'var_in') {
                                for (let i in g_el_in) {
                                    if (t.body[b].params.args[n].value === $(g_el_in[i].getAttribute('label')).attr('id')) {
                                        inp_value.push(g_el_in[i].id)
                                    }
                                }
                            }
                            if (t.body[b].params.args[n].type === 'const') {
                                inp_const.push(t.body[b].params.args[n].value)
                            }
                            if (t.body[b].params.args[n].type === 'block_out') {
                                args_values.push(t.body[b].params.args[n].value)
                            }
                        }
                    }
                    u = u >= 0 ? u : 0;
                    body_content[u].push(t.body[b].id);
                    let inp = graph.insertVertex(g_el_body[b], null, block_name('args'), 10, 130, 50, 30, 'body_child');
                    inp['type'] = 'args';
                    if (inp_value) {
                        for (let i in inp_value) {
                            for (let g_in in g_el_in) {
                                if (inp_value[i] === g_el_in[g_in].id) {
                                    graph.insertEdge(parent, null, '', inp, g_el_in[g_in], 'body_input');
                                }
                            }
                        }
                    }
                    if (inp_const) {
                        for (let c in inp_const) {
                            let x = g_el_body[b].geometry.x;
                            let y = g_el_body[b].geometry.y;
                            let constanta = graph.insertVertex(parent, null, block_name(inp_const[c]), x - 140, y + 100, 80, 80, 'constanta');
                            constanta.block_name = 'const';
                            graph.insertEdge(parent, null, '', inp, constanta, 'constanta_input');
                        }
                    }
                    if (args_values) {
                        for (let a in args_values) {
                            let b_id = args_values[a] instanceof Array ? args_values[a][0] : args_values[a];
                            for (let b in g_el_body) {
                                if (b_id === +g_el_body[b].id.split(' ')[1]) {
                                    out = graph.insertVertex(g_el_body[b], null, block_name('out'), 90, 90, 50, 30, 'body_child');
                                    out['type'] = 'out';
                                    graph.insertEdge(parent, null, '', inp, out, 'body_ch');
                                }
                            }
                        }
                    }
                    if (isKeyExist(t.body[b].params, 'IN')) {
                        if (t.body[b].params.IN.type === 'const') {
                            let inp = graph.insertVertex(g_el_body[b], null, block_name('IN'), 10, 90, 50, 30, 'body_child');
                            inp['type'] = 'in_const';
                            let x = g_el_body[b].geometry.x;
                            let y = g_el_body[b].geometry.y;
                            let constanta = graph.insertVertex(parent, null, block_name(t.body[b].params.IN.value), x - 120, y, 80, 80, 'constanta');
                            constanta.block_name = 'const';
                            graph.insertEdge(parent, null, '', inp, constanta, 'constanta_input');
                        }
                        else if (t.body[b].params.IN.type === 'var_in') {
                            let inp = graph.insertVertex(g_el_body[b], null, block_name(Object.keys(t.body[b].params)[0]), 10, 90, 50, 30, 'body_child');
                            inp['type'] = 'in_var_in';
                            for (var i in g_el_in) {
                                var l = $(g_el_in[i].getAttribute('label'));
                                if (t.body[b].params.IN.value === l.attr('id')) {
                                    graph.insertEdge(parent, null, '', inp, g_el_in[i], 'body_input');
                                }
                            }
                        }
                        else if (t.body[b].params.IN.type === 'block_out') {
                            let inp = graph.insertVertex(g_el_body[b], null, block_name(Object.keys(t.body[b].params)[0]), 10, 90, 50, 30, 'body_child');
                            inp['type'] = 'in_block_out';
                            for (var i in g_el_body) {
                                if (t.body[b].params.IN.value === +g_el_body[i].id.split(' ')[1]) {
                                    let out = false;
                                    for (let ch in g_el_body[i].children) {
                                        if (g_el_body[i].children[ch].type === 'out') {
                                            out = g_el_body[i].children[ch];
                                        }
                                    }
                                    if (!out) {
                                        out = graph.insertVertex(g_el_body[i], null, block_name('out'), 100, 90, 50, 30, 'body_child');
                                    }
                                    out['type'] = 'out';
                                    graph.insertEdge(parent, null, '', inp, out, 'body_ch');
                                }
                            }
                        }
                    }
                }
            }
            for (var o = 0; o < t.output.length; o++) {
                var id = 'output ' + o;
                var name = block_name(t.output[o], 'output');
                g_el_out[o] = graph.insertVertex(parent, id, name, 1300, (o === 0 ? y : y + o * 200), 140, 70, "output");
                g_el_out[o].block_name = 'output';
                var out = t.output[o].value instanceof Array ? t.output[o].value[0] : t.output[o].value;
                for (var elem in g_el_body) {
                    if (out === Number(g_el_body[elem].id.split(' ').pop())) {
                        let out = graph.insertVertex(g_el_body[elem], null, block_name('out'), 90, 130, 50, 30, 'body_child');
                        out['type'] = 'out';
                        graph.insertEdge(parent, null, '', g_el_out[o], out, 'body_output');
                    }
                }
            }
        }
        finally {
            graph.getModel().endUpdate();
            show_sidebar(sidebar, editor);
        }
    }
}


//create block name and add constanta's attribute
function block_name(label, type = false) {
    var doc = mxUtils.createXmlDocument();
    var block = doc.createElement('block');
    var name;
    if (type === 'input' || type === 'output') {
        if (typeof label === 'object') {
            name = "<span id='" + label.var + "'><b>" + label.var + "</b></span><br>" +
                "<span style='color: #4D4D4D' desc='" + label.description + "'>" + label.description + "</span>";
        }
        else if (typeof label === 'string') {
            let l = label.split('-');
            return "<span id='" + l[0] + "'><b>" + l[0] + "</b></span><br>" +
                "<span style='color: #4D4D4D' desc='" + (l[1] || '') + "'>" + (l[1] || '') + "</span>";
        }

    }
    else if (type === 'body') {
        if (typeof label === 'object') {
            name = "<span style='font-size: large' id='" + label.function + "'><b>" + label.function.toUpperCase() + "</b></span><br>";
        }
        else if (typeof label === 'string') {
            return "<span style='font-size: large' id='" + label + "'><b>" + label.toUpperCase() + "</b></span><br>";
        }
    }
    else if (type === 'const' || type === 'out') {
        return "<span id='" + label + "'>" + label + "</span>";
    }
    else if (!type) {
        name = "<span id='" + label + "'>" + label + "</span>";
    }
    else if (typeof label === 'object') {
        name = "<span style='font-size: large' id='" + label.var + "'><b>" + label.var + "</b></span><br>" +
            "<span style='color: #4D4D4D' desc='" + label.description + "'>" + label.description + "</span>";
    }
    block.setAttribute('label', name);
    return block;
}


function isKeyExist(object, key) {
    var d = false;
    for (var k in object) {
        if (k === key) {
            return true;
        }
        else if (object[k] instanceof Object) {
            d = isKeyExist(object[k], key);
        }
    }
    if (d) {
        return true;
    }
    return false;
}

function addOverlays(graph, cell) {
    var stroke = graph.stylesheet.getCellStyle(cell.style);
    var im = edit_icon(stroke.strokeColor, false);
    var im1 = del_icon(stroke.strokeColor, false);
    var overlay = new mxCellOverlay(new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(im)), 40, 40), 'Edit');
    var overlay1 = new mxCellOverlay(new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(im1)), 35, 35), 'Delete');
    overlay.cursor = overlay1.cursor = 'hand';
    overlay.align = overlay1.align = mxConstants.ALIGN_RIGHT;
    overlay.verticalAlign = overlay1.verticalAlign = mxConstants.ALIGN_TOP;
    overlay.tagName = 'edit';
    overlay1.tagName = 'del';
    overlay.getBounds = function (state) {
        var bounds = mxCellOverlay.prototype.getBounds.apply(this, arguments);
        if ('input, output'.includes(state.cell.style)) {
            bounds.x = state.cell.geometry.x + 80;
        }
        else if (state.cell.style === 'constanta') {
            if (state.cell.geometry.width < 100) {
                bounds.x = state.cell.geometry.x + 20;
                bounds.y = state.cell.geometry.y - 16;
            }
            else {
                bounds.x = state.cell.geometry.x + 30;
                bounds.y = state.cell.geometry.y - 16;
            }
        }
        return bounds;
    };
    overlay1.getBounds = function (state) {
        var bounds = mxCellOverlay.prototype.getBounds.apply(this, arguments);
        if ('input, output'.includes(state.cell.style)) {
            bounds.x = state.cell.geometry.x + 118;
        }
        else if (state.cell.style === 'constanta') {
            if (state.cell.geometry.width < 100) {
                bounds.x = state.cell.geometry.x + 58;
                bounds.y = state.cell.geometry.y - 12;
            }
            else {
                bounds.x = state.cell.geometry.x + 68;
                bounds.y = state.cell.geometry.y - 12;
            }
        }
        return bounds;
    };

    var mxCellRendererInstallCellOverlayListeners = mxCellRenderer.prototype.installCellOverlayListeners;
    mxCellRenderer.prototype.installCellOverlayListeners = function (state, overlay, shape) {
        var stroke = graph.stylesheet.getCellStyle(state.cell.style);

        mxEvent.addListener(shape.node, 'mouseover', mxUtils.bind(this, function (evt) {
            if (overlay.tagName === 'edit') {
                let y = edit_icon(stroke.strokeColor, true);
                let n = new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(y)), 40, 40);
                evt.path[0].attributes[4].nodeValue = n.src;
            }
            else if (overlay.tagName === 'del') {
                let y = del_icon(stroke.strokeColor, true);
                let n = new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(y)), 35, 35);
                evt.path[0].attributes[4].nodeValue = n.src;
            }
        }));
        mxEvent.addListener(shape.node, 'mouseout', mxUtils.bind(this, function (evt) {
            if (overlay.tagName === 'edit') {
                let y = edit_icon(stroke.strokeColor, false);
                let n = new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(y)), 40, 40);
                evt.path[0].attributes[4].nodeValue = n.src;
            }
            else if (overlay.tagName === 'del') {
                let y = del_icon(stroke.strokeColor, false);
                let n = new mxImage(('mySvgImage', 'data:image/svg+xml,' + encodeURIComponent(y)), 35, 35);
                evt.path[0].attributes[4].nodeValue = n.src;
            }
        }));
        return mxCellRendererInstallCellOverlayListeners.apply(this, arguments);
    };

    overlay.addListener(mxEvent.CLICK, function (sender, evt) {
        showEdit(graph, cell);
    });

    overlay1.addListener(mxEvent.CLICK, function (sender, evt) {
        graph.getModel().remove(evt.properties.cell)
    });

    graph.addCellOverlay(cell, overlay);
    graph.addCellOverlay(cell, overlay1);
}

function showEdit(graph, cell) {
    var form = new mxForm('Edit');
    form.table.style.margin = '0 4px';
    form.table.style.width = '280px'
    let label = $(cell.getAttribute('label'));
    var window_height = 200;
    if (cell.block_name === 'input' || cell.block_name === 'output') {
        var nameField = form.addText('Name:', (label.attr('id') ? label.attr('id') : null));
        var descField = form.addText('Description:', (label[2] ? label[2].innerHTML : null));
        window_height = 220;
    }
    else {
        var nameField = form.addText('Value:', label.attr('id'));
    }

    var wnd = null;
    // Defines the function to be executed when the
    // Cancel button is pressed in the dialog
    var cancelFunction = function () {
        wnd.destroy();
    };
    // Defines the function to be executed when the
    // OK button is pressed in the dialog
    var okFunction = function () {
        let newValue = ('input, output'.includes(cell.block_name)) ? nameField.value + '-' + descField.value : nameField.value;
        let bl = cell.id.split(' ');
        if (Object.keys(t).includes(bl[0])) {
            if (Object.keys(t[bl[0]]).includes(bl[1])) {
                if (t[bl[0]][bl[1]].required) {
                    if ('input, output'.includes(cell.block_name) && (!nameField.value || !descField.value)) {
                        alert('Fields are required');
                        return false;
                    }
                }
            }
        }
        graph.cellLabelChanged(cell, newValue);
        wnd.destroy();
    };

    mxForm.prototype.addButtons = function (okFunct, cancelFunct) {
        var tr = document.createElement('tr');
        var td = document.createElement('td');
        tr.appendChild(td);
        td = document.createElement('td');

        // Adds the cancel button
        button = document.createElement('button');
        button.className = 'can';
        mxUtils.write(button, mxResources.get('cancel') || 'Cancel');
        td.appendChild(button);

        mxEvent.addListener(button, 'click', function () {
            cancelFunct();
        });

        // Adds the ok button
        var button = document.createElement('button');
        button.className = 'ok';
        mxUtils.write(button, mxResources.get('ok') || 'OK');
        td.appendChild(button);
        td.className = 'but';

        mxEvent.addListener(button, 'click', function () {
            okFunct();
        });

        tr.appendChild(td);
        this.body.appendChild(tr);
    };
    form.addButtons(okFunction, cancelFunction);

    wnd = showModalWindow('EDIT', form.table, 300, window_height);
    $(document).on('keydown', function(e) {
        if (e.which == 27) {
            cancelFunction();
            e.preventDefault();
        }
        if (e.which == 13) {
            okFunction();
            e.preventDefault();
        }
    });
}

function showModalWindow(title, content, width, height) {
    var background = document.createElement('div');
    background.style.position = 'absolute';
    background.style.left = '0px';
    background.style.top = '0px';
    background.style.right = '0px';
    background.style.bottom = '0px';
    background.style.background = '#999999';
    background.style.zIndex = 111;
    mxUtils.setOpacity(background, 50);
    document.body.appendChild(background);
    var x = Math.max(0, document.body.scrollWidth / 2 - width / 2);
    var y = Math.max(10, (document.body.scrollHeight ||
        document.documentElement.scrollHeight) / 2 - height * 2 / 3);
    var wnd = new mxWindow(title, content, x, y, width, height, false, true);
    // Fades the background out after after the window has been closed
    wnd.addListener(mxEvent.DESTROY, function (evt) {
        mxEffects.fadeOut(background, 50, true,
            10, 30, true);
    });
    wnd.div.style.zIndex += 111;
    wnd.setVisible(true);
    return wnd;
}

function edit_icon(style, hover) {
    let stroke = style;
    let stroke_width = !hover ? '3px' : '6px';
    let col = !hover ? '#ccc' : '#666';
    var i = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 88 88">\n' +
        '    <defs>\n' +
        '        <style>\n' +
        '            .cls-1{fill:#fff;stroke:' + stroke + ';stroke-miterlimit:10;stroke-width:' + stroke_width + ';}.cls-2{fill:' + col + ';}.cls-3{fill:none;}\n' +
        '        </style>\n' +
        '    </defs>\n' +
        '    <title>new_pen</title>\n' +
        '    <g id="Layer_2" data-name="Layer 2">\n' +
        '        <g id="Layer_1-2" data-name="Layer 1">\n' +
        '            <rect class="cls-1" x="8.48" y="8.48" width="71.04" height="71.04"\n' +
        '                  rx="35.52" ry="35.52"/>\n' +
        '            <path class="cls-2"\n' +
        '                  d="M58.25,28.38a5.26,5.26,0,0,0-7.45,0L29.92,49.26a1.26,1.26,0,0,0-.3.51l-2.74,9.91a1.17,1.17,0,0,0,1.44,1.44l9.91-2.74a1.36,1.36,0,0,0,.52-.3L59.63,37.2a5.28,5.28,0,0,0,0-7.45ZM32.47,50,49.56,32.93l5.51,5.51L38,55.53Zm-1.1,2.21,4.41,4.4-6.1,1.69ZM58,35.54l-1.24,1.24-5.51-5.51L52.46,30a2.93,2.93,0,0,1,4.14,0L58,31.4A2.93,2.93,0,0,1,58,35.54Z"/>\n' +
        '            <rect class="cls-3" width="88" height="88"/>\n' +
        '        </g>\n' +
        '    </g>\n' +
        '</svg>';
    return i;
}

function del_icon(style, hover) {
    let stroke = style;
    let stroke_width = !hover ? '3px' : '6px';
    let col = !hover ? '#ccc' : '#666';
    var i = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 75.04 75.04">\n' +
        '    <defs>\n' +
        '        <style>\n' +
        '            .cls-1{fill:#fff;}.cls-2{fill:' + stroke + ';}.cls-3{fill:' + col + ';stroke:' + col + ';stroke-miterlimit:10;}\n' +
        '        </style>\n' +
        '    </defs>\n' +
        '    <title>Delete__</title>\n' +
        '    <g id="Layer_2" data-name="Layer 2">\n' +
        '        <g id="Layer_1-2" data-name="Layer 1">\n' +
        '            <rect class="cls-1" x="2" y="2" width="71.04" height="71.04"\n' +
        '                  rx="35.52" ry="35.52"/>\n' +
        '            <path class="cls-2"\n' +
        '                  d="M37.52,75A37.52,37.52,0,1,1,75,37.52,37.56,37.56,0,0,1,37.52,75Zm0-71A33.52,33.52,0,1,0,71,37.52,33.56,33.56,0,0,0,37.52,4Z"/>\n' +
        '            <path class="cls-3"\n' +
        '                  d="M51.91,25.39a1.06,1.06,0,0,1,.32.78,1.2,1.2,0,0,1-.32.81,1,1,0,0,1-.81.35H49.54L46.93,53.5A2.19,2.19,0,0,1,46.18,55a2.32,2.32,0,0,1-1.59.61H30.44A2.26,2.26,0,0,1,28.85,55a2.39,2.39,0,0,1-.74-1.56l-2.62-26.1H23.94a1.05,1.05,0,0,1-.82-.35,1.19,1.19,0,0,1-.31-.81,1.06,1.06,0,0,1,.31-.78,1.14,1.14,0,0,1,.82-.32h7.92V22a2.41,2.41,0,0,1,.78-1.81,2.59,2.59,0,0,1,1.84-.74h6.08a2.59,2.59,0,0,1,1.84.74A2.41,2.41,0,0,1,43.18,22v3.11H51.1A1.1,1.1,0,0,1,51.91,25.39Zm-4.63,1.94H27.76l2.61,25.89c0,.1,0,.14.07.14H44.59s.07,0,.07-.07ZM34.12,25.07h6.79V22c0-.24-.11-.36-.35-.36H34.48a.32.32,0,0,0-.36.36Z"/>\n' +
        '        </g>\n' +
        '    </g>\n' +
        '</svg>';
    return i
}
