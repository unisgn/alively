/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.data.MyJsonReader', {
    extend: 'Ext.data.reader.Json',

    alias: 'reader.my-json',
    
    messageProperty: 'msg',
    rootProperty: 'data'
});