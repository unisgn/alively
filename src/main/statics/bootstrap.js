Ext.log('start ext;');

Ext.Loader.setConfig({
    enabled: true,
    paths: {
        'Beaux': 'Beaux',
        'Lively': 'Lively'
    }
});


// Ext.Loader.loadScript('beaux/boot/override/override.js');

Ext.Loader.loadScript('Beaux/Beaux.js');

// Ext.Loader.loadScript('finetrust/data/Dict.js');
// doesn't work on extjs5
/*Ext.getDoc().on({
 contextmenu: function(e) { e.stopEvent(); }
 });*/

Ext.require('Beaux.login.LoginMgr');
Ext.require('Beaux.desktop.Desktop');


Ext.onReady(function () {


    // disable browser oncontextmenu event
    Ext.getBody().on({
        contextmenu: e => {
            e.stopEvent();
        }
    });

    ((Ext) => {
        var _false_reg = /"success":false/;
        var _true_reg = /"success":true/;
        Ext.Ajax.on({
            requestexception: (conn, resp) => {
                console.log(resp);
            },
            requestcomplete: (conn, resp) => {
                let data = resp.responseText;
                // pre test with regular expression, for performance consideration
                if (_false_reg.test(data)) {
                    data = Ext.JSON.decode(data);
                    let ok = data['success'];
                    if (!ok) {
                        Beaux.notify(data['msg']);
                        console.warn('restful protocol failure detected');
                        console.warn(data['traceback']);
                    }

                    // if (!_true_reg.test(data)) {
                    //     //further test via json decode, here ignored
                    //
                    //
                    // }

                }
            }
        });
    })(Ext);


    // TODO: hack the {Ext.data.reader.Reader} to handle global {success:false} event

    Beaux.setDisplayManager(null);
    Beaux.setDesktopManager(Beaux.desktop.Desktop);
    Beaux.boot();

});
