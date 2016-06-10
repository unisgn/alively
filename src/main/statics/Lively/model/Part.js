/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.Part', {
    extend: 'Lively.model.BusinessEntity',

    fields: [

        { name: 'is_bom',     type: 'boolean' },
        { name: 'parent_fk',      type: 'string' },
        { name: 'category_fk',    type: 'string' },
        { name: 'uom_fk',   type: 'string' },
        { name: 'cost_avg',   type: 'float' },
        { name: 'cost_std',   type: 'float' },
        { name: 'on_hand', type: 'float'},
        { name: 'on_order', type: 'float'},
        { name: 'on_demand',    type: 'float'}
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