/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.data.MyAjaxProxy', {
    extend: 'Ext.data.proxy.Ajax',
    alias: 'proxy.my-ajax',

    requires: [
        'Lively.data.MyJsonReader'
    ],

    reader: {
        type: 'my-json'
    }
});