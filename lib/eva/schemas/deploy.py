SCHEMA_DEPLOY = {
    'additionalProperties': False,
    'type': 'object',
    'properties': {
        'additionalProperties': False,
        'controller': {
            'type': 'object',
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'cvar': {
                            'type': 'object',
                            'patternProperties': {
                                '^.*$': {
                                    'type': ['string', 'number', 'boolean']
                                }
                            }
                        },
                        'phi': {
                            'type': 'object',
                            'patternProperties': {
                                '^.*$': {
                                    'type': 'object',
                                    'properties': {
                                        'module': {
                                            'type': 'string'
                                        },
                                        'src': {
                                            'type': 'string'
                                        },
                                        'config': {
                                            'type': 'object'
                                        }
                                    },
                                    'required': ['module'],
                                    'additionalProperties': False
                                }
                            }
                        },
                        'driver': {
                            'type': 'object',
                            'patternProperties': {
                                '^.*$': {
                                    'type': 'object',
                                    'properties': {
                                        'module': {
                                            'type': 'string'
                                        },
                                        'config': {
                                            'type': 'object'
                                        }
                                    },
                                    'required': ['module'],
                                    'additionalProperties': False
                                }
                            }
                        },
                        'key': {
                            'type': 'object',
                            'patternProperties': {
                                '^.*$': {
                                    'type': 'object',
                                    'properties': {
                                        'allow': {
                                            'type': ['string', 'array']
                                        },
                                        'cdata': {
                                            'type': ['string', 'array']
                                        },
                                        'groups': {
                                            'type': ['string', 'array']
                                        },
                                        'groups_ro': {
                                            'type': ['string', 'array']
                                        },
                                        'hosts_allow': {
                                            'type': ['string', 'array']
                                        },
                                        'hosts_assign': {
                                            'type': ['string', 'array']
                                        },
                                        'items': {
                                            'type': ['string', 'array']
                                        },
                                        'key': {
                                            'type': 'string'
                                        },
                                        'pvt': {
                                            'type': ['string', 'array']
                                        },
                                        'rpvt': {
                                            'type': ['string', 'array']
                                        },
                                        'sysfunc': {
                                            'type': 'boolean'
                                        }
                                    },
                                    'additionalProperties': False
                                }
                            }
                        },
                        'user': {
                            'type': 'object',
                            'patternProperties': {
                                '^.*$': {
                                    'type': 'object',
                                    'properties': {
                                        'password': {
                                            'type': 'string'
                                        },
                                        'key': {
                                            'type': ['string', 'array']
                                        }
                                    },
                                    'required': ['password', 'key'],
                                    'additionalProperties': False
                                }
                            }
                        },
                        'upload-runtime': {
                            'type': 'array',
                            'items': {
                                'type': 'string'
                            }
                        },
                        'before-deploy': {
                            'type': 'array',
                            'items': {
                                'type':
                                    'object',
                                'properties': {
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'type': 'string',
                                        'enum': ['system', 'sleep']
                                    },
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'type': 'number',
                                        'minimum': 0
                                    }
                                },
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }]
                            }
                        },
                        'before-undeploy': {
                            'type': 'array',
                            'items': {
                                'type':
                                    'object',
                                'properties': {
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'type': 'string',
                                        'enum': ['system', 'sleep']
                                    },
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'type': 'number',
                                        'minimum': 0
                                    }
                                },
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }]
                            }
                        },
                        'after-deploy': {
                            'type': 'array',
                            'items': {
                                'type':
                                    'object',
                                'properties': {
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'type': 'string',
                                        'enum': ['system', 'sleep']
                                    },
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'type': 'number',
                                        'minimum': 0
                                    }
                                },
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }]
                            }
                        },
                        'after-undeploy': {
                            'type': 'array',
                            'items': {
                                'type':
                                    'object',
                                'properties': {
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'type': 'string',
                                        'enum': ['system', 'sleep']
                                    },
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'type': 'number',
                                        'minimum': 0
                                    }
                                },
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }]
                            }
                        }
                    }
                }
            }
        },
        'unit': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'status': {
                            'type': 'integer'
                        },
                        'value': {
                            'type': ['number', 'string', 'boolean']
                        },
                        'driver': {
                            'type': 'object',
                            'properties': {
                                'id': {
                                    'type': 'string'
                                },
                                'config': {
                                    'type': 'object'
                                },
                                'additionalProperties': False
                            }
                        },
                        'action_allow_termination': {
                            'type': 'boolean'
                        },
                        'action_always_exec': {
                            'type': 'boolean'
                        },
                        'action_driver_config': {
                            'type': ['object', 'null']
                        },
                        'action_enabled': {
                            'type': 'boolean'
                        },
                        'action_exec': {
                            'type': ['string', 'null']
                        },
                        'action_queue': {
                            'type': 'integer',
                            'enum': [0, 1, 2]
                        },
                        'action_timeout': {
                            'type': ['number', 'null']
                        },
                        'auto_off': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'description': {
                            'type': 'string'
                        },
                        'expires': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'location': {},
                        'maintenance_duration': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'modbus_status': {
                            'type': ['string', 'null']
                        },
                        'modbus_value': {
                            'type': ['string', 'null']
                        },
                        'mqtt_control': {
                            'type': ['string', 'null']
                        },
                        'mqtt_update': {
                            'type': ['string', 'null']
                        },
                        'notify_events': {
                            'type': 'integer',
                            'enum': [0, 1, 2]
                        },
                        'snmp_trap': {},
                        'status_labels': {
                            'type': ['string', 'object']
                        },
                        'term_kill_interval': {
                            'type': ['number', 'null']
                        },
                        'update_driver_config': {
                            'type': ['object', 'null']
                        },
                        'update_exec': {
                            'type': ['string', 'null']
                        },
                        'update_exec_after_action': {
                            'type': 'boolean'
                        },
                        'update_if_action': {
                            'type': 'boolean'
                        },
                        'update_interval': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'update_state_after_action': {
                            'type': 'boolean'
                        },
                        'update_timeout': {
                            'type': ['number', 'null']
                        },
                        'value_condition': {
                            'type': 'string'
                        },
                        'value_in_range_max': {
                            'type': ['number', 'null']
                        },
                        'value_in_range_max_eq': {
                            'type': ['boolean', 'null']
                        },
                        'value_in_range_min': {
                            'type': ['number', 'null']
                        },
                        'value_in_range_min_eq': {
                            'type': ['boolean', 'null']
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'sensor': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'status': {
                            'type': 'integer'
                        },
                        'value': {
                            'type': ['number', 'string', 'boolean']
                        },
                        'driver': {
                            'type': 'object',
                            'properties': {
                                'id': {
                                    'type': 'string'
                                },
                                'config': {
                                    'type': 'object'
                                },
                                'additionalProperties': False
                            }
                        },
                        'description': {
                            'type': 'string'
                        },
                        'expires': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'location': {},
                        'maintenance_duration': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'modbus_value': {
                            'type': ['string', 'null']
                        },
                        'mqtt_update': {
                            'type': ['string', 'null']
                        },
                        'notify_events': {
                            'type': 'integer',
                            'enum': [0, 1, 2]
                        },
                        'snmp_trap': {},
                        'update_driver_config': {
                            'type': ['object', 'null']
                        },
                        'update_exec': {
                            'type': ['string', 'null']
                        },
                        'update_interval': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'update_timeout': {
                            'type': ['number', 'null']
                        },
                        'value_condition': {
                            'type': 'string'
                        },
                        'value_in_range_max': {
                            'type': ['number', 'null']
                        },
                        'value_in_range_max_eq': {
                            'type': ['boolean', 'null']
                        },
                        'value_in_range_min': {
                            'type': ['number', 'null']
                        },
                        'value_in_range_min_eq': {
                            'type': ['boolean', 'null']
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'lvar': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'status': {
                            'type': 'integer'
                        },
                        'value': {
                            'type': ['number', 'string', 'boolean']
                        },
                        'description': {
                            'type': 'string'
                        },
                        'expires': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'logic': {
                            'type': 'string',
                            'enum': ['simple', 'normal']
                        },
                        'mqtt_update': {
                            'type': ['string', 'null']
                        },
                        'notify_events': {
                            'type': 'integer',
                            'enum': [0, 1, 2]
                        },
                        'update_exec': {
                            'type': ['string', 'null']
                        },
                        'update_interval': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'update_timeout': {
                            'type': ['number', 'null']
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'lmacro': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'action_enabled': {
                            'type': 'boolean'
                        },
                        'action_exec': {
                            'type': ['string', 'null']
                        },
                        'description': {
                            'type': 'string'
                        },
                        'pass_errors': {
                            'type': 'boolean'
                        },
                        'send_critical': {
                            'type': 'boolean'
                        },
                        'src': {
                            'type': 'string'
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'dmatrix-rule': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'break_after_exec': {
                            'type': 'boolean'
                        },
                        'chillout_time': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'condition': {
                            'type': 'string'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'enabled': {
                            'type': 'boolean'
                        },
                        'for_initial': {
                            'type': 'string',
                            'enum': ['skip', 'any', 'only']
                        },
                        'for_item_group': {
                            'type': ['string', 'null']
                        },
                        'for_item_id': {
                            'type': ['string', 'null']
                        },
                        'for_item_type': {
                            'type': ['string', 'null']
                        },
                        'for_oid': {
                            'type': ['string', 'null']
                        },
                        'oid': {
                            'type': ['string', 'null']
                        },
                        'for_prop': {
                            'type': 'string',
                            'enum': ['status', 'value']
                        },
                        'for_prop_bit': {
                            'type': ['number', 'null']
                        },
                        'in_range_max': {
                            'type': ['number', 'null']
                        },
                        'in_range_max_eq': {
                            'type': ['boolean', 'null']
                        },
                        'in_range_min': {
                            'type': ['number', 'null']
                        },
                        'in_range_min_eq': {
                            'type': ['boolean', 'null']
                        },
                        'macro': {
                            'type': ['string', 'null']
                        },
                        'macro_args': {
                            'type': ['string', 'array']
                        },
                        'macro_kwargs': {
                            'type': ['string', 'object']
                        },
                        'priority': {
                            'type': 'integer',
                            'minimum': 1
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'dmatrix_rule': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'break_after_exec': {
                            'type': 'boolean'
                        },
                        'chillout_time': {
                            'type': 'number',
                            'minimum': 0
                        },
                        'condition': {
                            'type': 'string'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'enabled': {
                            'type': 'boolean'
                        },
                        'for_initial': {
                            'type': 'string',
                            'enum': ['skip', 'any', 'only']
                        },
                        'for_item_group': {
                            'type': ['string', 'null']
                        },
                        'for_item_id': {
                            'type': ['string', 'null']
                        },
                        'for_item_type': {
                            'type': ['string', 'null']
                        },
                        'for_oid': {
                            'type': ['string', 'null']
                        },
                        'oid': {
                            'type': ['string', 'null']
                        },
                        'for_prop': {
                            'type': 'string',
                            'enum': ['status', 'value']
                        },
                        'for_prop_bit': {
                            'type': ['number', 'null']
                        },
                        'in_range_max': {
                            'type': ['number', 'null']
                        },
                        'in_range_max_eq': {
                            'type': ['boolean', 'null']
                        },
                        'in_range_min': {
                            'type': ['number', 'null']
                        },
                        'in_range_min_eq': {
                            'type': ['boolean', 'null']
                        },
                        'macro': {
                            'type': ['string', 'null']
                        },
                        'macro_args': {
                            'type': ['string', 'array']
                        },
                        'macro_kwargs': {
                            'type': ['string', 'object']
                        },
                        'priority': {
                            'type': 'integer',
                            'minimum': 1
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'job': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'controller': {
                            'type': 'string'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'enabled': {
                            'type': 'boolean'
                        },
                        'every': {
                            'type': ['string', 'null']
                        },
                        'macro': {
                            'type': ['string', 'null']
                        },
                        'macro_args': {
                            'type': ['string', 'array']
                        },
                        'macro_kwargs': {
                            'type': ['string', 'object']
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        },
        'lcycle': {
            'patternProperties': {
                '^.*$': {
                    'type': 'object',
                    'properties': {
                        'autostart': {
                            'type': 'boolean'
                        },
                        'controller': {
                            'type': 'string'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'ict': {
                            'type': 'number',
                            'exclusiveMinimum': 0
                        },
                        'interval': {
                            'type': 'number',
                            'exclusiveMinimum': 0
                        },
                        'macro': {
                            'type': ['string', 'null']
                        },
                        'macro_args': {
                            'type': ['string', 'array']
                        },
                        'macro_kwargs': {
                            'type': ['string', 'object']
                        },
                        'on_error': {
                            'type': ['string', 'null']
                        }
                    },
                    'additionalProperties': False,
                    'required': ['controller']
                }
            }
        }
    }
}
