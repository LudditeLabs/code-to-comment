define(['jquery', 'static/js/api'], function($, api) {
    var $reqName = $('#req-name'),
        $reqData = $('#req-data'),
        $repData = $('#rep-data'),
        $repSummary = $('#rep-summary'),
        fileName = null;

    $('input:file')
    .val('')
    .change(function() {
        fileName = $(this).val();
    });

    $('#btn-submit').click(function() {
        var reqName = $reqName.val();
        if (reqName == '') {
            alert('Invalid request name.');
            return $reqName.focus().select();
        }
        var data  = $reqData.val();
        if (data == '') {
            alert('Invalid request data.');
            return $reqData.focus().select();
        }
        try {
            var reqData = JSON.parse(data);
        } catch (e) {
            alert('Invalid JSON in endpoint data. ' + e.message);
            return $reqData.focus().select();
        }

        $repSummary.html('');
        $repData.text('');

        var promise;
        if (fileName === null) {
            promise = api.send(reqName, reqData);
        } else {
            promise = api.send(reqName, reqData, {$files: $('input:file')});
        }

        var widgets = $('input,textarea,select');

        widgets.prop('disabled', true);

        promise
        .done(function(data) {
            $repSummary.html('<span style=color:green>SUCCESS</span>');
            $repData.text(JSON.stringify(data, undefined, '  '));
        })
        .fail(function(err) {
            $repSummary.html('<span style=color:red>ERROR ' + err.message + '</span>');
            if (err.data) {
                $repData.text(JSON.stringify(err.data, undefined, '  '));
            }
        })
        .always(function() {
            widgets.prop('disabled', false);
        });
    });

    return {};
});
