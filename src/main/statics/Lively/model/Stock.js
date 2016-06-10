/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.Stock', {
    extend: 'Lively.model.PrimeEntity',

    fields: [
        { name: 'warehouse_fk',     type: 'string' },
        { name: 'part_fk',     type: 'string' },
        { name: 'lot',    type: 'float'},
        { name: 'uom_fk',    type: 'string'}
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