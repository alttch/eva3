SCHEMA_DEVICE = {
    'additionalProperties': False,
    'properties': {
        'additionalProperties': False,
        'controller': {
            'patternProperties': {
                '^.*$': {
                    'additionalProperties': False,
                    'properties': {
                        'after-deploy': {
                            'items': {
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }, {
                                    'required': ['install-pkg']
                                }],
                                'properties': {
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'minimum': 0,
                                        'type': 'number'
                                    },
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'enum': ['system', 'sleep'],
                                        'type': 'string'
                                    },
                                    'install-pkg': {
                                        'type': 'string'
                                    }
                                },
                                'type': 'object'
                            },
                            'type': 'array'
                        },
                        'after-undeploy': {
                            'items': {
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }, {
                                    'required': ['install-pkg']
                                }],
                                'properties': {
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'minimum': 0,
                                        'type': 'number'
                                    },
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'enum': ['system', 'sleep'],
                                        'type': 'string'
                                    },
                                    'install-pkg': {
                                        'type': 'string'
                                    }
                                },
                                'type': 'object'
                            },
                            'type': 'array'
                        },
                        'before-deploy': {
                            'items': {
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }, {
                                    'required': ['install-pkg']
                                }],
                                'properties': {
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'minimum': 0,
                                        'type': 'number'
                                    },
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'enum': ['system', 'sleep'],
                                        'type': 'string'
                                    },
                                    'install-pkg': {
                                        'type': 'string'
                                    }
                                },
                                'type': 'object'
                            },
                            'type': 'array'
                        },
                        'before-undeploy': {
                            'items': {
                                'oneOf': [{
                                    'required': ['api']
                                }, {
                                    'required': ['cm-api']
                                }, {
                                    'required': ['function']
                                }, {
                                    'required': ['install-pkg']
                                }],
                                'properties': {
                                    '_pass': {
                                        'type': 'boolean'
                                    },
                                    '_timeout': {
                                        'minimum': 0,
                                        'type': 'number'
                                    },
                                    'api': {
                                        'type': 'string'
                                    },
                                    'cm-api': {
                                        'type': 'string'
                                    },
                                    'function': {
                                        'enum': ['system', 'sleep'],
                                        'type': 'string'
                                    },
                                    'install-pkg': {
                                        'type': 'string'
                                    }
                                },
                                'type': 'object'
                            },
                            'type': 'array'
                        },
                        'cvar': {
                            'patternProperties': {
                                '^.*$': {
                                    'type': ['string', 'number', 'boolean']
                                }
                            },
                            'type': 'object'
                        },
                        'driver': {
                            'patternProperties': {
                                '^.*$': {
                                    'additionalProperties': False,
                                    'properties': {
                                        'config': {
                                            'type': 'object'
                                        },
                                        'module': {
                                            'type': 'string'
                                        }
                                    },
                                    'required': ['module'],
                                    'type': 'object'
                                }
                            },
                            'type': 'object'
                        },
                        'key': {
                            'patternProperties': {
                                '^.*$': {
                                    'additionalProperties': False,
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
                                    'type': 'object'
                                }
                            },
                            'type': 'object'
                        },
                        'phi': {
                            'patternProperties': {
                                '^.*$': {
                                    'additionalProperties': False,
                                    'properties': {
                                        'config': {
                                            'type': 'object'
                                        },
                                        'module': {
                                            'type': 'string'
                                        },
                                        'src': {
                                            'type': 'string'
                                        }
                                    },
                                    'required': ['module'],
                                    'type': 'object'
                                }
                            },
                            'type': 'object'
                        },
                        'plugins': {
                            'patternProperties': {
                                '^.*$': {
                                    'additionalProperties': False,
                                    'properties': {
                                        'config': {
                                            'type': ['object']
                                        },
                                        'src': {
                                            'type': 'string'
                                        }
                                    },
                                    'required': ['src'],
                                    'type': 'object'
                                }
                            },
                            'type': 'object'
                        },
                        'upload-runtime': {
                            'items': {
                                'type': 'string'
                            },
                            'type': 'array'
                        },
                        'user': {
                            'patternProperties': {
                                '^.*$': {
                                    'additionalProperties': False,
                                    'properties': {
                                        'key': {
                                            'type': ['string', 'array']
                                        },
                                        'password': {
                                            'type': 'string'
                                        }
                                    },
                                    'required': ['password', 'key'],
                                    'type': 'object'
                                }
                            },
                            'type': 'object'
                        }
                    },
                    'type': 'object'
                }
            },
            'type': 'object'
        },
        'sensor': {
            'patternProperties': {
                '^.*$': {
                    'additionalProperties': False,
                    'patternProperties': {
                        '^__.*$': {}
                    },
                    'properties': {
                        'controller': {
                            'type': 'string'
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
                    'patternProperties': {
                        '^__.*$': {}
                    },
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
                        'controller': {
                            'type': 'string'
                        },
                        'description': {
                            'type': 'string'
                        },
                        'driver': {
                            'additionalProperties': False,
                            'properties': {
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
