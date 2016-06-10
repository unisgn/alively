/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.Role', {
    extend: 'Lively.model.PrimeEntity',

    fields: [
        { name: 'code',     type: 'string' },
        { name: 'name',      type: 'string' },
        { name: 'memo',    type: 'string' },
        { name: 'flag',   type: 'boolean' }
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