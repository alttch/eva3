<?php
include "eva-apiclient.php";

$api = new EVA_APIClientLocal('uc', null);

$api->ssl_verify(false);

// call EVA API function
echo "Successful call:\n";
list($code, $result) = $api->call('test');
echo 'CODE: '.$code."\n";
print_r($result);

// call EVA API function with params
echo "Non-existing item:\n";
list($code, $result) = $api->call('state', array(
    'i' => 'this_item_doesnt_exist'));
echo 'CODE: '.$code."\n";
print_r($result);

// failed call
echo "Failed call:\n";
list($code, $result) = $api->call('cmd', array(
    'c' => 'test',
    'a' => '1 2 3',
    'w' => 10
    ));
echo 'CODE: '.$code."\n";
print_r($result);

// timeout
echo "Timeout:\n";
$api->set_timeout(2);
list($code, $result) = $api->call('cmd', array(
    'c' => 'test', 'w' => 10));
echo 'CODE: '.$code."\n";
print_r($result);

// call unknown function
echo "Unknown function:\n";
list($code, $result) = $api->call('this_function_doesnt_exist');
echo 'CODE: '.$code."\n";
print_r($result);

// call with invalid key
echo "Invalid key:\n";
$api->set_key('THIS_KEY_IS_INVALID');
list($code, $result) = $api->call('test');
echo 'CODE: '.$code."\n";
print_r($result);

// server error
echo "Server error:\n";
$api->set_uri("http://127.0.0.1:99999");
list($code, $result) = $api->call('test');
echo 'CODE: '.$code."\n";
print_r($result);

// call with API not initialized
echo "API not initialized:\n";
$api->set_uri(null);
$api->set_product(null);
list($code, $result) = $api->call('test');
echo 'CODE: '.$code."\n";
print_r($result);
?>
