SCHEMA_DEVICE = {
    'additionalProperties': False,
    'properties': {
        'additionalProperties': False,
        'sensor': {
            'patternProperties': {
                '^.*$': {
                    'additionalProperties': False,
                    'properties': {
                        'description': {
                            'type': 'string'
                        },
                        'driver': {
                            'properties': {
                                'additionalProperties': False,
                                'config': {
                                    'type': 'object'
                                },
                                'id': {
                                    'type': 'string'
                                }
                            },
                            'type': 'object'
                        },
                        'expires': {
                            'minimum': 0,
                            'type': 'number'
                        },
                        'location': {},
                        'maintenance_duration': {
                            'minimum': 0,
                            'type': 'number'
                        },
                        'modbus_value': {
                            'type': ['string', 'null']
                        },
                        'mqtt_update': {
                            'type': ['string', 'null']
                        },
                        'notify_events': {
                            'enum': [0, 1, 2],
                            'type': 'integer'
                        },
                        'snmp_trap': {},
                        'status': {
                            'type': 'integer'
                        },
                        'update_driver_config': {
                            'type': ['object', 'null']
                        },
                        'update_exec': {
                            'type': ['string', 'null']
                        },
                        'update_interval': {
                            'minimum': 0,
                            'type': 'number'
                        },
                        'update_timeout': {
                            'type': ['number', 'null']
                        },
                        'value': {
                            'type': ['number', 'string', 'boolean']
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
                    'type': 'object'
                }
            }
        },
        'unit': {
            'patternProperties': {
                '^.*$': {
                    'additionalProperties': False,
                    'properties': {
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
                            'enum': [0, 1, 2],
                            'type': 'integer'
                        },
                        'action_timeout': {
                            'type': ['number', 'null']
                        },
                        'auto_off': {
                            'minimum': 0,
                            'type': 'number'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'driver': {
                            'properties': {
                                'additionalProperties': False,
                                'config': {
                                    'type': 'object'
                                },
                                'id': {
                                    'type': 'string'
                                }
                            },
                            'type': 'object'
                        },
                        'expires': {
                            'minimum': 0,
                            'type': 'number'
                        },
                        'location': {},
                        'maintenance_duration': {
                            'minimum': 0,
                            'type': 'number'
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
                            'enum': [0, 1, 2],
                            'type': 'integer'
                        },
                        'snmp_trap': {},
                        'status': {
                            'type': 'integer'
                        },
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
                            'minimum': 0,
                            'type': 'number'
                        },
                        'update_state_after_action': {
                            'type': 'boolean'
                        },
                        'update_timeout': {
                            'type': ['number', 'null']
                        },
                        'value': {
                            'type': ['number', 'string', 'boolean']
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
                    'type': 'object'
                }
            }
        }
    },
    'type': 'object'
}
