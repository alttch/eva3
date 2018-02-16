<?php
/**
 * apiclient.php
 *
 * EVA API Client
 *
 * @author      Altertech Group, http://www.altertech.com/
 * @copyright   Copyright (C) 2012-2017 Altertech Group
 * @license     See http://www.eva-ics.com/
 * @version     3.0.0
 */

$eva_version = '3.0.0';

$eva_result_ok = 0;
$eva_result_not_found = 1;
$eva_result_forbidden = 2;
$eva_result_api_error = 3;
$eva_result_unknown_error = 4;
$eva_result_not_ready = 5;
$eva_result_func_unknown = 6;
$eva_result_server_error = 7;
$eva_result_server_timeout = 8;
$eva_result_bad_data = 9;
$eva_result_func_failed = 10;

$_eva_sysapi_uri = '/sys-api/';

$_eva_sysapi_func = array(
        'cmd',
        'lock',
        'unlock',
        'log_rotate',
        'log_debug',
        'log_info',
        'log_warning',
        'log_error',
        'log_critical',
        'log_get',
        'notifiers',
        'save',
        'get_cvar',
        'set_cvar',
        'set_debug',
        'file_unlink',
        'file_get',
        'file_put',
        'file_set_exec',
        'create_user',
        'set_user_password',
        'set_user_key',
        'destroy_user',
        'list_keys',
        'list_users',
        'dump'
        );

$_eva_sysapi_func_cr = array(
        'lock',
        'unlock',
        'log_rotate',
        'log_debug',
        'log_info',
        'log_warning',
        'log_error',
        'log_critical',
        'save',
        'set_debug',
        'set_cvar',
        'file_unlink',
        'file_put',
        'file_set_exec',
        'create_user',
        'set_user_password',
        'set_user_key',
        'destroy_user',
        'dump',
        );

$_eva_sysapi_func_ce = array(
        'cmd'
        );

$_eva_sysapi_func_post = array(
        'create_user',
        'set_user_password',
        'file_put'
        );

$_eva_api_func = array(
        'uc' =>
            array(
                'uri' => '/uc-api/',
                'func' => array(
                    'test',
                    'state',
                    'groups',
                    'update',
                    'action',
                    'result',
                    'terminate',
                    'q_clean',
                    'kill',
                    'disable_actions',
                    'enable_actions',
                    'get_config',
                    'save_config',
                    'list',
                    'list_props',
                    'set_prop',
                    'create_unit',
                    'create_sensor',
                    'create_mu',
                    'clone',
                    'destroy',
                    'login',
                    'logout'
                    ),
                'cr' => array(
                    'update',
                    'terminate',
                    'kill',
                    'q_clean',
                    'disable_actions',
                    'enable_actions',
                    'save_config',
                    'set_prop',
                    'create_unit',
                    'create_sensor',
                    'create_mu',
                    'clone',
                    'destroy',
                    'login',
                    'logout'
                    ),
                'ce' => array(
                    'action'
                    ),
                'post' => array(
                    )
                ),
        'lm' =>
            array(
                'uri' => '/lm-api/',
                'func' =>
                    array(
                    'test',
                    'state',
                    'groups',
                    'groups_macro',
                    'set',
                    'reset',
                    'run',
                    'result',
                    'get_config',
                    'save_config',
                    'list',
                    'list_remote',
                    'list_controllers',
                    'list_macros',
                    'create_macro',
                    'destroy_macro',
                    'append_controller',
                    'remove_controller',
                    'list_props',
                    'list_macro_props',
                    'list_controller_props',
                    'set_prop',
                    'set_macro_prop',
                    'set_controller_prop',
                    'reload_controller',
                    'create_lvar',
                    'destroy_lvar',
                    'list_rules',
                    'list_rule_props',
                    'set_rule_prop',
                    'create_rule',
                    'destroy_rule',
                    'login',
                    'logout'
                    ),
                'cr' => array(
                    'set',
                    'reset',
                    'save_config',
                    'set_prop',
                    'set_macro_prop',
                    'set_controller_prop',
                    'create_macro',
                    'destroy_macro',
                    'append_controller',
                    'remove_controller',
                    'reload_controller',
                    'create_lvar',
                    'destroy_lvar',
                    'set_rule_prop',
                    'create_rule',
                    'destroy_rule',
                    'login',
                    'logout'
                    ),
                'ce' => array(
                    'run'
                    ),
                'post' => array (
                    )
            ),
        'sfa' =>
            array(
                'uri' => '/sfa-api/',
                'func' =>
                    array(
                    'test',
                    'state',
                    'state_all',
                    'groups',
                    'action',
                    'terminate',
                    'kill',
                    'q_clean',
                    'disable_actions',
                    'enable_actions',
                    'set',
                    'reset',
                    'list_macros',
                    'groups_macro',
                    'run',
                    'list_controllers',
                    'append_controller',
                    'remove_controller',
                    'list_controller_props',
                    'set_controller_prop',
                    'reload_controller',
                    'list_remote',
                    'list_rule_props',
                    'set_rule_prop',
                    'login',
                    'logout'
                    ),
                'cr' => array(
                    'terminate',
                    'kill',
                    'q_clean',
                    'disable_actions',
                    'enable_actions',
                    'set',
                    'reset',
                    'set_controller_prop',
                    'append_controller',
                    'remove_controller',
                    'reload_controller',
                    'set_rule_prop',
                    'login',
                    'logout'
                    ),
                'ce' => array(
                    'action',
                    'run'
                    ),
                'post' => array (
                    )
            )
        );


class EVA_APIClient {

    function __construct() {
        $this->_key = '';
        $this->_uri = '';
        $this->_timeout = 5;
        $this->_product_code = 'sfa';
        $this->_ssl_verify = true;
    }


    function set_key($key) { $this->_key = $key; }

    function set_uri($uri) { $this->_uri = $uri; }

    function set_timeout($timeout) { $this->_timeout = $timeout; }

    function set_product($product) { $this->_product_code = $product; }

    function ssl_verify($v) { $this->_ssl_verify = $v; }


    function call($func, $params = null, $timeout = null) {
        if(!is_callable('curl_init')) {
            trigger_error('Error: curl not enabled', E_USER_ERROR);
            return array($GLOBALS['eva_result_not_ready'], array());
            }
        if(!is_callable('json_decode')) {
            trigger_error('Error: json not enabled', E_USER_ERROR);
            return array($GLOBALS['eva_result_not_ready'], array());
            }
        if (!$this->_uri)
                return array($GLOBALS['eva_result_not_ready'], array());
        $t = $timeout ? $timeout : $this->_timeout;
        $api_uri = null;
        $check_result = false;
        $check_exitcode = false;
        $post = false;
        if ($this->_product_code &&
            array_key_exists(
                $this->_product_code, $GLOBALS['_eva_api_func']) &&
            in_array($func,
                    $GLOBALS['_eva_api_func'][$this->_product_code]['func'])) {
                $api_uri =
                        $GLOBALS['_eva_api_func'][$this->_product_code]['uri'];
                if (in_array($func,
                    $GLOBALS['_eva_api_func'][$this->_product_code]['cr']))
                        $check_result = true;
                if (in_array($func,
                    $GLOBALS['_eva_api_func'][$this->_product_code]['ce']))
                        $check_exitcode = true;
                if (in_array($func,
                    $GLOBALS['_eva_api_func'][$this->_product_code]['post']))
                        $post = true;
        }
        elseif (in_array($func, $GLOBALS['_eva_sysapi_func'])) {
            $api_uri = $GLOBALS['_eva_sysapi_uri'];
            if (in_array($func, $GLOBALS['_eva_sysapi_func_cr']))
                $check_result = true;
            if (in_array($func, $GLOBALS['_eva_sysapi_func_ce']))
                $check_exitcode = true;
            if (in_array($func, $GLOBALS['_eva_sysapi_func_post']))
                $post = true;
        }
        if (!$api_uri)
            return array($GLOBALS['eva_result_func_unknown'], array());
        if ($params) $p = $params; else $p = array();
        if (!array_key_exists('k', $p)) $p['k'] = $this->_key;
        $ch = curl_init();
        $ssl_verify = $this->_ssl_verify ? 2 : 0;
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, $ssl_verify);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, $ssl_verify);
        $q = '';
        foreach ($p as $k => $v) {
            if ($q) $q .= '&';
            $q .= $k.'='.urlencode($v);
        }
        if ($post) {
            curl_setopt($ch, CURLOPT_URL, $this->_uri.$api_uri.$func);
            curl_setopt($ch, CURLOPT_POST, 1);
            curl_setopt($ch, CURLOPT_POSTFIELDS, $q);
        } else {
            curl_setopt($ch, CURLOPT_URL,
                $this->_uri.$api_uri.'/'.$func.'?'.$q);
        }
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_TIMEOUT, $t);
        $response = curl_exec($ch);
        $c = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        $e = curl_errno($ch);
        if ($e == 28)
            return array($GLOBALS['eva_result_server_timeout'], array());
        if ($e > 0) return array($GLOBALS['eva_result_server_error'], array());
        curl_close($ch);
        if ($c != 200) {
            if ($c == 403)
                return array($GLOBALS['eva_result_forbidden'], array());
            if ($c == 404)
                return array($GLOBALS['eva_result_not_found'], array());
            if ($c == 500)
                return array($GLOBALS['eva_result_api_error'], array());
            return array($GLOBALS['eva_result_unknown_error'], array());
            }
        $result = json_decode($response, true);
        if (!$result) return array($GLOBALS['eva_result_bad_data'], array());
        if (
            ($check_result &&
                (!array_key_exists('result', $result) ||
                    $result['result'] != 'OK')) ||
                ($check_exitcode && array_key_exists('exitcode', $result) &&
                    $result['exitcode'])
            ) return array($GLOBALS['eva_result_func_failed'], $result);
        return array($GLOBALS['eva_result_ok'], $result);
    }
}



class EVA_APIClientLocal extends EVA_APIClient {

    function __construct($product, $dir_eva) {
        parent::__construct();
        if ($dir_eva) {
            $etc = $dir_eva.'/etc';
        } else {
            $etc = realpath(dirname(__FILE__)).'/../../etc';
        }
        $no_api_err = 'Error: API not found in server config';
        $this->_key = '';
        $this->_product_code = $product;
        $ini = parse_ini_file($etc.'/'.$product.'_apikeys.ini', true);
        if (!$ini) {
            trigger_error($no_api_err, E_USER_ERROR);
            return;
        }
        foreach ($ini as $v) {
            if (array_key_exists('master', $v)
                && $v['master'] == '1'
                && array_key_exists('key', $v)) {
                    $this->_key = $v['key'];
                    break;
            }
        }
        $ini = parse_ini_file($etc.'/'.$product.'.ini', true);
        if (!array_key_exists('webapi', $ini)) {
            trigger_error($no_api_err, E_USER_ERROR);
            return;
        }
        $ini = $ini['webapi'];
        if (array_key_exists('listen', $ini)) {
            $u = $ini['listen'];
            $pfx = 'http://';
            $default_port = 80;
        } elseif (array_key_exists('ssl_listen', $ini)) {
            $u = $ini['ssl_listen'];
            $pfx = 'https://';
            $default_port = 443;
        } else {
            trigger_error($no_api_err, E_USER_ERROR);
            return;
        }
        if (strpos($u, ':')) {
            list($host, $port) = explode(':', $u);
        } else {
            $host = $u;
            $port = $default_port;
        }
        if ($host == '0.0.0.0') $host = '127.0.0.1';
        $this->_uri = $pfx.$host.':'.$port;
    }

}
?>
