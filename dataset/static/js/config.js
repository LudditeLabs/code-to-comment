require.config({
    shim : {
        "bootstrap" : { "deps" :['jquery'] }
    },
    baseUrl: '',
    paths: {
        'jquery': 'static/js/jquery-3.2.1.min',
        'bootstrap' : '//netdna.bootstrapcdn.com/bootstrap/3.1.1/js/bootstrap.min'
    },
});

require(['static/js/app']);