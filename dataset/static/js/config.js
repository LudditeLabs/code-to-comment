require.config({
    shim : {
        "bootstrap" : { "deps" :['jquery'] }
    },
    baseUrl: '',
    paths: {
        'jquery': 'static/js/jquery-3.2.1.min',
        'popper': 'https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.12.3/umd/popper.min',
        'bootstrap' : 'https://maxcdn.bootstrapcdn.com/bootstrap/4.0.0-beta.2/js/bootstrap.min'
    },
});

require(['static/js/app']);