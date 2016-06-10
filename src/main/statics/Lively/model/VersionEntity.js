/**
 * Created by 0xFranCiS on Mar 23, 2015..
 */
Ext.define('Lively.model.VersionEntity', {
    extend: 'Finetrust.model.PrimeEntity',
    
    fields:[
        {name:'version', type:'int'},
        {name:'archived', type:'boolean', defaultValue:false, persist: false},
        {name:'active', type:'boolean', defaultValue: true, persist: false}
    ],
    
    versionProperty: 'version'
    
});