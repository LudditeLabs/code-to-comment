define(['jquery'], function($) {
    var _opt = {
            sessHeader: 'X-SID',
            fakeHeader: 'X-Fake',
            baseURL: '/api',
            fake: false,
            logData: false,
            logSuccess: false,
            logFailure: true,
            sessIdCookie: 'sid',
            sessIdCookieExpDays: 0, // if > 0 then put session id in cookie
            logPrefix: 'api: ',
            $files: null    // this property can't be set via configure()
        },
        _sessId;

    function _getOpts(opt) {
        return $.extend({}, _opt, opt);
    };

    return {
        send: function(name, params, opt) {

            var def = $.Deferred(),
                ops = _getOpts(opt),
                url = ops.baseURL,
                args_tst = {
                    'q': 'i = i + 1;',
                },
                args = {};

            ff = ops.$files;

            if (ff && ff.length) {
                var data = new FormData();

                $.each(ff, function(i, f) {
                    $.each(f.files, function(j, file) {
                        var key = $(f).attr('name');
                        if (j) {
                            key += '-' + j;
                        }
                        data.append(key, file);
                    });
                });
                data.append('json', JSON.stringify(params));
                args.data = data;
            } else {
                args.data = JSON.stringify(params);
            }

            $.post( 
                url,
                args_tst,
                function(data, status){
                    alert("Data: " + data + "\nStatus: " + status);
                    def.resolve(status)
                }
            );


            /*
            wrap[sid] = {
                type: 'request',
                name: name,
                version: 1,
                params: params || {}
            };

            var args = {
                url: ops.baseURL + name,
                method: 'POST',
                headers: hh,
                cache: false
                dataType: 'json',
                contentType: false,
                processData: false
            },
            ff = ops.$files;

            if (ff && ff.length) {
                var data = new FormData();

                $.each(ff, function(i, f) {
                    $.each(f.files, function(j, file) {
                        var key = $(f).attr('name');
                        if (j) {
                            key += '-' + j;
                        }
                        data.append(key, file);
                    });
                });
                data.append('json', JSON.stringify(wrap));
                args.data = data;
            } else {
                args.data = JSON.stringify(wrap);
            }

            $.ajax.post(
                args.url,
                args.data,
                function(data, textStatus, xhr) {
                }
            )

            $.ajax(args)
            .done(function(data, textStatus, xhr) {
                if (ops.logSuccess || ops.logFailure) {
                    var rep = {};
                    rep[name] = data.rc ? {rc: data.rc, message: data.message} : data.data;
                }

                if (data.rc) {
                    def.reject({
                        xhr: xhr,
                        message: 'API ' + data.rc + ' ' + data.message,
                        data: data
                    });
                    if (ops.logFailure) {
                        _log('call failed: ' + (ops.logData ? JSON.stringify(rep) : name));
                    }
                } else {
                    if (ops.logSuccess) {
                        _log('call succeeded: ' + (ops.logData ? JSON.stringify(rep) : name));
                    }
                    def.resolve(data);
                }
            })
            .fail(function(xhr, textStatus, errorThrown) {
                def.reject({
                    xhr: xhr,
                    message: 'HTTP ' + xhr.status + ' ' + textStatus + ' (' + errorThrown + ')'
                });
                if (ops.logFailure) {
                    _log('call failed: ' + name + ', (' + xhr.status + ' ' + errorThrown + ')');
                }
            });
            */

            return def.promise();
        }
    };
});
