function Workflow2XBlock(runtime, element) {
    $(element).find('.save-button').bind('click', function() {
        console.info('save-button is click');
        var handlerUrl = runtime.handlerUrl(element, 'studioSubmit');
        var data = {
            qNo: $(element).find('input[name=qNo]').val(),
            maxTry: $(element).find('input[name=maxTry]').val(),
        };
        runtime.notify('save', {state: 'start'});
        $.post(handlerUrl, JSON.stringify(data)).done(function(response) {
            runtime.notify('save', {state: 'end'});
        });
    });

    $(element).find('.cancel-button').bind('click', function() {
        console.info('cancel-button is click');
        runtime.notify('cancel', {});
    });
}
