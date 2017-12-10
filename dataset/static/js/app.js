define(['jquery', 'static/js/api'], function ($, api) {
    if ($('.index-page').length > 0) {
        $('#btn-submit').hide();
        var dbpath = '';

        html_options = ['<option value="">-- Select DB --</option>']

        var fn = function (dbs) {
            if (!dbs) {
                alert('Empyt DB paths!');
                return;
            }

            $.each(dbs, function (i, e) {
                if (e) {
                    html_options.push('<option value=' + i + '>' + e + '</option>');
                }
            });

            $('#dbpath').html(html_options.join('')).change(function () {
                var sel = $(this);
                var op = sel.find('option:selected');
                dbpath = dbs[op.val()];

                if (op) {
                    $('#btn-submit').show();
                };
            });
        };

        $.ajax('/static/db.txt', {
            dataType: 'text',
            cache: true
        })
        .done(function (rep) {
            fn(rep.split('\n'));
        })
        .fail(function () {
            alert("Error during loading of files with DB paths!");
        });

        $('#btn-submit').click(function () {
            var url = 'gen_info'
            var form = $('<form action="' + url + '" method="post">' +
                '<input type="text" name="dbpath" value="' + dbpath + '" />' +
                '</form>');
            $('body').append(form);
            form.submit()
        });
    }
    else if ($('.gen-info-page').length > 0) {
        function DoPost() {
            var path = this.text;
            var url = 'repo_info';
            var form = $('<form action="' + url + '" method="post">' +
                '<input type="text" name="rpath" value="' + path + '" />' +
                '</form>');
            $('body').append(form);
            form.submit()
        };

        $('.repo-ref').each(function (i, obj) {
            $(obj).on('click', DoPost);
        });
    }
});
