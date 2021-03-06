/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.BusinessEntity', {
    extend: 'Lively.model.AuditEntity',

    fields: [
        {name: 'number', type: 'string'},
        {name: 'code', type: 'string'},
        {name: 'name', type: 'string'},
        {name: 'alias', type: 'string'},
        {name: 'memo', type: 'string'},
        {name: 'keyword', type: 'string'}
    ]

    /*
    Uncomment to add validation rules
    validators: {
        age: 'presence',
        name: { type: 'length', min: 2 },
        gender: { type: 'inclusion', list: ['Male', 'Female'] },
        username: [
            { type: 'exclusion', list: ['Admin', 'Operator'] },
            { type: 'format', matcher: /([a-z]+)[0-9]{2,3}/i }
        ]
    }
    */

    /*
    Uncomment to add a rest proxy that syncs data with the back end.
    proxy: {
        type: 'rest',
        url : '/users'
    }
    */
});