/**
 * Created by yinlan on 6/10/16.
 */
Ext.define('Lively.model.User', {
    extend: 'Lively.model.AuditEntity',

    fields: [
        {name: 'name', type: 'string'},
        {name: 'emp_fk', type: 'string'},
        {name: 'memo', type: 'string'},
        {name: 'expire_date', type: 'date', dateFormat: 'U'},
        {name: 'login_ip', type: 'string', persist: false},
        {name: 'login_mac', type: 'string', persist: false},
        {name: 'login_time', type: 'string', persist: false},
        {name: 'logout_time', type: 'string', persist: false}
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