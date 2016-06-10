/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.PrimeEntity', {
    extend: 'Ext.data.Model',

    requires: [
        'Ext.data.identifier.Uuid',
        'Lively.data.MyRestProxy'
    ],
    
    identifier:'uuid',
    schema: {
        namespace: 'Lively.model',
        proxy:{
            type:'my-rest',
            url:'/api/{entityName}'
        }
    }
});