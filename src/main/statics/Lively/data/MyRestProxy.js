/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.data.MyRestProxy', {
    extend: 'Ext.data.proxy.Rest',
    alias: 'proxy.my-rest',

    requires: [
        'Lively.data.MyJsonReader'
    ],

    reader: {
        type: 'my-json'
    }
});